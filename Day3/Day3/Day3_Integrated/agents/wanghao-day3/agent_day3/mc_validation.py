"""Fail-closed validation for Jinzhu's unreviewed-development HTTP Monte Carlo v2 response.

This is an integration/audit boundary for the *explicitly unreviewed* development
route.  It does not call a simulation engine, does not reconstruct Monte Carlo
trials from a sample path, and never converts a passing response into a reviewed
or decision-ready result.

The authoritative wire shape is loaded from Jinzhu's
``causora.contract.v2.schema.json``.  Independent checks below bind the nine
matrix cells and traces to the request, their aggregate statistics, deltas, and
selection rules.  A schema-valid payload that is a legacy local mock,
deterministic preview, reviewed-looking response, or inconsistent aggregate is
therefore rejected.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover - deployment dependency failure
    raise RuntimeError("mc_validation requires jsonschema for the authoritative v2 contract") from exc


SCENARIOS = ("baseline", "demand-drop", "lead-stress")
OPTIONS = ("D0", "D1", "D2")
COMPONENTS = ("purchase", "holding", "stockoutLoss", "renewalPremium", "terminationFee")
UNREVIEWED_MODE = "unreviewed_development_only"
DEV_HEADER_VALUES = {
    "x-causora-review-status": "unreviewed-development-only",
    "x-causora-trace-contract": "causora.contract.v2-dev-unreviewed",
    "x-causora-execution-mode": "unreviewed-development-only",
}
EXPECTED_COMPONENT_INPUTS = {
    "purchase": ("matrix.unitsFromA", "matrix.unitsFromB", "unitPricesUsd.A", "unitPricesUsd.B"),
    "holding": ("operatingPolicy.holdingCostUsdPerUnitWeek", "reorderPointUnits"),
    "stockoutLoss": ("operatingPolicy.lostContributionMarginUsdPerUnit",),
    "renewalPremium": ("matrix.unitsFromA", "unitPricesUsd.A", "contract.renewalPriceIncreasePct"),
    "terminationFee": ("option.terminateA", "contract.renewalLocked", "contract.terminationFeeUsd"),
}


class MCValidationError(ValueError):
    """Raised when a development-only HTTP MC response is not auditable."""


def canonical_sha(value: Any) -> str:
    """SHA-256 of canonical JSON without normalising original JSON number types.

    ``json.dumps`` retains Python's distinct spellings for ``1`` and ``1.0``;
    callers must pass the originally decoded JSON value rather than a model dump
    that may coerce values.  Non-finite values and non-JSON types raise
    ``ValueError`` instead of receiving a lossy hash.
    """
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"value is not canonical JSON: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


def resolve_pointer(doc: Any, pointer: str) -> Any:
    """Resolve an RFC 6901 JSON Pointer without silently creating values.

    The empty pointer selects ``doc``.  Missing object members, invalid array
    indexes, and malformed ``~`` escapes raise ``ValueError``.  ``-`` is not a
    readable array index and is rejected.
    """
    if not isinstance(pointer, str):
        raise ValueError("JSON Pointer must be a string")
    if pointer == "":
        return doc
    if not pointer.startswith("/"):
        raise ValueError("non-empty JSON Pointer must begin with '/'")

    def decode(token: str) -> str:
        position = 0
        while position < len(token):
            if token[position] == "~":
                if position + 1 >= len(token) or token[position + 1] not in "01":
                    raise ValueError(f"malformed JSON Pointer escape in {pointer!r}")
                position += 2
            else:
                position += 1
        return token.replace("~1", "/").replace("~0", "~")

    current = doc
    for raw_token in pointer[1:].split("/"):
        token = decode(raw_token)
        if isinstance(current, dict):
            if token not in current:
                raise ValueError(f"JSON Pointer does not resolve: {pointer!r}")
            current = current[token]
        elif isinstance(current, list):
            if token == "-" or not token or (len(token) > 1 and token[0] == "0") or not token.isascii() or not token.isdecimal():
                raise ValueError(f"invalid JSON Pointer array index {token!r}")
            index = int(token)
            if index >= len(current):
                raise ValueError(f"JSON Pointer does not resolve: {pointer!r}")
            current = current[index]
        else:
            raise ValueError(f"JSON Pointer does not resolve through scalar: {pointer!r}")
    return current


def _fail(message: str) -> None:
    raise MCValidationError(message)


def _schema_path() -> Path:
    """Locate the schema copied with Wang's Jinzhu reference, or an explicit backend."""
    project_root = Path(__file__).resolve().parents[1]
    candidates: list[Path] = []
    configured_schema = os.environ.get("CAUSORA_DAY3_SCHEMA")
    if configured_schema:
        candidates.append(Path(configured_schema).expanduser())
    candidates.extend(
        (
            project_root / "reference" / "jinzhu_day3" / "causora.contract.v2.schema.json",
            project_root / "reference" / "causora.contract.v2.schema.json",
        )
    )
    configured_backend = os.environ.get("CAUSORA_DAY3_BACKEND")
    if configured_backend:
        candidates.append(Path(configured_backend).expanduser() / "contracts" / "causora.contract.v2.schema.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    _fail(
        "authoritative causora.contract.v2.schema.json is unavailable; copy it to "
        "reference/jinzhu_day3 or set CAUSORA_DAY3_SCHEMA/CAUSORA_DAY3_BACKEND"
    )


