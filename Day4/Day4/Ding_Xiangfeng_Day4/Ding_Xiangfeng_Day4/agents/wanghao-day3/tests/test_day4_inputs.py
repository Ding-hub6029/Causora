"""Focused regression tests for the Day 4 immutable input/evidence boundary."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Callable

import pytest


AGENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = AGENT_ROOT.parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend" / "backend"
for path in (AGENT_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agent_day4.evidence import EvidenceValidationError, enrich_evidence
from agent_day4.inputs import (
    InputValidationError,
    make_verified_run,
    mechanism_for,
    numeric_registry,
    project_role,
    validate_run,
)


FRONTEND_FIXTURE = json.loads(
    (PROJECT_ROOT / "frontend" / "tests" / "fixtures" / "reviewed-v2-TEST_FIXTURE_ONLY.json").read_text(encoding="utf-8")
)
REVIEWED_BUNDLE = json.loads(
    (BACKEND_ROOT / "reviewed" / "wang-2026-10-07" / "reviewed_contract.json").read_text(encoding="utf-8")
)
DEMO_DATA = json.loads((BACKEND_ROOT / "demo_data" / "causora_day1_mock.json").read_text(encoding="utf-8"))
PDF_PATH = AGENT_ROOT / "fixtures" / "demo" / "supplier_a_agreement.pdf"
PDF_SHA256 = hashlib.sha256(PDF_PATH.read_bytes()).hexdigest()


def _conditional_public_record() -> dict[str, Any]:
    """Native EV-020 is an existing conditional source clause, never a new ID."""
    return {
        "id": "EV-020",
        "sourceFile": "supplier_a_agreement.pdf",
        "page": 4,
        "quote": "The agreement automatically renews for 24 months at a 14% higher unit price.",
        "locatorBbox": None,
        "extractedField": "auto_renew",
        "extractedValue": True,
        "matchMethod": "fuzzy",  # Deliberately ignored; the adapter recomputes exact proof.
        "matchScore": 0.0,
        "quoteMatched": False,
    }


def public_evidence(*, conditional: bool = True) -> list[dict[str, Any]]:
    result = copy.deepcopy(DEMO_DATA["evidence"])
    if conditional:
        result.append(_conditional_public_record())
    return result


def reviewed_candidate(
    *,
    request: dict[str, Any] | None = None,
    response: dict[str, Any] | None = None,
    contract: dict[str, Any] | None = None,
    evidence: list[dict[str, Any]] | None = None,
):
    current_response = copy.deepcopy(response or FRONTEND_FIXTURE["response"])
    return make_verified_run(
        simulation_request=copy.deepcopy(request or FRONTEND_FIXTURE["request"]),
        simulation_response=current_response,
        contract=copy.deepcopy(contract or REVIEWED_BUNDLE),
        evidence=copy.deepcopy(evidence if evidence is not None else public_evidence()),
        source_root=PROJECT_ROOT,
        simulation_request_id=current_response["requestId"],
    )


@pytest.fixture(scope="module")
def reviewed_run():
    """Frontend TEST_FIXTURE_ONLY response + actual backend contract + physical PDF."""
    return validate_run(reviewed_candidate())


@pytest.fixture(scope="module")
def actual_development_response() -> dict[str, Any]:
    """Exercise the original unreviewed engine builder exactly once per test module."""
    from app.unreviewed_development import build_unreviewed_development_success_v2

    return build_unreviewed_development_success_v2(
        copy.deepcopy(FRONTEND_FIXTURE["request"]),
        request_id="req-day4-inputs-original-dev-builder",
        project_root=BACKEND_ROOT,
    )


@pytest.fixture(scope="module")
def actual_development_run(actual_development_response: dict[str, Any]):
    return validate_run(
        make_verified_run(
            simulation_request=copy.deepcopy(FRONTEND_FIXTURE["request"]),
            simulation_response=actual_development_response,
            contract=copy.deepcopy(DEMO_DATA["contract"]),
            evidence=public_evidence(conditional=False),
            source_root=BACKEND_ROOT,
            simulation_request_id=actual_development_response["requestId"],
        ),
        require_reviewed=False,
    )


def _trace(response: dict[str, Any], scenario: str = "baseline", option: str = "D0") -> dict[str, Any]:
    return response["data"]["traces"][scenario][option]


def _contract_parameter(trace: dict[str, Any], key: str) -> dict[str, Any]:
    return next(item for item in trace["parameters"] if item["key"] == key)


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_all_keys(item) for item in value.values()))
    if isinstance(value, (list, tuple)):
        return set().union(*(_all_keys(item) for item in value)) if value else set()
    return set()


def _all_text(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [text for item in value.values() for text in _all_text(item)]
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in _all_text(item)]
    return [value] if isinstance(value, str) else []


def test_public_enrichment_derives_hash_types_and_conditional_native_id() -> None:
    records = public_evidence()
    # A false public flag and fuzzy score cannot block or replace physical proof.
    records[0]["quoteMatched"] = False
    records[0]["matchScore"] = 0.01
    enriched = enrich_evidence(records, source_root=PROJECT_ROOT, contract=REVIEWED_BUNDLE)

    assert [item["id"] for item in enriched] == ["EV-014", "EV-019", "EV-021", "EV-024", "EV-027", "EV-020"]
    assert all(item["sourceSha256"] == PDF_SHA256 and item["quoteMatched"] is True for item in enriched)
    assert {item["id"]: item["extractedValue"] for item in enriched}["EV-021"] == 0.14
    assert {item["id"]: item["unit"] for item in enriched}["EV-024"] == "share"
    assert all("matchScore" not in item and "matchMethod" not in item for item in enriched)

    five = enrich_evidence(public_evidence(conditional=False), source_root=PROJECT_ROOT, contract=REVIEWED_BUNDLE)
    assert [item["id"] for item in five] == ["EV-014", "EV-019", "EV-021", "EV-024", "EV-027"]
    invented = public_evidence(conditional=False) + [{**_conditional_public_record(), "id": "EV-999"}]
    with pytest.raises(EvidenceValidationError):
        enrich_evidence(invented, source_root=PROJECT_ROOT, contract=REVIEWED_BUNDLE)


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (lambda records: records.__setitem__(0, {**records[0], "quote": "not the original clause"}), "quote"),
        (lambda records: records.__setitem__(0, {**records[0], "sourceSha256": "0" * 64}), "sourceSha256"),
        (lambda records: records.__setitem__(2, {**records[2], "extractedValue": "13%"}), "extractedValue"),
    ],
)
def test_evidence_enrichment_rejects_bad_quote_hash_and_percentage(
    mutate: Callable[[list[dict[str, Any]]], None], error: str
) -> None:
    records = public_evidence()
    mutate(records)
    with pytest.raises(EvidenceValidationError, match=error):
        enrich_evidence(records, source_root=PROJECT_ROOT, contract=REVIEWED_BUNDLE)


def test_reviewed_frontend_fixture_is_detached_immutable_and_revalidates(reviewed_run) -> None:
    raw_evidence = public_evidence()
    candidate = reviewed_candidate(evidence=raw_evidence)
    # ``make_verified_run`` deep-detaches before validation.
    raw_evidence[0]["quote"] = "caller mutation after construction"
    verified = validate_run(candidate)

    assert verified.reviewed is True
    assert verified.pin_snapshot_sha256
    assert all(item["quoteMatched"] is True for item in verified.evidence)
    assert all("sourceSha256" in item and "unit" in item for item in verified.evidence)
    with pytest.raises(TypeError):
        verified.simulation_response["requestId"] = "mutated"  # type: ignore[index]
    with pytest.raises(TypeError):
        verified.evidence[0]["quoteMatched"] = False  # type: ignore[index]

    again = validate_run(verified)
    assert again.pin_snapshot_sha256 == verified.pin_snapshot_sha256
    assert again.evidence == verified.evidence == reviewed_run.evidence


def _stale_trace_id(response: dict[str, Any]) -> None:
    _trace(response)["simulationId"] = "sim-stale-other-run"


def _stale_data_version(response: dict[str, Any]) -> None:
    response["dataVersion"] = "stale-data-version"


def _stale_scenario(response: dict[str, Any]) -> None:
    _trace(response)["scenarioId"] = "stale-scenario"


def _stale_request(_response: dict[str, Any], request: dict[str, Any]) -> None:
    request["seed"] += 1


def _stale_request_scenario(field: str) -> Callable[[dict[str, Any], dict[str, Any]], None]:
    def mutate(_response: dict[str, Any], request: dict[str, Any]) -> None:
        scenario = next(item for item in request["scenarios"] if item["id"] == "demand-drop")
        scenario[field] += 1 if field == "demandUnits24m" else 0.01
    return mutate


def _stale_formula(response: dict[str, Any]) -> None:
    _trace(response)["formulaVersion"] = "tco-v-stale"


def _stale_option(response: dict[str, Any]) -> None:
    response["data"]["simulation"]["matrix"]["baseline"][0]["optionId"] = "D9"


@pytest.mark.parametrize(
    "name,mutation",
    [
        ("simulation_id", lambda response, request: _stale_trace_id(response)),
        ("data_version", lambda response, request: _stale_data_version(response)),
        ("scenario", lambda response, request: _stale_scenario(response)),
        ("request", _stale_request),
        ("request_demand", _stale_request_scenario("demandUnits24m")),
        ("request_shock", _stale_request_scenario("demandShock")),
        ("request_lead", _stale_request_scenario("leadTimeMultiplier")),
        ("formula", lambda response, request: _stale_formula(response)),
        ("option", lambda response, request: _stale_option(response)),
    ],
)
def test_rejects_all_stale_identity_dimensions(name: str, mutation: Callable[[dict[str, Any], dict[str, Any]], None]) -> None:
    response, request = copy.deepcopy(FRONTEND_FIXTURE["response"]), copy.deepcopy(FRONTEND_FIXTURE["request"])
    mutation(response, request)
    with pytest.raises(InputValidationError):
        validate_run(reviewed_candidate(request=request, response=response))


def test_rejects_mock_simulation_identity_from_formal_reviewed_input() -> None:
    response = copy.deepcopy(FRONTEND_FIXTURE["response"])
    original = response["data"]["simulation"]["simulationId"]
    replacement = "sim-mock-formal-input-rejected"
    # Keep response and all nine traces mutually consistent so the failure is the
    # formal mock marker rather than an ordinary stale trace identity mismatch.
    response = json.loads(json.dumps(response).replace(original, replacement))
    with pytest.raises(InputValidationError, match="execution identity marker"):
        validate_run(reviewed_candidate(response=response))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda request: request["scenarios"][0].__setitem__("unexpected", "field"),
        lambda request: request["options"][0].pop("description"),
        lambda request: request.__setitem__("riskThreshold", float("inf")),
        lambda request: request["scenarios"][0].__setitem__("leadTimeMultiplier", float("nan")),
    ],
)
def test_request_dto_shape_and_finite_values_are_strict(mutate: Callable[[dict[str, Any]], None]) -> None:
    request = copy.deepcopy(FRONTEND_FIXTURE["request"])
    mutate(request)
    with pytest.raises(InputValidationError):
        validate_run(reviewed_candidate(request=request))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda response: _trace(response)["stockoutProbability"].__setitem__("value", 0.5),
        lambda response: _trace(response)["cashOutflowP90"].__setitem__("rankOneBased", 1),
        lambda response: next(
            item for item in response["data"]["deltas"] if item["scenarioId"] == "baseline" and item["optionId"] == "D1"
        ).__setitem__("deltaTco", 1),
        lambda response: _contract_parameter(_trace(response), "contract.renewalLocked")["provenance"].update(
            {"kind": "approved_operating_assumption", "status": "approved"}
        ),
    ],
)
def test_rejects_bad_probability_p90_delta_and_parameter_provenance(mutation: Callable[[dict[str, Any]], None]) -> None:
    response = copy.deepcopy(FRONTEND_FIXTURE["response"])
    mutation(response)
    with pytest.raises(InputValidationError):
        validate_run(reviewed_candidate(response=response))


def test_approved_policy_null_source_file_is_legitimate(reviewed_run) -> None:
    parameter = next(
        item for item in _trace(copy.deepcopy(FRONTEND_FIXTURE["response"]))["parameters"]
        if item["key"] == "operatingPolicy.safetyStockUnits"
    )
    assert parameter["provenance"]["kind"] == "approved_operating_assumption"
    assert parameter["provenance"]["sourceFile"] is None
    assert reviewed_run.reviewed is True


def test_actual_development_engine_run_is_usable_only_as_development(actual_development_run) -> None:
    assert actual_development_run.reviewed is False
    context = actual_development_run.simulation_response["data"]["executionContext"]
    assert context["decisionReady"] is False
    assert all(item["internalOnly"] is True and item["quoteMatched"] is True for item in actual_development_run.evidence)
    with pytest.raises(InputValidationError):
        validate_run(actual_development_run)

    # Projection helpers revalidate in the actual run mode: this is the explicit
    # internal smoke path, not a reviewed-data promotion.
    assert project_role(actual_development_run, "baseline", "COO")["operations"]
    assert mechanism_for(actual_development_run, "demand-drop")["scenarioId"] == "demand-drop"
    assert numeric_registry(actual_development_run, "baseline", "D1")["delta_tco"]["kind"] == "money"


def test_role_field_isolation_mechanism_and_current_option_registry(reviewed_run) -> None:
    cfo = project_role(reviewed_run, "demand-drop", "CFO")
    coo = project_role(reviewed_run, "demand-drop", "COO")
    risk = project_role(reviewed_run, "demand-drop", "Risk")
    assert set(cfo) == {"role", "scenarioId", "selectedOptionId", "selectionStatus", "finance"}
    assert set(coo) == {"role", "scenarioId", "selectedOptionId", "selectionStatus", "operations"}
    assert set(risk) == {"role", "scenarioId", "selectedOptionId", "selectionStatus", "risk"}
    assert "operations" not in _all_keys(cfo) and "finance" not in _all_keys(coo)
    assert "sourceFile" not in _all_keys(risk) and "sourceSha256" not in _all_keys(risk)
    assert not any("supplier_a_agreement.pdf" in text for text in _all_text(risk))

    scenario = next(item for item in reviewed_run.simulation_request["scenarios"] if item["id"] == "demand-drop")
    rows = {item["optionId"]: item for item in reviewed_run.simulation_response["data"]["simulation"]["matrix"]["demand-drop"]}
    mechanism = mechanism_for(reviewed_run, "demand-drop")
    expected_floor = round(reviewed_run.contract["minPurchaseShareA"] * scenario["demandUnits24m"])
    assert mechanism["scenarioDemandUnits24m"] == scenario["demandUnits24m"]
    assert mechanism["committedExcessUnits"] == max(0, reviewed_run.contract["minPurchaseUnitsA"] - expected_floor)
    assert mechanism["holdingCostDeltaUsd"] == {
        option_id: rows[option_id]["breakdown"]["holding"] - rows["D0"]["breakdown"]["holding"]
        for option_id in ("D0", "D1", "D2")
    }
    assert "renewalLocked" not in mechanism

    registry = numeric_registry(reviewed_run, "demand-drop", "D1")
    assert registry["delta_tco"]["value"] == next(
        item["deltaTco"] for item in reviewed_run.simulation_response["data"]["deltas"]
        if item["scenarioId"] == "demand-drop" and item["optionId"] == "D1"
    )
    assert registry["stockout_probability"]["value"] == rows["D1"]["stockoutProbability"]
    assert registry["cash_outflow_p90"]["value"] == rows["D1"]["cashOutflowP90"]
    assert all(not key.startswith("baseline.") and not key.startswith("lead-stress.") for key in registry)
    assert registry["demand-drop.D1.option_id"]["value"] == "D1"
