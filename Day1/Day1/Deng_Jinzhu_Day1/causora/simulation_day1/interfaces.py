"""Day 1 simulation boundary, NOT the 104-week or Monte Carlo engine.

The wire names/shapes are imported conceptually from lib/contracts.ts and
API_CONTRACT.md; this module deliberately does not create a rival API.
Only a labelled mock-response builder is implemented. The production engine
raises until physical inventory/reorder and cash-P90 assumptions are approved.
"""
from __future__ import annotations

import json
import hashlib
import math
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from simulation_day1.wire_models import SimulateRequest, SimulateSuccess

SCHEMA_VERSION = "causora.contract.v1"
FORMULA_VERSION = "tco-v1"
OPTION_IDS = ("D0", "D1", "D2")
SCENARIO_IDS = ("baseline", "demand-drop", "lead-stress")
OPTION_SPECS = {"D0": (1.0, False), "D1": (0.6, False), "D2": (0.0, True)}
ROOT = Path(__file__).resolve().parents[1]
FROZEN_MOCK_SHA256 = "7002888a4d9f831a7210ec0dbf6cfd556c4c22a134d41e2f0d9674689ceddf56"


class ContractInputError(ValueError):
    """400/422 validation_error at the future HTTP adapter boundary."""


def _frozen_mock() -> dict[str, Any]:
    """Read only the original v4.1 snapshot; a changed file needs team re-freeze."""
    raw = (ROOT / "demo_data" / "causora_day1_mock.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != FROZEN_MOCK_SHA256:
        raise ContractInputError("Day 1 LOCAL MOCK changed without dataVersion / team re-freeze")
    return json.loads(raw.decode("utf-8"))


def _keys(value: Any, keys: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ContractInputError(f"{where}: expected keys {sorted(keys)}")
    return value


def _number(value: Any, where: str, low: float, high: float = math.inf,
            integer: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high or (integer and not isinstance(value, int)):
        raise ContractInputError(f"{where}: finite {'integer' if integer else 'number'} in [{low}, {high}] required")
    return value


def _text(value: Any, where: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractInputError(f"{where}: nonempty string required")


def _validate_contract(contract: dict[str, Any]) -> None:
    """Do not promote a PDF clause into a notice fact or a forecast estimator."""
    for key in ("forecastBasis", "noticeRecordSource", "decisionDate", "renewalDate", "noticeDeadline"):
        _text(contract.get(key), key)
    if contract["forecastBasis"] != "locked-at-renewal":
        raise ContractInputError("Day 1 forecastBasis changed; team approval required")
    if not isinstance(contract.get("noticeSent"), bool):
        raise ContractInputError("noticeSent is missing; never infer no notice")
    if not isinstance(contract.get("renewalLocked"), bool):
        raise ContractInputError("renewalLocked must be an explicit derived boolean")
    for key in ("daysToRenewal", "renewalNoticeDays", "lockedForecastUnits24m", "minPurchaseUnitsA", "terminationFeeUsd"):
        _number(contract.get(key), key, 0, integer=True)
    for key in ("minPurchaseShareA", "renewalPriceIncreasePct"):
        _number(contract.get(key), key, 0, 1)
    try:
        dates = [date.fromisoformat(contract[key]) for key in ("decisionDate", "renewalDate", "noticeDeadline")]
        if any(not re.fullmatch(r"\d{4}-\d{2}-\d{2}", contract[key]) for key in ("decisionDate", "renewalDate", "noticeDeadline")):
            raise ValueError("not ISO YYYY-MM-DD")
    except ValueError as exc:
        raise ContractInputError("invalid contract dates") from exc
    decision, renewal, deadline = dates
    if (renewal - decision).days != contract["daysToRenewal"] or renewal - timedelta(days=contract["renewalNoticeDays"]) != deadline:
        raise ContractInputError("notice deadline / daysToRenewal inconsistent")
    if contract["renewalLocked"] != (decision > deadline and not contract["noticeSent"]):
        raise ContractInputError("renewalLocked inconsistent with dated notice input")
    if (contract["lockedForecastUnits24m"], contract["minPurchaseShareA"], contract["minPurchaseUnitsA"]) != (26000, 0.6, 15600):
        raise ContractInputError("Day 1 forecast basis/floor changed; re-freeze together")


def validate_request(request: dict[str, Any], *, dataset_id: str = "ds-001", contract: dict[str, Any] | None = None,
                     allow_unfrozen_scenarios: bool = False) -> None:
    """Validate v1 DTO; Day 1's static adapter accepts only frozen scenarios.

    The future physical engine may explicitly opt out of this *mock-only*
    scenario gate, but must calculate every metric from its new input.
    """
    try:
        SimulateRequest.model_validate_json(json.dumps(request, allow_nan=False))
    except (ValidationError, ValueError, TypeError) as exc:
        raise ContractInputError(f"invalid v1 SimulateRequest: {exc}") from exc
    _keys(request, {"schemaVersion", "datasetId", "scenarios", "options", "seed", "riskThreshold", "budgetCeilingUsd"}, "request")
    if request["schemaVersion"] != SCHEMA_VERSION or request["datasetId"] != dataset_id:
        raise ContractInputError("unknown schemaVersion or datasetId")
    _number(request["seed"], "seed", 0, integer=True)
    _number(request["riskThreshold"], "riskThreshold", 0, 1)
    _number(request["budgetCeilingUsd"], "budgetCeilingUsd", 0, integer=True)
    scenarios, options = request["scenarios"], request["options"]
    if not isinstance(scenarios, list) or not isinstance(options, list):
        raise ContractInputError("scenarios/options must be arrays")
    if len(scenarios) != 3 or {s.get("id") for s in scenarios if isinstance(s, dict)} != set(SCENARIO_IDS):
        raise ContractInputError("exactly baseline, demand-drop, lead-stress required for Day 1 demo")
    if len(options) != 3 or {o.get("id") for o in options if isinstance(o, dict)} != set(OPTION_IDS):
        raise ContractInputError("exactly one each of D0, D1, D2 required")
    for scenario in scenarios:
        _keys(scenario, {"id", "label", "tag", "demandShock", "demandUnits24m", "leadTime", "leadTimeMultiplier", "description"}, "scenario")
        for key in ("label", "tag", "leadTime", "description"):
            _text(scenario[key], f"scenario.{key}")
        _number(scenario["demandShock"], "demandShock", -100, 1000)
        _number(scenario["demandUnits24m"], "demandUnits24m", 0, integer=True)
        _number(scenario["leadTimeMultiplier"], "leadTimeMultiplier", 0.001)
    for option in options:
        _keys(option, {"id", "label", "shareA", "terminateA", "allocation", "short", "description"}, "option")
        for key in ("label", "allocation", "short", "description"):
            _text(option[key], f"option.{key}")
        _number(option["shareA"], "shareA", 0, 1)
        if (option["shareA"], option["terminateA"]) != OPTION_SPECS[option["id"]]:
            raise ContractInputError(f"{option['id']}: frozen allocation/exit meaning changed")
    if contract is not None:
        _validate_contract(contract)
        for scenario in scenarios:
            expected = round(contract["lockedForecastUnits24m"] * (1 + scenario["demandShock"] / 100))
            if scenario["demandUnits24m"] != expected:
                raise ContractInputError(f"{scenario['id']}: demandUnits24m differs from frozen demo forecast × shock")
    if not allow_unfrozen_scenarios:
        snapshot = _frozen_mock()
        frozen = {scenario["id"]: scenario for scenario in snapshot["scenarios"]}
        for scenario in scenarios:
            original = frozen[scenario["id"]]
            if scenario != original:
                changed = sorted(key for key in original if scenario[key] != original[key])
                raise ContractInputError(f"{scenario['id']}: Day 1 LOCAL MOCK frozen scenario mismatch ({', '.join(changed)}); real simulation is not available")
        frozen_options = {option["id"]: option for option in snapshot["options"]}
        for option in options:
            original = frozen_options[option["id"]]
            if option != original:
                changed = sorted(key for key in original if option[key] != original[key])
                raise ContractInputError(f"{option['id']}: Day 1 LOCAL MOCK frozen option mismatch ({', '.join(changed)}); real simulation is not available")


def check_accounting(simulation: dict[str, Any], contract: dict[str, Any], options: list[dict[str, Any]]) -> None:
    """Guard static inputs (or future engine results) against double premiums and fees."""
    prices = simulation["unitPricesUsd"]
    for scenario_id, cells in simulation["matrix"].items():
        if scenario_id not in SCENARIO_IDS or {cell["optionId"] for cell in cells} != set(OPTION_IDS) or len(cells) != 3:
            raise ContractInputError(f"{scenario_id}: missing/duplicate option cells")
        for cell in cells:
            option = next(o for o in options if o["id"] == cell["optionId"])
            a, b = cell["unitsFromA"], cell["unitsFromB"]
            if not all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in (a, b)):
                raise ContractInputError("units must be nonnegative integers")
            if a + b and not math.isclose(a / (a + b), option["shareA"], abs_tol=1e-12):
                raise ContractInputError(f"{scenario_id}/{option['id']}: allocation mismatch")
            if cell["feasible"] and contract["renewalLocked"] and not option["terminateA"] and a < contract["minPurchaseUnitsA"]:
                raise ContractInputError(f"{scenario_id}/{option['id']}: contractual minimum violated")
            costs = cell["breakdown"]
            if set(costs) != {"purchase", "holding", "stockoutLoss", "renewalPremium", "terminationFee"} or any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in costs.values()):
                raise ContractInputError("breakdown requires five nonnegative integer USD lines")
            if costs["purchase"] != round(a * prices["A"] + b * prices["B"]):
                raise ContractInputError("base-price purchase mismatch (do not uplift twice)")
            expected_premium = round(a * prices["A"] * contract["renewalPriceIncreasePct"]) if contract["renewalLocked"] else 0
            if costs["renewalPremium"] != expected_premium:
                raise ContractInputError("renewal premium mismatch")
            if costs["terminationFee"] != (contract["terminationFeeUsd"] if option["terminateA"] and contract["renewalLocked"] else 0):
                raise ContractInputError("termination fee mismatch")
            if cell["expectedTco"] != sum(costs.values()):
                raise ContractInputError("TCO does not reconcile")
            for key in ("stockoutProbability", "serviceLevel"):
                _number(cell[key], key, 0, 1)
            _number(cell["cashOutflowP90"], "cashOutflowP90", 0, integer=True)


def select_by_scenario(simulation: dict[str, Any], request: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Selection uses eligible cells only; ties break by ID and violations are ordered."""
    selections = {}
    for scenario in request["scenarios"]:
        scenario_id = scenario["id"]
        cells = {row["optionId"]: row for row in simulation["matrix"][scenario_id]}
        eligible = []
        violations = []
        for option_id in OPTION_IDS:
            cell = cells[option_id]
            failed = []
            if not cell["feasible"]:
                failed.append("infeasible")
            if cell["stockoutProbability"] > request["riskThreshold"]:
                failed.append("stockout_threshold")
            if cell["cashOutflowP90"] > request["budgetCeilingUsd"]:
                failed.append("cash_ceiling")
            violations.extend({"optionId": option_id, "code": code} for code in failed)
            if not failed:
                eligible.append(cell)
        if eligible:
            winner = min(eligible, key=lambda c: (c["expectedTco"], c["optionId"]))
            selections[scenario_id] = {"scenarioId": scenario_id, "status": "selected", "recommendedOptionId": winner["optionId"], "constraintViolations": violations}
        else:
            selections[scenario_id] = {"scenarioId": scenario_id, "status": "no_feasible_option", "recommendedOptionId": None, "constraintViolations": violations}
    return selections


def calculate_deltas(simulation: dict[str, Any], scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deltas = []
    for scenario in scenarios:
        sid = scenario["id"]
        cells = {row["optionId"]: row for row in simulation["matrix"][sid]}
        base = cells["D0"]
        for oid in OPTION_IDS:
            row = cells[oid]
            deltas.append({"scenarioId": sid, "optionId": oid, "baselineOptionId": "D0",
                           "deltaTco": row["expectedTco"] - base["expectedTco"],
                           "deltaStockoutPp": round((row["stockoutProbability"] - base["stockoutProbability"]) * 100, 10),
                           "deltaServicePp": round((row["serviceLevel"] - base["serviceLevel"]) * 100, 10),
                           "deltaCashP90": row["cashOutflowP90"] - base["cashOutflowP90"]})
    return deltas


def make_mock_request(mock: dict[str, Any], *, risk_threshold: float = 0.12, budget_usd: int = 480000) -> dict[str, Any]:
    return {"schemaVersion": SCHEMA_VERSION, "datasetId": "ds-001", "scenarios": mock["scenarios"],
            "options": mock["options"], "seed": mock["simulation"]["seed"],
            "riskThreshold": risk_threshold, "budgetCeilingUsd": budget_usd}


def make_mock_response(mock: dict[str, Any], request: dict[str, Any], *, request_id: str) -> dict[str, Any]:
    """Wrap the baseline's *unchanged* illustrative cells; not a simulation run."""
    validate_request(request, contract=mock["contract"])
    if mock != _frozen_mock():
        raise ContractInputError("Day 1 LOCAL MOCK input snapshot changed; team re-freeze required")
    _text(request_id, "requestId")
    simulation = mock["simulation"]
    if mock["meta"]["schemaVersion"] != SCHEMA_VERSION or simulation["dataVersion"] != mock["meta"]["dataVersion"] or simulation["monteCarloRuns"] != 0 or "mock" not in simulation["simulationId"]:
        raise ContractInputError("refusing to label this result as a Day 1 local mock")
    if simulation["seed"] != request["seed"] or simulation["weeks"] != 104 or simulation["formulaVersion"] != FORMULA_VERSION:
        raise ContractInputError("mock metadata differs from request or 104-week declaration")
    check_accounting(simulation, mock["contract"], request["options"])
    response = {"schemaVersion": SCHEMA_VERSION, "dataVersion": simulation["dataVersion"], "requestId": request_id,
            "data": {"simulation": simulation, "deltas": calculate_deltas(simulation, request["scenarios"]),
                     "selections": select_by_scenario(simulation, request)}}
    try:
        SimulateSuccess.model_validate_json(json.dumps(response, allow_nan=False))
    except (ValidationError, ValueError, TypeError) as exc:
        raise ContractInputError(f"invalid v1 SimulateSuccess: {exc}") from exc
    return response


def simulate_104_weeks(request: dict[str, Any], dataset: dict[str, Any]) -> dict[str, Any]:
    """Day 2 boundary. In particular, never infer holding/loss/P90 from mock KPIs."""
    validate_request(request, dataset_id=dataset["datasetId"], contract=dataset["contract"], allow_unfrozen_scenarios=True)
    raise NotImplementedError("Day 2: 104-week state, replenishment, lead-time sampling, Monte Carlo and cash P90 need verified input assumptions")


if __name__ == "__main__":
    mock = _frozen_mock()
    dest = Path(__file__).parent / "examples"
    request = make_mock_request(mock)
    (dest / "simulate_request.json").write_text(json.dumps(request, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (dest / "simulate_response_LOCAL_MOCK.json").write_text(json.dumps(make_mock_response(mock, request, request_id="req-day1-mock-001"), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    no_option = make_mock_request(mock, budget_usd=1)
    (dest / "simulate_request_no_feasible.json").write_text(json.dumps(no_option, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (dest / "simulate_response_no_feasible_LOCAL_MOCK.json").write_text(json.dumps(make_mock_response(mock, no_option, request_id="req-day1-mock-002"), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Wrote static LOCAL MOCK envelopes; no 104-week simulation was executed.")