@lru_cache(maxsize=4)
def _validator_for(schema_path: str) -> jsonschema.protocols.Validator:
    try:
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        validator_class = jsonschema.validators.validator_for(schema)
        validator_class.check_schema(schema)
        return validator_class(schema)
    except (OSError, json.JSONDecodeError, jsonschema.exceptions.SchemaError) as exc:
        raise MCValidationError(f"cannot load authoritative v2 schema: {exc}") from exc


def _validate_schema(response: dict[str, Any]) -> None:
    validator = _validator_for(str(_schema_path()))
    error = next(validator.iter_errors(response), None)
    if error is not None:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        _fail(f"response fails authoritative causora.contract.v2 schema at {location}: {error.message}")


def _is_int(value: Any, *, minimum: int | None = None) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and (minimum is None or value >= minimum)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _same_scalar(expected: Any, actual: Any) -> bool:
    """Compare JSON scalar values without treating a bool as an integer or 1 as 1.0."""
    return type(expected) is type(actual) and expected == actual


def _decimal(value: Any, where: str) -> Decimal:
    if not isinstance(value, str):
        _fail(f"{where} must retain a raw decimal string")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise MCValidationError(f"{where} is not a decimal string") from exc
    if not parsed.is_finite():
        _fail(f"{where} must be finite")
    return parsed


def _check_headers(headers: Mapping[str, Any] | None, request_id: str) -> None:
    if headers is None:
        return
    if not isinstance(headers, Mapping):
        _fail("headers must be a mapping when provided")
    normalised: dict[str, Any] = {}
    for name, value in headers.items():
        if not isinstance(name, str):
            _fail("header names must be strings")
        key = name.lower()
        if key in normalised:
            _fail(f"duplicate case-insensitive header {name!r}")
        normalised[key] = value
    for name, expected in DEV_HEADER_VALUES.items():
        if normalised.get(name) != expected:
            _fail(f"required development header {name} must equal {expected!r}")
    if normalised.get("x-request-id") != request_id:
        _fail("X-Request-Id must exactly match response.requestId")


def _request_maps(request: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(request, dict):
        _fail("request must be a dictionary")
    if request.get("datasetId") != "ds-001":
        _fail("latest supplied development service is bound to dataset ds-001")
    request_schema = Path(__file__).resolve().parents[1] / "reference" / "jinzhu_day3" / "simulate_request_v1.schema.json"
    if not request_schema.is_file():
        _fail("authoritative v1 request schema is unavailable")
    error = next(_validator_for(str(request_schema)).iter_errors(request), None)
    if error is not None:
        _fail("request does not conform to the unchanged v1 schema")
    if not _is_int(request.get("seed"), minimum=0):
        _fail("request.seed must be a nonnegative integer")
    scenarios = request.get("scenarios")
    options = request.get("options")
    if not isinstance(scenarios, list) or not isinstance(options, list):
        _fail("request.scenarios and request.options must be lists")
    if not _is_number(request.get("riskThreshold")) or not 0 <= float(request["riskThreshold"]) <= 1:
        _fail("request.riskThreshold must be a finite fraction from zero to one")
    if not _is_int(request.get("budgetCeilingUsd"), minimum=0):
        _fail("request.budgetCeilingUsd must be a nonnegative integer")
    scenario_by_id: dict[str, dict[str, Any]] = {}
    option_by_id: dict[str, dict[str, Any]] = {}
    for item in scenarios:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item["id"] in scenario_by_id:
            _fail("request scenarios must be objects with unique string IDs")
        scenario_by_id[item["id"]] = item
    for item in options:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item["id"] in option_by_id:
            _fail("request options must be objects with unique string IDs")
        option_by_id[item["id"]] = item
    if len(scenarios) != 3 or set(scenario_by_id) != set(SCENARIOS):
        _fail("request must contain exactly the three fixed scenarios once each")
    if len(options) != 3 or set(option_by_id) != set(OPTIONS):
        _fail("request must contain exactly D0, D1, and D2 once each")
    expected_options = {"D0": (1.0, False), "D1": (0.6, False), "D2": (0.0, True)}
    for option_id, option in option_by_id.items():
        if not _is_number(option.get("shareA")) or float(option["shareA"]) != expected_options[option_id][0] or option.get("terminateA") is not expected_options[option_id][1]:
            _fail(f"request option {option_id} changes its fixed share/termination meaning")
    for scenario_id, scenario in scenario_by_id.items():
        for key in ("demandShock", "demandUnits24m", "leadTimeMultiplier"):
            if key not in scenario or not _is_number(scenario[key]):
                _fail(f"request scenario {scenario_id}.{key} is missing or non-finite")
        if not _is_int(scenario["demandUnits24m"], minimum=0) or float(scenario["leadTimeMultiplier"]) <= 0:
            _fail(f"request scenario {scenario_id} has invalid units or lead-time multiplier")
    return scenario_by_id, option_by_id


def _reject_legacy_or_reviewed(response: dict[str, Any]) -> None:
    if response.get("schemaVersion") != "causora.contract.v2":
        _fail("only causora.contract.v2 HTTP success envelopes are accepted")
    # A v1 local mock or deterministic preview cannot have this v2 shape, but
    # explicit markers make the rejection understandable even if fields are padded.
    wire_text = json.dumps(response, ensure_ascii=False, sort_keys=True, allow_nan=False).lower()
    if "local_mock" in wire_text or "local mock" in wire_text or "deterministic" in wire_text:
        _fail("legacy LOCAL_MOCK/deterministic output is not a Monte Carlo HTTP response")


def _check_execution_context(response: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    data = response["data"]
    simulation = data["simulation"]
    context = data["executionContext"]
    expected_statuses = {
        "humanReviewStatus": "not_reviewed_development_only",
        "policyStatus": "unapproved_development_only",
        "contractReleaseStatus": "not_released_development_only",
    }
    if context.get("mode") != UNREVIEWED_MODE or context.get("decisionReady") is not False:
        _fail("executionContext must be exactly unreviewed_development_only and not decision-ready")
    for key, expected in expected_statuses.items():
        if context.get(key) != expected:
            _fail(f"executionContext.{key} must remain {expected!r}")
    banner = context.get("banner")
    if not isinstance(banner, str):
        _fail("executionContext.banner must be a string")
    banner_upper = banner.upper()
    if not all(fragment in banner_upper for fragment in ("UNREVIEWED", "DEVELOPMENT ONLY", "NOT DECISION-READY")):
        _fail("executionContext.banner must explicitly say UNREVIEWED DEVELOPMENT ONLY and NOT DECISION-READY")
    data_version = simulation["dataVersion"]
    if response.get("dataVersion") != data_version or "UNREVIEWED_DEV_ONLY" not in data_version:
        _fail("envelope and simulation dataVersion must match and contain UNREVIEWED_DEV_ONLY")
    if not simulation["simulationId"].startswith("sim-dev-unreviewed-"):
        _fail("simulationId must use the sim-dev-unreviewed- prefix")
    if simulation.get("weeks") != 104:
        _fail("simulation must declare exactly 104 weeks")
    if not _is_int(simulation.get("monteCarloRuns"), minimum=1):
        _fail("monteCarloRuns must be an actual positive Monte Carlo run count")
    return data, simulation


def _parameter_map(trace: dict[str, Any], where: str) -> dict[str, dict[str, Any]]:
    parameters = trace["parameters"]
    parameter_by_key = {parameter.get("key"): parameter for parameter in parameters if isinstance(parameter, dict)}
    if len(parameter_by_key) != len(parameters) or any(not isinstance(key, str) or not key for key in parameter_by_key):
        _fail(f"{where}.parameters must have unique nonempty keys")
    return parameter_by_key


def _check_unreviewed_provenance(trace: dict[str, Any], where: str) -> None:
    identity = trace["runIdentity"]
    if identity.get("executionMode") != UNREVIEWED_MODE:
        _fail(f"{where}.runIdentity.executionMode is not unreviewed development")
    if identity.get("reviewRecordId") is not None or identity.get("reviewRecordSha256") is not None:
        _fail(f"{where}.runIdentity falsely supplies a review record")
    for key in ("policyApprovalReference", "policyConfigurationId", "contractApprovalReference"):
        value = identity.get(key)
        if not isinstance(value, str) or "UNREVIEWED_DEV_ONLY" not in value:
            _fail(f"{where}.runIdentity.{key} must retain its UNREVIEWED_DEV_ONLY marker")
    for parameter in trace["parameters"]:
        provenance = parameter["provenance"]
        if parameter["key"].startswith("contract.") and provenance.get("kind") != "unreviewed_development_contract":
            _fail(f"{where} contract parameter lacks unreviewed contract provenance")
        if parameter["key"].startswith("operatingPolicy.") and provenance.get("kind") != "unreviewed_development_assumption":
            _fail(f"{where} operating parameter lacks unapproved policy provenance")
        if provenance.get("reviewRecordId") is not None or provenance.get("reviewRecordSha256") is not None:
            _fail(f"{where} parameter {parameter['key']} falsely supplies a review record")
        if provenance.get("kind") in {"reviewed_contract", "approved_operating_assumption"} or provenance.get("status") in {"reviewed", "approved"}:
            _fail(f"{where} parameter {parameter['key']} presents reviewed/approved provenance")
        if provenance.get("kind") in {"unreviewed_development_contract", "unreviewed_development_assumption"}:
            if provenance.get("status") != "unreviewed_development_only" or "UNREVIEWED_DEV_ONLY" not in provenance.get("sourceId", ""):
                _fail(f"{where} parameter {parameter['key']} lacks explicit unreviewed provenance")


def _check_rounding(component: dict[str, Any], where: str) -> None:
    audit = component["roundingAudit"]
    raw = _decimal(audit["rawMeanUsd"], f"{where}.rawMeanUsd")
    difference = _decimal(audit["displayedMinusRawMeanUsd"], f"{where}.displayedMinusRawMeanUsd")
    if audit["displayedValueUsd"] != component["valueUsd"]:
        _fail(f"{where}.roundingAudit.displayedValueUsd differs from component value")
    if difference != Decimal(component["valueUsd"]) - raw:
        _fail(f"{where}.roundingAudit displayed-minus-raw difference does not reconcile")


def _check_trace(
    trace: dict[str, Any], cell: dict[str, Any], scenario: dict[str, Any], option: dict[str, Any],
    scenario_id: str, option_id: str, simulation: dict[str, Any],
) -> int:
    where = f"trace[{scenario_id}][{option_id}]"
    expected_identity = (scenario_id, option_id, simulation["simulationId"], simulation["dataVersion"], simulation["formulaVersion"])
    actual_identity = (trace.get("scenarioId"), trace.get("optionId"), trace.get("simulationId"), trace.get("dataVersion"), trace.get("formulaVersion"))
    if actual_identity != expected_identity:
        _fail(f"{where} identity differs from its matrix cell/simulation")
    _check_unreviewed_provenance(trace, where)
    parameter_by_key = _parameter_map(trace, where)
    for key in ("contract.renewalLocked", "contract.renewalPriceIncreasePct", "contract.minPurchaseUnitsA", "contract.terminationFeeUsd"):
        if key not in parameter_by_key:
            _fail(f"{where} is missing required contract parameter {key}")
        value = parameter_by_key[key]["value"]
        valid = (type(value) is bool if key.endswith("renewalLocked") else
                 _is_number(value) and value >= 0 if key.endswith("renewalPriceIncreasePct") else
                 _is_int(value, minimum=0))
        if not valid:
            _fail(f"{where} contract parameter {key} has the wrong primitive type or range")
    bindings = {
        "scenario.demandShock": scenario["demandShock"],
        "scenario.demandUnits24m": scenario["demandUnits24m"],
        "scenario.leadTimeMultiplier": scenario["leadTimeMultiplier"],
        "option.shareA": option["shareA"],
        "option.terminateA": option["terminateA"],
        "matrix.unitsFromA": cell["unitsFromA"],
        "matrix.unitsFromB": cell["unitsFromB"],
        "unitPricesUsd.A": simulation["unitPricesUsd"]["A"],
        "unitPricesUsd.B": simulation["unitPricesUsd"]["B"],
        "configuration.executionMode": UNREVIEWED_MODE,
    }
    for key, expected in bindings.items():
        parameter = parameter_by_key.get(key)
        if parameter is None or not _same_scalar(parameter.get("value"), expected):
            _fail(f"{where}.parameters[{key}] is not bound to the request/cell/simulation")

    component_by_key = {component.get("key"): component for component in trace["components"] if isinstance(component, dict)}
    if len(component_by_key) != len(COMPONENTS) or set(component_by_key) != set(COMPONENTS):
        _fail(f"{where} must contain each of the five TCO components exactly once")
    for key in COMPONENTS:
        component = component_by_key[key]
        if component["valueUsd"] != cell["breakdown"][key]:
            _fail(f"{where}.{key} differs from matrix breakdown")
        if tuple(component["inputKeys"]) != EXPECTED_COMPONENT_INPUTS[key]:
            _fail(f"{where}.{key}.inputKeys are not the closed v2 formula inputs")
        if any(input_key not in parameter_by_key for input_key in component["inputKeys"]):
            _fail(f"{where}.{key}.inputKeys do not resolve to parameters")
        _check_rounding(component, f"{where}.{key}")
    if trace["expectedTcoUsd"] != cell["expectedTco"] or sum(component["valueUsd"] for component in component_by_key.values()) != cell["expectedTco"]:
        _fail(f"{where} five component values do not reconcile to matrix expectedTco")

    runs = simulation["monteCarloRuns"]
    probability = trace["stockoutProbability"]
    if probability["denominatorRuns"] != runs or probability["numeratorStockoutRuns"] > runs:
        _fail(f"{where}.stockoutProbability must use the simulation Monte Carlo denominator")
    expected_probability = probability["numeratorStockoutRuns"] / runs
    if not math.isclose(float(probability["value"]), expected_probability, rel_tol=0.0, abs_tol=1e-12) or not math.isclose(float(cell["stockoutProbability"]), expected_probability, rel_tol=0.0, abs_tol=1e-12):
        _fail(f"{where}.stockoutProbability does not equal numerator/Monte Carlo runs")

    service = trace["serviceLevel"]
    if service["fulfilledUnitsAllRuns"] > service["demandUnitsAllRuns"]:
        _fail(f"{where}.serviceLevel fulfilled units exceed demand")
    expected_service = service["fulfilledUnitsAllRuns"] / service["demandUnitsAllRuns"] if service["demandUnitsAllRuns"] else 1.0
    if not math.isclose(float(service["value"]), expected_service, rel_tol=0.0, abs_tol=1e-12) or not math.isclose(float(cell["serviceLevel"]), expected_service, rel_tol=0.0, abs_tol=1e-12):
        _fail(f"{where}.serviceLevel does not equal aggregate fulfilled/demand counts")

    p90 = trace["cashOutflowP90"]
    if p90["denominatorRuns"] != runs or p90["rankOneBased"] != (9 * runs + 9) // 10:
        _fail(f"{where}.cashOutflowP90 must use ceil(0.9N) for the same Monte Carlo N")
    if p90["valueUsd"] != cell["cashOutflowP90"]:
        _fail(f"{where}.cashOutflowP90 differs from matrix aggregate")
    if p90["includedCashComponents"] != ["purchase", "holding", "renewalPremium", "terminationFee"] or p90["excludedNonCashComponents"] != ["stockoutLoss"]:
        _fail(f"{where}.cashOutflowP90 cash component inclusion is not frozen")

    sample_path = trace["samplePath"]
    if sample_path["classification"] != "single_realised_trial_not_aggregate" or len(sample_path["weeks"]) != 104:
        _fail(f"{where}.samplePath must be one 104-week realised trial, not an aggregate")
    note = sample_path["note"].lower()
    if "not" not in note or not any(word in note for word in ("average", "expectation", "aggregate")):
        _fail(f"{where}.samplePath.note must reject aggregate interpretation")
    # Deliberately do not infer probabilities, means, or P90 from these 104 rows:
    # they document one run only; aggregate identities above use trace counters.
    return len(sample_path["weeks"])


def _check_deltas(data: dict[str, Any], matrix: dict[str, list[dict[str, Any]]]) -> None:
    deltas = data["deltas"]
    delta_by_identity = {(delta.get("scenarioId"), delta.get("optionId")): delta for delta in deltas if isinstance(delta, dict)}
    required = {(scenario_id, option_id) for scenario_id in SCENARIOS for option_id in OPTIONS}
    if len(deltas) != 9 or len(delta_by_identity) != 9 or set(delta_by_identity) != required:
        _fail("deltas must contain every one of the nine scenario/option identities exactly once")
    for scenario_id in SCENARIOS:
        by_option = {cell["optionId"]: cell for cell in matrix[scenario_id]}
        baseline = by_option["D0"]
        for option_id in OPTIONS:
            delta = delta_by_identity[(scenario_id, option_id)]
            cell = by_option[option_id]
            expected = {
                "baselineOptionId": "D0",
                "deltaTco": cell["expectedTco"] - baseline["expectedTco"],
                "deltaStockoutPp": round((cell["stockoutProbability"] - baseline["stockoutProbability"]) * 100, 10),
                "deltaServicePp": round((cell["serviceLevel"] - baseline["serviceLevel"]) * 100, 10),
                "deltaCashP90": cell["cashOutflowP90"] - baseline["cashOutflowP90"],
            }
            for field, value in expected.items():
                if delta.get(field) != value:
                    _fail(f"delta {scenario_id}/{option_id}.{field} is not the true D0-relative value")


def _check_selections(request: dict[str, Any], data: dict[str, Any], matrix: dict[str, list[dict[str, Any]]]) -> None:
    selections = data["selections"]
    if set(selections) != set(SCENARIOS):
        _fail("selections must cover exactly the three scenarios")
    risk = request["riskThreshold"]
    budget = request["budgetCeilingUsd"]
    for scenario_id in SCENARIOS:
        selection = selections[scenario_id]
        if selection["scenarioId"] != scenario_id:
            _fail(f"selection {scenario_id} has a mismatched scenarioId")
        by_option = {cell["optionId"]: cell for cell in matrix[scenario_id]}
        eligible: list[dict[str, Any]] = []
        violations: list[dict[str, str]] = []
        for option_id in OPTIONS:
            cell = by_option[option_id]
            failed: list[str] = []
            if not cell["feasible"]:
                failed.append("infeasible")
            if cell["stockoutProbability"] > risk:
                failed.append("stockout_threshold")
            if cell["cashOutflowP90"] > budget:
                failed.append("cash_ceiling")
            violations.extend({"optionId": option_id, "code": code} for code in failed)
            if not failed:
                eligible.append(cell)
        if eligible:
            expected_status = "selected"
            expected_option: str | None = min(eligible, key=lambda cell: (cell["expectedTco"], cell["optionId"]))["optionId"]
        else:
            expected_status, expected_option = "no_feasible_option", None
        if selection["status"] != expected_status or selection["recommendedOptionId"] != expected_option or selection["constraintViolations"] != violations:
            _fail(f"selection {scenario_id} is not derived from feasible cells and request risk/budget")


def validate_mc_response(request: dict, response: dict, headers: dict | None = None) -> dict:
    """Validate a Jinzhu v2 unreviewed-development HTTP MC success response.

    Args:
        request: Exact v1 simulation request sent to ``POST /api/simulate``.
        response: Decoded JSON v2 success envelope returned by the HTTP service.
        headers: Optional response headers.  If supplied, all three development
            markers and an exact ``X-Request-Id`` are mandatory.

    Returns:
        A compact **development-only** audit summary with matrix/sample coverage,
        IDs, and canonical raw-JSON hashes.  It never states that the result is
        reviewed, approved, or decision-ready.

    Raises:
        ValueError: Any shape, provenance, metadata, aggregate, delta, selection,
            request binding, or header inconsistency.  No field is repaired.
    """
    if not isinstance(request, dict) or not isinstance(response, dict):
        _fail("request and response must both be dictionaries")
    # Hash before schema/model processing so 1 and 1.0 remain distinguishable.
    request_sha = canonical_sha(request)
    response_sha = canonical_sha(response)
    scenario_by_id, option_by_id = _request_maps(request)
    _reject_legacy_or_reviewed(response)
    _validate_schema(response)
    _check_headers(headers, response["requestId"])
    data, simulation = _check_execution_context(response)
    if simulation["seed"] != request["seed"]:
        _fail("simulation.seed must exactly match request.seed")

    matrix = simulation["matrix"]
    if set(matrix) != set(SCENARIOS):
        _fail("matrix must cover exactly baseline, demand-drop, and lead-stress")
    if set(data["traces"]) != set(SCENARIOS) or any(set(data["traces"][scenario]) != set(OPTIONS) for scenario in SCENARIOS):
        _fail("traces must cover every fixed scenario and option before reading run identity")
    sample_weeks = 0
    reference_identity = data["traces"]["baseline"]["D0"]["runIdentity"]
    reference_contract = {p["key"]: p for p in data["traces"]["baseline"]["D0"]["parameters"] if p["key"].startswith("contract.")}
    for scenario_id in SCENARIOS:
        cells = matrix[scenario_id]
        cell_by_option = {cell.get("optionId"): cell for cell in cells if isinstance(cell, dict)}
        if len(cells) != 3 or len(cell_by_option) != 3 or set(cell_by_option) != set(OPTIONS):
            _fail(f"matrix {scenario_id} must contain exactly one D0/D1/D2 cell")
        traces = data["traces"].get(scenario_id)
        if not isinstance(traces, dict) or set(traces) != set(OPTIONS):
            _fail(f"traces {scenario_id} must contain exactly D0/D1/D2")
        for option_id in OPTIONS:
            if traces[option_id]["runIdentity"] != reference_identity:
                _fail("one simulation cannot carry different per-cell run/policy/contract identities")
            current_contract = {p["key"]: p for p in traces[option_id]["parameters"] if p["key"].startswith("contract.")}
            if current_contract != reference_contract:
                _fail("one simulation cannot carry different per-cell contract values/provenance")
            sample_weeks += _check_trace(
                traces[option_id], cell_by_option[option_id], scenario_by_id[scenario_id], option_by_id[option_id],
                scenario_id, option_id, simulation,
            )
    _check_deltas(data, matrix)
    _check_selections(request, data, matrix)
    if sample_weeks != 936:
        _fail(f"complete nine-cell sample-path coverage must be 936 weeks, got {sample_weeks}")
    return {
        "kind": "CAUSORA_DAY3_UNREVIEWED_MC_HTTP_VALIDATION_V1",
        "devOnly": True,
        "decisionReady": False,
        "matrixCells": 9,
        "sampleWeeks": sample_weeks,
        "simulationId": simulation["simulationId"],
        "dataVersion": simulation["dataVersion"],
        "requestSha256": request_sha,
        "responseSha256": response_sha,
    }


__all__ = ["MCValidationError", "canonical_sha", "resolve_pointer", "validate_mc_response"]
