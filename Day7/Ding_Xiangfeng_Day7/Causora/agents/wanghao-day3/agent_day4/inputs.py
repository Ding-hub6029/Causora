"""Strict Day 4 input boundary for reviewed Simulation v2 traces.

No provider is called here.  The functions validate a detached current simulation,
then construct small role-specific projections.  They intentionally do not expose
raw source paths, request prose, review comments, or full traces to a model.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable
import copy
import math
import re

from .evidence import (
    EvidenceValidationError,
    canonical_sha256,
    enrich_evidence,
    public_evidence,
    validate_evidence_records,
)


SCENARIO_IDS = ("baseline", "demand-drop", "lead-stress")
OPTION_IDS = ("D0", "D1", "D2")
COMPONENT_KEYS = ("purchase", "holding", "stockoutLoss", "renewalPremium", "terminationFee")
PUBLIC_TOKENS = ("delta_tco", "stockout_probability", "cash_outflow_p90")
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")

_REQUIRED_CONTRACT_FIELDS = frozenset((
    "decisionDate", "renewalDate", "daysToRenewal", "renewalNoticeDays", "noticeDeadline", "noticeSent",
    "noticeRecordSource", "renewalLocked", "renewalTermMonths", "renewalPriceIncreasePct", "minPurchaseShareA",
    "forecastBasis", "lockedForecastUnits24m", "minPurchaseUnitsA", "terminationFeeUsd", "evidenceIds",
))
_TRACE_CONTRACT_FIELDS = {
    "contract.renewalLocked": "renewalLocked",
    "contract.renewalPriceIncreasePct": "renewalPriceIncreasePct",
    "contract.minPurchaseUnitsA": "minPurchaseUnitsA",
    "contract.terminationFeeUsd": "terminationFeeUsd",
}
_PROVENANCE_STATUS = {
    "reviewed_contract": "reviewed",
    "unreviewed_development_contract": "unreviewed_development_only",
    "approved_operating_assumption": "approved",
    "unreviewed_development_assumption": "unreviewed_development_only",
    "observed_synthetic_dataset": "observed",
    "derived_formula": "derived",
}


class InputValidationError(ValueError):
    """Raised before any model input is created from a simulation record."""


class FrozenDict(dict):
    """A recursively frozen dict which remains JSON-serialisable as a mapping."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        dict.__init__(self)
        dict.update(self, *args, **kwargs)

    @staticmethod
    def _immutable(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError("VerifiedRun data are immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable

    def __reduce__(self):  # pragma: no cover - defensive support for serializers/copy
        return (FrozenDict, (dict(self),))


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return FrozenDict({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise InputValidationError(f"run contains unsupported non-JSON value {type(value).__name__}")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class VerifiedRun:
    """Immutable detached input record; constructed only by :func:`validate_run`.

    ``contract`` can be the bare reviewed contract or a reviewed-bundle object
    containing ``contract`` and ``fieldProvenance``.  Pass a separate bundle to
    ``validate_run(..., reviewed_bundle=...)`` when it is supplied by the caller.
    """

    simulation_request: Mapping[str, Any]
    simulation_response: Mapping[str, Any]
    contract: Mapping[str, Any]
    evidence: tuple[Mapping[str, Any], ...]
    source_root: Path
    simulation_request_id: str
    pin_snapshot_sha256: str = ""

    @property
    def reviewed(self) -> bool:
        data = self.simulation_response.get("data", {})
        context = data.get("executionContext", {}) if isinstance(data, Mapping) else {}
        return context.get("mode") == "reviewed_release_gated"


def make_verified_run(
    *,
    simulation_request: Mapping[str, Any],
    simulation_response: Mapping[str, Any],
    contract: Mapping[str, Any],
    evidence: Iterable[Mapping[str, Any]] = (),
    source_root: Path | str,
    simulation_request_id: str,
) -> VerifiedRun:
    """Build an untrusted candidate that must still be passed to ``validate_run``."""
    return VerifiedRun(
        simulation_request=copy.deepcopy(dict(simulation_request)),
        simulation_response=copy.deepcopy(dict(simulation_response)),
        contract=copy.deepcopy(dict(contract)),
        evidence=tuple(copy.deepcopy(dict(item)) for item in evidence),
        source_root=Path(source_root),
        simulation_request_id=simulation_request_id,
    )


def _fail(message: str) -> None:
    raise InputValidationError(message)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{label}: expected object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, (list, tuple)):
        _fail(f"{label}: expected array")
    return list(value)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label}: expected non-empty text")
    return value


def _integer(value: Any, label: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(f"{label}: expected integer")
    if minimum is not None and value < minimum:
        _fail(f"{label}: below minimum")
    return value


def _number(value: Any, label: str, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        _fail(f"{label}: expected finite number")
    numeric = float(value)
    if minimum is not None and numeric < minimum or maximum is not None and numeric > maximum:
        _fail(f"{label}: outside allowed range")
    return numeric


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        _fail(f"{label}: expected boolean")
    return value


def _exact_keys(value: Mapping[str, Any], required: Iterable[str], label: str) -> None:
    expected = set(required)
    actual = set(value)
    if actual != expected:
        _fail(f"{label}: fields differ (missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)})")


def _same_number(actual: Any, expected: float | int, label: str, tolerance: float = 1e-10) -> None:
    if not math.isclose(_number(actual, label), float(expected), rel_tol=0.0, abs_tol=tolerance):
        _fail(f"{label}: differs from recomputed value")


def _canonical(value: Any) -> str:
    try:
        return canonical_sha256(_thaw(value))
    except (TypeError, ValueError) as exc:
        raise InputValidationError("run data are not canonical JSON") from exc


def _request_maps(request: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    _exact_keys(request, ("schemaVersion", "datasetId", "scenarios", "options", "seed", "riskThreshold", "budgetCeilingUsd"), "simulation_request")
    if request.get("schemaVersion") != "causora.contract.v1":
        _fail("simulation_request.schemaVersion: expected causora.contract.v1")
    _text(request.get("datasetId"), "simulation_request.datasetId")
    _integer(request.get("seed"), "simulation_request.seed", 0)
    _number(request.get("riskThreshold"), "simulation_request.riskThreshold", 0, 1)
    _integer(request.get("budgetCeilingUsd"), "simulation_request.budgetCeilingUsd", 0)
    scenarios = _list(request.get("scenarios"), "simulation_request.scenarios")
    options = _list(request.get("options"), "simulation_request.options")
    scenario_map: dict[str, Mapping[str, Any]] = {}
    option_map: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(scenarios):
        scenario = _mapping(raw, f"request.scenarios[{index}]")
        _exact_keys(
            scenario,
            ("id", "label", "tag", "demandShock", "demandUnits24m", "leadTime", "leadTimeMultiplier", "description"),
            f"request.scenarios[{index}]",
        )
        sid = _text(scenario.get("id"), f"request.scenarios[{index}].id")
        _text(scenario.get("label"), f"request.scenarios[{index}].label")
        _text(scenario.get("tag"), f"request.scenarios[{index}].tag")
        _integer(scenario.get("demandUnits24m"), f"request.scenarios[{index}].demandUnits24m", 0)
        _number(scenario.get("demandShock"), f"request.scenarios[{index}].demandShock")
        _number(scenario.get("leadTimeMultiplier"), f"request.scenarios[{index}].leadTimeMultiplier", 0)
        _text(scenario.get("leadTime"), f"request.scenarios[{index}].leadTime")
        _text(scenario.get("description"), f"request.scenarios[{index}].description")
        if sid in scenario_map:
            _fail("simulation_request.scenarios: duplicate ID")
        scenario_map[sid] = scenario
    for index, raw in enumerate(options):
        option = _mapping(raw, f"request.options[{index}]")
        _exact_keys(
            option,
            ("id", "label", "shareA", "terminateA", "allocation", "short", "description"),
            f"request.options[{index}]",
        )
        oid = _text(option.get("id"), f"request.options[{index}].id")
        _text(option.get("label"), f"request.options[{index}].label")
        _number(option.get("shareA"), f"request.options[{index}].shareA", 0, 1)
        _bool(option.get("terminateA"), f"request.options[{index}].terminateA")
        _text(option.get("allocation"), f"request.options[{index}].allocation")
        _text(option.get("short"), f"request.options[{index}].short")
        _text(option.get("description"), f"request.options[{index}].description")
        if oid in option_map:
            _fail("simulation_request.options: duplicate ID")
        option_map[oid] = option
    if set(scenario_map) != set(SCENARIO_IDS) or len(scenario_map) != 3 or set(option_map) != set(OPTION_IDS) or len(option_map) != 3:
        _fail("simulation_request: requires the current baseline/demand-drop/lead-stress and D0/D1/D2 identities")
    return scenario_map, option_map


def _contract_payload(contract_or_bundle: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any] | None]:
    if "contract" in contract_or_bundle:
        bundle_contract = _mapping(contract_or_bundle.get("contract"), "reviewed_bundle.contract")
        provenance = contract_or_bundle.get("fieldProvenance")
        if provenance is not None:
            provenance = _mapping(provenance, "reviewed_bundle.fieldProvenance")
        return bundle_contract, provenance
    return contract_or_bundle, None


def _validate_contract(contract: Mapping[str, Any], label: str = "contract") -> None:
    _exact_keys(contract, _REQUIRED_CONTRACT_FIELDS, label)
    try:
        decision = date.fromisoformat(_text(contract.get("decisionDate"), f"{label}.decisionDate"))
        renewal = date.fromisoformat(_text(contract.get("renewalDate"), f"{label}.renewalDate"))
        deadline = date.fromisoformat(_text(contract.get("noticeDeadline"), f"{label}.noticeDeadline"))
    except ValueError as exc:
        raise InputValidationError(f"{label}: dates must be ISO calendar dates") from exc
    days = _integer(contract.get("daysToRenewal"), f"{label}.daysToRenewal", 0)
    notice_days = _integer(contract.get("renewalNoticeDays"), f"{label}.renewalNoticeDays", 0)
    if days != (renewal - decision).days or deadline != renewal.fromordinal(renewal.toordinal() - notice_days):
        _fail(f"{label}: date derivations do not reconcile")
    notice_sent = _bool(contract.get("noticeSent"), f"{label}.noticeSent")
    _text(contract.get("noticeRecordSource"), f"{label}.noticeRecordSource")
    expected_locked = days < notice_days and not notice_sent
    if _bool(contract.get("renewalLocked"), f"{label}.renewalLocked") is not expected_locked:
        _fail(f"{label}.renewalLocked: must remain the conditional date/notice result")
    _integer(contract.get("renewalTermMonths"), f"{label}.renewalTermMonths", 1)
    _number(contract.get("renewalPriceIncreasePct"), f"{label}.renewalPriceIncreasePct", 0, 1)
    share = _number(contract.get("minPurchaseShareA"), f"{label}.minPurchaseShareA", 0, 1)
    if contract.get("forecastBasis") != "locked-at-renewal":
        _fail(f"{label}.forecastBasis: expected locked-at-renewal")
    locked_forecast = _integer(contract.get("lockedForecastUnits24m"), f"{label}.lockedForecastUnits24m", 0)
    min_purchase = _integer(contract.get("minPurchaseUnitsA"), f"{label}.minPurchaseUnitsA", 0)
    if min_purchase != int(round(share * locked_forecast)):
        _fail(f"{label}.minPurchaseUnitsA: does not match fixed locked forecast floor")
    _integer(contract.get("terminationFeeUsd"), f"{label}.terminationFeeUsd", 0)
    evidence_ids = _list(contract.get("evidenceIds"), f"{label}.evidenceIds")
    if set(evidence_ids) != {"EV-014", "EV-019", "EV-021", "EV-024", "EV-027"} or len(evidence_ids) != 5:
        _fail(f"{label}.evidenceIds: requires exactly the five public evidence IDs")


def _validate_bundle_provenance(
    field_provenance: Mapping[str, Any] | None,
    contract: Mapping[str, Any],
    *,
    reviewed: bool,
) -> None:
    if field_provenance is None:
        return
    _exact_keys(field_provenance, _REQUIRED_CONTRACT_FIELDS, "reviewed_bundle.fieldProvenance")
    for field, raw in field_provenance.items():
        entry = _mapping(raw, f"fieldProvenance.{field}")
        required = {"evidenceId", "sourceFile", "sourceSha256", "reviewItemId", "derivedFromReviewItemIds", "status"}
        _exact_keys(entry, required, f"fieldProvenance.{field}")
        _text(entry.get("evidenceId"), f"fieldProvenance.{field}.evidenceId")
        _text(entry.get("sourceFile"), f"fieldProvenance.{field}.sourceFile")
        source_hash = _text(entry.get("sourceSha256"), f"fieldProvenance.{field}.sourceSha256")
        if not _SHA256_RE.fullmatch(source_hash):
            _fail(f"fieldProvenance.{field}.sourceSha256: expected SHA-256")
        _text(entry.get("reviewItemId"), f"fieldProvenance.{field}.reviewItemId")
        dependencies = _list(entry.get("derivedFromReviewItemIds"), f"fieldProvenance.{field}.derivedFromReviewItemIds")
        if not dependencies or any(not isinstance(item, str) or not item for item in dependencies):
            _fail(f"fieldProvenance.{field}.derivedFromReviewItemIds: expected non-empty IDs")
        if reviewed and entry.get("status") != "reviewed":
            _fail(f"fieldProvenance.{field}: official run requires reviewed field provenance")


def _validate_context(data: Mapping[str, Any], *, require_reviewed: bool) -> tuple[bool, Mapping[str, Any]]:
    context = _mapping(data.get("executionContext"), "response.data.executionContext")
    _exact_keys(context, ("mode", "banner", "humanReviewStatus", "policyStatus", "contractReleaseStatus", "decisionReady"), "executionContext")
    mode = context.get("mode")
    banner = _text(context.get("banner"), "executionContext.banner")
    reviewed = mode == "reviewed_release_gated"
    if reviewed:
        if (context.get("humanReviewStatus"), context.get("policyStatus"), context.get("contractReleaseStatus"), context.get("decisionReady")) != ("reviewed", "approved", "released", True):
            _fail("executionContext: reviewed run lacks review/policy/release readiness")
        if "unreviewed" in banner.lower():
            _fail("executionContext: reviewed banner cannot contain unreviewed")
    elif mode == "unreviewed_development_only":
        if (context.get("humanReviewStatus"), context.get("policyStatus"), context.get("contractReleaseStatus"), context.get("decisionReady")) != ("not_reviewed_development_only", "unapproved_development_only", "not_released_development_only", False):
            _fail("executionContext: unreviewed development status mismatch")
        if "UNREVIEWED" not in banner.upper():
            _fail("executionContext: development banner lacks irreversible marker")
    else:
        _fail("executionContext.mode: unsupported execution mode")
    if require_reviewed and not reviewed:
        _fail("official Day 4 input requires a reviewed, decision-ready v2 context")
    return reviewed, context


def _validate_cell(cell: Mapping[str, Any], *, scenario_id: str, option: Mapping[str, Any], prices: Mapping[str, Any], label: str) -> None:
    _exact_keys(cell, ("optionId", "feasible", "expectedTco", "stockoutProbability", "serviceLevel", "cashOutflowP90", "breakdown", "unitsFromA", "unitsFromB", "tone"), label)
    _text(cell.get("optionId"), f"{label}.optionId")
    _bool(cell.get("feasible"), f"{label}.feasible")
    expected_tco = _integer(cell.get("expectedTco"), f"{label}.expectedTco", 0)
    _number(cell.get("stockoutProbability"), f"{label}.stockoutProbability", 0, 1)
    _number(cell.get("serviceLevel"), f"{label}.serviceLevel", 0, 1)
    _integer(cell.get("cashOutflowP90"), f"{label}.cashOutflowP90", 0)
    units_a = _integer(cell.get("unitsFromA"), f"{label}.unitsFromA", 0)
    units_b = _integer(cell.get("unitsFromB"), f"{label}.unitsFromB", 0)
    if cell.get("tone") not in {"neutral", "recommended", "risk"}:
        _fail(f"{label}.tone: unsupported")
    breakdown = _mapping(cell.get("breakdown"), f"{label}.breakdown")
    _exact_keys(breakdown, COMPONENT_KEYS, f"{label}.breakdown")
    if sum(_integer(breakdown.get(key), f"{label}.breakdown.{key}", 0) for key in COMPONENT_KEYS) != expected_tco:
        _fail(f"{label}: breakdown does not sum to expected TCO")
    price_a = _number(prices.get("A"), "simulation.unitPricesUsd.A", 0)
    price_b = _number(prices.get("B"), "simulation.unitPricesUsd.B", 0)
    if abs(_integer(breakdown.get("purchase"), f"{label}.breakdown.purchase") - (units_a * price_a + units_b * price_b)) > 0.50000001:
        _fail(f"{label}: purchase does not reconcile to units and unit prices")
    total = units_a + units_b
    if total <= 0:
        _fail(f"{label}: allocation has no units")
    _same_number(units_a / total, _number(option.get("shareA"), "option.shareA"), f"{label}: allocation")


def _validate_deltas_and_selections(
    request: Mapping[str, Any], data: Mapping[str, Any], matrix: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> None:
    deltas = _list(data.get("deltas"), "response.data.deltas")
    if len(deltas) != 9:
        _fail("response.data.deltas: requires all nine scenario/option deltas")
    delta_map: dict[tuple[str, str], Mapping[str, Any]] = {}
    for index, raw in enumerate(deltas):
        item = _mapping(raw, f"deltas[{index}]")
        _exact_keys(item, ("scenarioId", "optionId", "baselineOptionId", "deltaTco", "deltaStockoutPp", "deltaServicePp", "deltaCashP90"), f"deltas[{index}]")
        key = (_text(item.get("scenarioId"), f"deltas[{index}].scenarioId"), _text(item.get("optionId"), f"deltas[{index}].optionId"))
        if key in delta_map:
            _fail("response.data.deltas: duplicate identity")
        delta_map[key] = item
    if set(delta_map) != {(sid, oid) for sid in SCENARIO_IDS for oid in OPTION_IDS}:
        _fail("response.data.deltas: identities differ from current request")
    for sid in SCENARIO_IDS:
        baseline = matrix[sid]["D0"]
        for oid in OPTION_IDS:
            item = delta_map[(sid, oid)]
            cell = matrix[sid][oid]
            if item.get("baselineOptionId") != "D0":
                _fail(f"delta {sid}/{oid}: baseline must be D0")
            expected = {
                "deltaTco": cell["expectedTco"] - baseline["expectedTco"],
                "deltaStockoutPp": round((cell["stockoutProbability"] - baseline["stockoutProbability"]) * 100, 10),
                "deltaServicePp": round((cell["serviceLevel"] - baseline["serviceLevel"]) * 100, 10),
                "deltaCashP90": cell["cashOutflowP90"] - baseline["cashOutflowP90"],
            }
            for key, value in expected.items():
                if isinstance(value, float):
                    _same_number(item.get(key), value, f"delta {sid}/{oid}.{key}")
                elif item.get(key) != value:
                    _fail(f"delta {sid}/{oid}.{key}: differs from D0-relative recomputation")
    selections = _mapping(data.get("selections"), "response.data.selections")
    if set(selections) != set(SCENARIO_IDS):
        _fail("response.data.selections: must cover the current three scenarios")
    risk, budget = request["riskThreshold"], request["budgetCeilingUsd"]
    for sid in SCENARIO_IDS:
        selection = _mapping(selections[sid], f"selections.{sid}")
        _exact_keys(selection, ("scenarioId", "status", "recommendedOptionId", "constraintViolations"), f"selections.{sid}")
        if selection.get("scenarioId") != sid:
            _fail(f"selections.{sid}.scenarioId: stale scenario")
        violations: list[dict[str, str]] = []
        eligible: list[Mapping[str, Any]] = []
        for oid in OPTION_IDS:
            cell = matrix[sid][oid]
            failures: list[str] = []
            if cell["feasible"] is not True:
                failures.append("infeasible")
            if cell["stockoutProbability"] > risk:
                failures.append("stockout_threshold")
            if cell["cashOutflowP90"] > budget:
                failures.append("cash_ceiling")
            violations.extend({"optionId": oid, "code": code} for code in failures)
            if not failures:
                eligible.append(cell)
        actual = _list(selection.get("constraintViolations"), f"selections.{sid}.constraintViolations")
        if actual != violations:
            _fail(f"selections.{sid}: constraints do not recompute from current matrix/request")
        if eligible:
            winner = min(eligible, key=lambda row: (row["expectedTco"], row["optionId"]))["optionId"]
            if selection.get("status") != "selected" or selection.get("recommendedOptionId") != winner:
                _fail(f"selections.{sid}: selection does not follow current constraint/TCO rule")
        elif selection.get("status") != "no_feasible_option" or selection.get("recommendedOptionId") is not None:
            _fail(f"selections.{sid}: no-feasible result must not invent a winner")


def _validate_trace(
    trace: Mapping[str, Any], cell: Mapping[str, Any], *, scenario_id: str, option_id: str, scenario: Mapping[str, Any],
    option: Mapping[str, Any], request_seed: int, simulation: Mapping[str, Any], reviewed: bool,
    contract: Mapping[str, Any], reference_identity: Mapping[str, Any] | None,
    reference_contract_parameters: Mapping[str, Any] | None,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    label = f"traces.{scenario_id}.{option_id}"
    _exact_keys(trace, ("traceSchemaVersion", "simulationId", "dataVersion", "formulaVersion", "scenarioId", "optionId", "runIdentity", "parameters", "components", "expectedTcoUsd", "stockoutProbability", "serviceLevel", "cashOutflowP90", "summaryRoundingRule", "samplePath"), label)
    if (trace.get("traceSchemaVersion"), trace.get("simulationId"), trace.get("dataVersion"), trace.get("formulaVersion"), trace.get("scenarioId"), trace.get("optionId")) != ("causora.formula-trace.v1", simulation["simulationId"], simulation["dataVersion"], "tco-v1", scenario_id, option_id):
        _fail(f"{label}: identity differs from current matrix run")
    identity = _mapping(trace.get("runIdentity"), f"{label}.runIdentity")
    _exact_keys(identity, ("executionMode", "reviewRecordId", "reviewRecordSha256", "contractPayloadSha256", "policyApprovalReference", "policyConfigurationId", "policySha256", "contractApprovalReference", "contractReleaseRecordSha256"), f"{label}.runIdentity")
    if identity.get("executionMode") != ("reviewed_release_gated" if reviewed else "unreviewed_development_only"):
        _fail(f"{label}.runIdentity.executionMode: differs from response context")
    for key in ("contractPayloadSha256", "policySha256", "contractReleaseRecordSha256"):
        value = _text(identity.get(key), f"{label}.runIdentity.{key}")
        if not _SHA256_RE.fullmatch(value):
            _fail(f"{label}.runIdentity.{key}: expected SHA-256")
    for key in ("policyApprovalReference", "policyConfigurationId", "contractApprovalReference"):
        _text(identity.get(key), f"{label}.runIdentity.{key}")
    if reviewed:
        _text(identity.get("reviewRecordId"), f"{label}.runIdentity.reviewRecordId")
        review_hash = _text(identity.get("reviewRecordSha256"), f"{label}.runIdentity.reviewRecordSha256")
        if not _SHA256_RE.fullmatch(review_hash):
            _fail(f"{label}.runIdentity.reviewRecordSha256: missing reviewed record hash")
    elif identity.get("reviewRecordId") is not None or identity.get("reviewRecordSha256") is not None:
        _fail(f"{label}.runIdentity: development trace cannot claim review")
    if reference_identity is not None and dict(identity) != dict(reference_identity):
        _fail(f"{label}.runIdentity: all nine cells must carry one current release identity")
    if identity.get("contractPayloadSha256") != _canonical(contract):
        _fail(f"{label}.runIdentity.contractPayloadSha256: differs from complete canonical contract payload")
    if trace.get("expectedTcoUsd") != cell["expectedTco"]:
        _fail(f"{label}.expectedTcoUsd: differs from matrix")
    components = _list(trace.get("components"), f"{label}.components")
    if len(components) != 5:
        _fail(f"{label}.components: requires exactly five costs")
    keys: set[str] = set()
    for index, raw in enumerate(components):
        component = _mapping(raw, f"{label}.components[{index}]")
        _exact_keys(component, ("key", "formula", "inputKeys", "valueUsd", "roundingAudit"), f"{label}.components[{index}]")
        key = _text(component.get("key"), f"{label}.components[{index}].key")
        if key not in COMPONENT_KEYS or key in keys:
            _fail(f"{label}.components: missing/duplicate cost component")
        keys.add(key)
        _text(component.get("formula"), f"{label}.components[{index}].formula")
        _integer(component.get("valueUsd"), f"{label}.components[{index}].valueUsd", 0)
        if component["valueUsd"] != cell["breakdown"][key]:
            _fail(f"{label}.components[{index}]: differs from matrix cost")
        inputs = _list(component.get("inputKeys"), f"{label}.components[{index}].inputKeys")
        if not inputs or any(not isinstance(value, str) or not value for value in inputs):
            _fail(f"{label}.components[{index}].inputKeys: expected named inputs")
        audit = _mapping(component.get("roundingAudit"), f"{label}.components[{index}].roundingAudit")
        _exact_keys(audit, ("rawMeanUsd", "displayedValueUsd", "displayedMinusRawMeanUsd", "method"), f"{label}.components[{index}].roundingAudit")
        try:
            raw_mean, difference = float(_text(audit.get("rawMeanUsd"), "roundingAudit.rawMeanUsd")), float(_text(audit.get("displayedMinusRawMeanUsd"), "roundingAudit.displayedMinusRawMeanUsd"))
        except ValueError as exc:
            raise InputValidationError(f"{label}.roundingAudit: expected finite decimal text") from exc
        if not math.isfinite(raw_mean) or not math.isfinite(difference) or audit.get("displayedValueUsd") != component["valueUsd"] or abs(component["valueUsd"] - raw_mean - difference) > 1e-6:
            _fail(f"{label}.roundingAudit: does not reconcile")
        _text(audit.get("method"), f"{label}.roundingAudit.method")
    if keys != set(COMPONENT_KEYS) or sum(component["valueUsd"] for component in components) != cell["expectedTco"]:
        _fail(f"{label}.components: all five values must reconcile to TCO")
    parameters = _list(trace.get("parameters"), f"{label}.parameters")
    if not parameters:
        _fail(f"{label}.parameters: field provenance closure is missing")
    parameter_map: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(parameters):
        parameter = _mapping(raw, f"{label}.parameters[{index}]")
        _exact_keys(parameter, ("key", "value", "unit", "provenance"), f"{label}.parameters[{index}]")
        key = _text(parameter.get("key"), f"{label}.parameters[{index}].key")
        if key in parameter_map:
            _fail(f"{label}.parameters: duplicate key {key}")
        if not isinstance(parameter.get("value"), (str, int, float, bool)) or isinstance(parameter.get("value"), float) and not math.isfinite(parameter["value"]):
            _fail(f"{label}.parameters[{index}].value: invalid scalar")
        _text(parameter.get("unit"), f"{label}.parameters[{index}].unit")
        provenance = _mapping(parameter.get("provenance"), f"{label}.parameters[{index}].provenance")
        _exact_keys(provenance, ("kind", "status", "sourceId", "sourceFile", "sourceSha256", "evidenceIds", "reviewRecordId", "reviewRecordSha256", "note"), f"{label}.parameters[{index}].provenance")
        kind = _text(provenance.get("kind"), f"{label}.parameters[{index}].provenance.kind")
        if kind not in _PROVENANCE_STATUS or provenance.get("status") != _PROVENANCE_STATUS[kind]:
            _fail(f"{label}.parameters[{index}].provenance: kind/status mismatch")
        _text(provenance.get("sourceId"), f"{label}.parameters[{index}].provenance.sourceId")
        _text(provenance.get("note"), f"{label}.parameters[{index}].provenance.note")
        evidence_ids = _list(provenance.get("evidenceIds"), f"{label}.parameters[{index}].provenance.evidenceIds")
        if any(not isinstance(item, str) or not item for item in evidence_ids):
            _fail(f"{label}.parameters[{index}].provenance.evidenceIds: invalid IDs")
        needs_source = kind in {"reviewed_contract", "approved_operating_assumption", "observed_synthetic_dataset", "unreviewed_development_contract", "unreviewed_development_assumption"}
        if needs_source:
            # Backend v2 permits a policy approval to be fileless while still
            # requiring its policy SHA; all other source-backed kinds name a file.
            if kind != "approved_operating_assumption" or provenance.get("sourceFile") is not None:
                _text(provenance.get("sourceFile"), f"{label}.parameters[{index}].provenance.sourceFile")
            source_hash = _text(provenance.get("sourceSha256"), f"{label}.parameters[{index}].provenance.sourceSha256")
            if not _SHA256_RE.fullmatch(source_hash):
                _fail(f"{label}.parameters[{index}].provenance.sourceSha256: expected SHA-256")
        if reviewed:
            if kind.startswith("unreviewed"):
                _fail(f"{label}.parameters[{index}]: reviewed run has unreviewed provenance")
            if kind == "reviewed_contract":
                if not evidence_ids or provenance.get("reviewRecordId") != identity["reviewRecordId"] or provenance.get("reviewRecordSha256") != identity["reviewRecordSha256"]:
                    _fail(f"{label}.parameters[{index}]: reviewed field provenance is not bound to run review record")
            elif provenance.get("reviewRecordId") is not None or provenance.get("reviewRecordSha256") is not None:
                _fail(f"{label}.parameters[{index}]: only reviewed contract provenance may cite review")
        elif provenance.get("reviewRecordId") is not None or provenance.get("reviewRecordSha256") is not None:
            _fail(f"{label}.parameters[{index}]: development provenance cannot cite review")
        if key.startswith("contract."):
            expected_kind = "reviewed_contract" if reviewed else "unreviewed_development_contract"
            if kind != expected_kind:
                _fail(f"{label}.parameters[{index}]: contract field lacks mode-correct provenance")
        parameter_map[key] = parameter
    unresolved = {input_key for component in components for input_key in component["inputKeys"]} - set(parameter_map)
    if unresolved:
        _fail(f"{label}.components: unresolved parameter inputs {sorted(unresolved)}")
    contract_parameters = {key: parameter_map[key] for key in parameter_map if key.startswith("contract.")}
    for parameter_key, contract_key in _TRACE_CONTRACT_FIELDS.items():
        parameter = contract_parameters.get(parameter_key)
        if parameter is None or parameter["value"] != contract[contract_key]:
            _fail(f"{label}.parameters: {parameter_key} differs from complete contract payload")
    # The trace is only current when every native request-derived parameter still
    # equals the exact request that produced the matrix.  A matching seed/ID and
    # contract hash cannot authorise a stale scenario shock, demand, lead time,
    # or option allocation from a prior calculation.
    request_parameters: dict[str, tuple[Any, str]] = {
        "scenario.demandShock": (scenario["demandShock"], "percent"),
        "scenario.demandUnits24m": (scenario["demandUnits24m"], "units/24m"),
        "scenario.leadTimeMultiplier": (scenario["leadTimeMultiplier"], "multiplier"),
        "option.shareA": (option["shareA"], "fraction"),
        "option.terminateA": (option["terminateA"], "boolean"),
    }
    for parameter_key, (expected_value, expected_unit) in request_parameters.items():
        parameter = parameter_map.get(parameter_key)
        if parameter is None:
            _fail(f"{label}.parameters: missing current request parameter {parameter_key}")
        if parameter["unit"] != expected_unit:
            _fail(f"{label}.parameters: {parameter_key} unit differs from current request")
        if isinstance(expected_value, bool):
            if parameter["value"] is not expected_value:
                _fail(f"{label}.parameters: {parameter_key} differs from current request")
        else:
            _same_number(parameter["value"], expected_value, f"{label}.parameters: {parameter_key}")
    # Current native traces do not expose a seed parameter, but fail closed when
    # a future trace does: it must bind to the request seed, not a stale run.
    for parameter_key in ("simulation.seed", "run.seed", "request.seed", "configuration.seed"):
        if parameter_key in parameter_map:
            parameter = parameter_map[parameter_key]
            if parameter["unit"] not in {"seed", "integer"} or parameter["value"] != request_seed:
                _fail(f"{label}.parameters: {parameter_key} differs from current request seed")
    if reference_contract_parameters is not None and _canonical(contract_parameters) != _canonical(reference_contract_parameters):
        _fail(f"{label}.parameters: contract values/provenance differ across current run cells")
    probability = _mapping(trace.get("stockoutProbability"), f"{label}.stockoutProbability")
    _exact_keys(probability, ("value", "numeratorStockoutRuns", "denominatorRuns", "definition"), f"{label}.stockoutProbability")
    runs = _integer(simulation.get("monteCarloRuns"), "simulation.monteCarloRuns", 1)
    numerator = _integer(probability.get("numeratorStockoutRuns"), f"{label}.stockoutProbability.numeratorStockoutRuns", 0)
    denominator = _integer(probability.get("denominatorRuns"), f"{label}.stockoutProbability.denominatorRuns", 1)
    if probability.get("definition") != "trials_with_at_least_one_lost_unit / monteCarloRuns" or denominator != runs or numerator > denominator:
        _fail(f"{label}.stockoutProbability: invalid Monte Carlo basis")
    _same_number(probability.get("value"), numerator / denominator, f"{label}.stockoutProbability.value", 1e-12)
    _same_number(cell["stockoutProbability"], numerator / denominator, f"{label}.matrix.stockoutProbability", 1e-12)
    service = _mapping(trace.get("serviceLevel"), f"{label}.serviceLevel")
    _exact_keys(service, ("value", "fulfilledUnitsAllRuns", "demandUnitsAllRuns", "definition"), f"{label}.serviceLevel")
    fulfilled = _integer(service.get("fulfilledUnitsAllRuns"), f"{label}.serviceLevel.fulfilledUnitsAllRuns", 0)
    demand = _integer(service.get("demandUnitsAllRuns"), f"{label}.serviceLevel.demandUnitsAllRuns", 0)
    expected_service = fulfilled / demand if demand else 1.0
    if service.get("definition") != "fulfilled_units_all_runs / demand_units_all_runs" or fulfilled > demand:
        _fail(f"{label}.serviceLevel: invalid aggregate basis")
    _same_number(service.get("value"), expected_service, f"{label}.serviceLevel.value", 1e-12)
    _same_number(cell["serviceLevel"], expected_service, f"{label}.matrix.serviceLevel", 1e-12)
    cash = _mapping(trace.get("cashOutflowP90"), f"{label}.cashOutflowP90")
    _exact_keys(cash, ("valueUsd", "method", "percentile", "rankOneBased", "denominatorRuns", "includedCashComponents", "excludedNonCashComponents", "perRunRounding"), f"{label}.cashOutflowP90")
    if cash.get("method") != "nearest_rank_ceil_0.90N" or cash.get("percentile") != 0.9 or cash.get("rankOneBased") != math.ceil(0.9 * runs) or cash.get("denominatorRuns") != runs or cash.get("includedCashComponents") != ["purchase", "holding", "renewalPremium", "terminationFee"] or cash.get("excludedNonCashComponents") != ["stockoutLoss"] or cash.get("perRunRounding") != "whole_usd_half_even" or cash.get("valueUsd") != cell["cashOutflowP90"]:
        _fail(f"{label}.cashOutflowP90: rank, components, or matrix value mismatch")
    _integer(cash.get("valueUsd"), f"{label}.cashOutflowP90.valueUsd", 0)
    _text(trace.get("summaryRoundingRule"), f"{label}.summaryRoundingRule")
    sample = _mapping(trace.get("samplePath"), f"{label}.samplePath")
    _exact_keys(sample, ("sampleRunIndex", "classification", "note", "weeks"), f"{label}.samplePath")
    if sample.get("classification") != "single_realised_trial_not_aggregate":
        _fail(f"{label}.samplePath: cannot represent aggregate results")
    note = _text(sample.get("note"), f"{label}.samplePath.note").lower()
    if "not" not in note or not any(word in note for word in ("average", "aggregate", "expectation")):
        _fail(f"{label}.samplePath.note: lacks non-aggregate warning")
    _integer(sample.get("sampleRunIndex"), f"{label}.samplePath.sampleRunIndex", 0)
    if sample["sampleRunIndex"] >= runs:
        _fail(f"{label}.samplePath.sampleRunIndex: outside Monte Carlo run range")
    weeks = _list(sample.get("weeks"), f"{label}.samplePath.weeks")
    if len(weeks) != 104:
        _fail(f"{label}.samplePath.weeks: requires all 104 weeks")
    week_keys = ("week", "startDate", "openingUnits", "arrivalsA", "arrivalsB", "demandUnits", "availableUnits", "fulfilledUnits", "lostUnits", "endingUnits", "onOrderUnitsBefore", "inventoryPositionBefore", "reorderPointUnits", "orderedA", "orderedB", "sampledLeadDaysA", "sampledLeadDaysB", "plannedArrivalWeekA", "plannedArrivalWeekB", "onOrderUnitsAfter", "holdingRawUsd", "stockoutLossRawUsd", "basePurchaseRawUsd", "renewalPremiumRawUsd", "terminationFeeRawUsd")
    for index, raw in enumerate(weeks):
        week = _mapping(raw, f"{label}.samplePath.weeks[{index}]")
        _exact_keys(week, week_keys, f"{label}.samplePath.weeks[{index}]")
        if _integer(week.get("week"), f"{label}.samplePath.weeks[{index}].week", 1) != index + 1:
            _fail(f"{label}.samplePath.weeks: wrong week sequence")
        try:
            date.fromisoformat(_text(week.get("startDate"), f"{label}.samplePath.weeks[{index}].startDate"))
        except ValueError as exc:
            raise InputValidationError(f"{label}.samplePath.weeks[{index}].startDate: invalid date") from exc
        for key in ("openingUnits", "arrivalsA", "arrivalsB", "demandUnits", "availableUnits", "fulfilledUnits", "lostUnits", "endingUnits", "onOrderUnitsBefore", "inventoryPositionBefore", "reorderPointUnits", "orderedA", "orderedB", "onOrderUnitsAfter"):
            _integer(week.get(key), f"{label}.samplePath.weeks[{index}].{key}", 0)
        for key in ("sampledLeadDaysA", "sampledLeadDaysB", "plannedArrivalWeekA", "plannedArrivalWeekB"):
            if week.get(key) is not None:
                _integer(week.get(key), f"{label}.samplePath.weeks[{index}].{key}", 0)
        for key in ("holdingRawUsd", "stockoutLossRawUsd", "basePurchaseRawUsd", "renewalPremiumRawUsd", "terminationFeeRawUsd"):
            try:
                parsed = float(_text(week.get(key), f"{label}.samplePath.weeks[{index}].{key}"))
            except ValueError as exc:
                raise InputValidationError(f"{label}.samplePath.weeks[{index}].{key}: invalid decimal text") from exc
            if not math.isfinite(parsed):
                _fail(f"{label}.samplePath.weeks[{index}].{key}: non-finite decimal")
    return identity, contract_parameters


def _trace_evidence_provenance(response: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    traces = response["data"]["traces"]
    for sid in SCENARIO_IDS:
        for oid in OPTION_IDS:
            for parameter in traces[sid][oid]["parameters"]:
                if str(parameter.get("key", "")).startswith("contract."):
                    provenance = parameter["provenance"]
                    for evidence_id in provenance.get("evidenceIds", []):
                        prior = result.get(evidence_id)
                        # The same evidence may support more than one parameter;
                        # parameter-specific sourceId/note are allowed to differ.
                        # Its source and reviewed-record identity cannot differ.
                        if prior is not None and (
                            prior.get("sourceFile"), prior.get("sourceSha256"), prior.get("reviewRecordId"), prior.get("reviewRecordSha256")
                        ) != (
                            provenance.get("sourceFile"), provenance.get("sourceSha256"), provenance.get("reviewRecordId"), provenance.get("reviewRecordSha256")
                        ):
                            _fail(f"trace evidence {evidence_id}: source/review provenance differs across cells")
                        result[evidence_id] = provenance
    return result


def validate_run(
    run: VerifiedRun,
    *,
    require_reviewed: bool = True,
    reviewed_bundle: Mapping[str, Any] | None = None,
) -> VerifiedRun:
    """Return an immutable detached run only after complete current-run validation.

    ``require_reviewed=False`` is an explicit internal developer path.  It accepts
    only an *unreviewed_development_only* record and never turns it into reviewed
    data.  It is not a Boardroom transport escape hatch.

    ``reviewed_bundle`` is optional because callers may already put the supplied
    bundle in ``run.contract``.  If supplied, it is the canonical contract source
    and every trace contract field and identity hash is checked against it.
    """
    if not isinstance(run, VerifiedRun):
        _fail("run: expected VerifiedRun")
    root = Path(run.source_root).resolve()
    if not root.is_dir():
        _fail("run.source_root: unavailable")
    request = _thaw(run.simulation_request)
    response = _thaw(run.simulation_response)
    run_contract = _thaw(run.contract)
    supplied_bundle = _thaw(reviewed_bundle) if reviewed_bundle is not None else run_contract
    request = _mapping(request, "simulation_request")
    response = _mapping(response, "simulation_response")
    source_contract, field_provenance = _contract_payload(_mapping(supplied_bundle, "contract/bundle"))
    source_contract = _mapping(source_contract, "contract")
    _validate_contract(source_contract)
    scenario_map, option_map = _request_maps(request)
    _exact_keys(response, ("schemaVersion", "dataVersion", "requestId", "data"), "simulation_response")
    if response.get("schemaVersion") != "causora.contract.v2":
        _fail("simulation_response.schemaVersion: expected causora.contract.v2")
    request_id = _text(run.simulation_request_id, "simulation_request_id")
    if response.get("requestId") != request_id:
        _fail("simulation_response.requestId: stale or unrelated simulation request")
    data_version = _text(response.get("dataVersion"), "simulation_response.dataVersion")
    data = _mapping(response.get("data"), "simulation_response.data")
    _exact_keys(data, ("simulation", "deltas", "selections", "traces", "executionContext"), "simulation_response.data")
    reviewed, _context = _validate_context(data, require_reviewed=require_reviewed)
    if not require_reviewed and reviewed:
        # This makes developer-only call sites deliberately choose reviewed or
        # development input rather than silently treating a reviewed result as a
        # development result.
        _fail("developer validation mode accepts only explicit unreviewed development records")
    simulation = _mapping(data.get("simulation"), "response.data.simulation")
    _exact_keys(simulation, ("simulationId", "seed", "dataVersion", "formulaVersion", "weeks", "monteCarloRuns", "unitPricesUsd", "matrix"), "response.data.simulation")
    simulation_id = _text(simulation.get("simulationId"), "simulation.simulationId")
    simulation_marker = simulation_id.lower()
    if reviewed and ("unreviewed" in simulation_marker or "mock" in simulation_marker) or not reviewed and "unreviewed" not in simulation_marker:
        _fail("simulation.simulationId: execution identity marker does not match context")
    if (simulation.get("seed"), simulation.get("dataVersion"), simulation.get("formulaVersion"), simulation.get("weeks")) != (request["seed"], data_version, "tco-v1", 104):
        _fail("simulation: seed/dataVersion/formula/104-week identity differs from current request")
    _integer(simulation.get("monteCarloRuns"), "simulation.monteCarloRuns", 1)
    if not reviewed and "UNREVIEWED_DEV_ONLY" not in data_version:
        _fail("simulation.dataVersion: development record lacks UNREVIEWED_DEV_ONLY marker")
    if reviewed and "unreviewed" in data_version.lower():
        _fail("simulation.dataVersion: reviewed record contains development marker")
    prices = _mapping(simulation.get("unitPricesUsd"), "simulation.unitPricesUsd")
    _exact_keys(prices, ("A", "B"), "simulation.unitPricesUsd")
    _number(prices.get("A"), "simulation.unitPricesUsd.A", 0)
    _number(prices.get("B"), "simulation.unitPricesUsd.B", 0)
    raw_matrix = _mapping(simulation.get("matrix"), "simulation.matrix")
    if set(raw_matrix) != set(SCENARIO_IDS):
        _fail("simulation.matrix: scenarios differ from current request")
    matrix: dict[str, dict[str, Mapping[str, Any]]] = {}
    for sid in SCENARIO_IDS:
        cells = _list(raw_matrix.get(sid), f"simulation.matrix.{sid}")
        if len(cells) != 3:
            _fail(f"simulation.matrix.{sid}: requires D0/D1/D2")
        by_option: dict[str, Mapping[str, Any]] = {}
        for index, raw in enumerate(cells):
            cell = _mapping(raw, f"simulation.matrix.{sid}[{index}]")
            oid = _text(cell.get("optionId"), f"simulation.matrix.{sid}[{index}].optionId")
            if oid in by_option or oid not in option_map:
                _fail(f"simulation.matrix.{sid}: option differs from current request")
            _validate_cell(cell, scenario_id=sid, option=option_map[oid], prices=prices, label=f"simulation.matrix.{sid}[{index}]")
            by_option[oid] = cell
        if tuple(by_option) != OPTION_IDS:
            _fail(f"simulation.matrix.{sid}: option identities/order differ from current request")
        matrix[sid] = by_option
    _validate_deltas_and_selections(request, data, matrix)
    raw_traces = _mapping(data.get("traces"), "response.data.traces")
    if set(raw_traces) != set(SCENARIO_IDS):
        _fail("response.data.traces: missing current scenarios")
    reference_identity: Mapping[str, Any] | None = None
    reference_contract_parameters: Mapping[str, Any] | None = None
    total_weeks = 0
    for sid in SCENARIO_IDS:
        by_option = _mapping(raw_traces.get(sid), f"traces.{sid}")
        if set(by_option) != set(OPTION_IDS):
            _fail(f"traces.{sid}: missing current options")
        for oid in OPTION_IDS:
            identity, contract_parameters = _validate_trace(
                _mapping(by_option[oid], f"traces.{sid}.{oid}"), matrix[sid][oid], scenario_id=sid, option_id=oid,
                scenario=scenario_map[sid], option=option_map[oid], request_seed=request["seed"], simulation=simulation,
                reviewed=reviewed, contract=source_contract,
                reference_identity=reference_identity, reference_contract_parameters=reference_contract_parameters,
            )
            reference_identity = identity
            reference_contract_parameters = contract_parameters
            total_weeks += 104
    if total_weeks != 936:
        _fail("trace coverage: all nine 104-week paths are required")
    _validate_bundle_provenance(field_provenance, source_contract, reviewed=reviewed)
    trace_provenance = _trace_evidence_provenance(response)
    try:
        # ``run.evidence`` may be the immutable public frontend EvidenceRecord
        # shape, which intentionally has no source hash or typed internal value.
        # Enrichment derives those private values from the physical PDF; it never
        # carries through quoteMatched/matchScore/manual flags supplied by a
        # client.  The second validation binds a reviewed trace to that source.
        internal_evidence = enrich_evidence(
            _list(run.evidence, "run.evidence"), source_root=root, contract=source_contract,
        )
        validated_evidence = validate_evidence_records(
            internal_evidence, source_root=root,
            trace_contract_provenance=trace_provenance if reviewed else None,
            required_ids=set(trace_provenance) if reviewed else (),
        )
    except EvidenceValidationError as exc:
        raise InputValidationError(f"evidence validation failed: {exc}") from exc
    if reviewed:
        # Required IDs arise from the actual trace, not a broad global pool; EV-020
        # is included only because the reviewed renewalLocked parameter cites it.
        if field_provenance is not None:
            for parameter_key, contract_key in _TRACE_CONTRACT_FIELDS.items():
                trace_parameter = reference_contract_parameters[parameter_key]
                trace_p = trace_parameter["provenance"]
                bundle_p = field_provenance[contract_key]
                if (trace_p["sourceId"], trace_p["sourceFile"], trace_p["sourceSha256"], trace_p["evidenceIds"]) != (bundle_p["evidenceId"], bundle_p["sourceFile"], bundle_p["sourceSha256"], [bundle_p["evidenceId"]]):
                    _fail(f"trace contract provenance for {contract_key}: differs from supplied reviewed bundle")
    verified_evidence: list[dict[str, Any]] = []
    for item in validated_evidence:
        record = {
            "id": item.id,
            "sourceFile": item.source_file,
            "sourceSha256": item.source_sha256,
            "page": item.page,
            "quote": item.quote,
            "extractedField": item.extracted_field,
            "extractedValue": item.extracted_value,
            "unit": item.unit,
            # This is recomputed after exact PDF/page/typed extraction checks.
            # It is never copied from an untrusted public EvidenceRecord.
            "quoteMatched": True,
        }
        if not reviewed:
            # Source-checked development evidence may aid an internal smoke, but
            # cannot imply review, policy approval, release, or decision status.
            record["internalOnly"] = True
        verified_evidence.append(record)
    pin_snapshot = canonical_sha256({
        "request": request,
        "responseIdentity": {"requestId": request_id, "simulationId": simulation_id, "dataVersion": data_version},
        "contractPayloadSha256": reference_identity["contractPayloadSha256"] if reference_identity else "",
        "evidenceSourceHashes": sorted(item.source_sha256 for item in validated_evidence),
    })
    return VerifiedRun(
        simulation_request=_freeze(request), simulation_response=_freeze(response), contract=_freeze(source_contract),
        # Keep only detached, source-derived private records.  ``project_role``
        # separately constructs the source-path-free public Risk projection.
        evidence=tuple(_freeze(item) for item in verified_evidence),
        source_root=root, simulation_request_id=request_id, pin_snapshot_sha256=pin_snapshot,
    )


def _current(run: VerifiedRun) -> VerifiedRun:
    """Revalidate a current record in its own execution mode without promotion.

    Formal Boardroom transport already invokes ``validate_run(...,
    require_reviewed=True)`` in the parent pipeline.  These pure projection
    helpers are also used by the explicit internal development smoke path, where
    a valid ``unreviewed_development_only`` record must remain development-only.
    """
    if not isinstance(run, VerifiedRun):
        _fail("run: expected VerifiedRun")
    return validate_run(run, require_reviewed=run.reviewed)


def _scenario_and_rows(run: VerifiedRun, scenario_id: str) -> tuple[Mapping[str, Any], Mapping[str, Mapping[str, Any]], Mapping[str, Any]]:
    request = run.simulation_request
    scenario = next((item for item in request["scenarios"] if item["id"] == scenario_id), None)
    if scenario is None:
        _fail("scenario_id: not in this verified current request")
    data = run.simulation_response["data"]
    rows = {row["optionId"]: row for row in data["simulation"]["matrix"][scenario_id]}
    selection = data["selections"][scenario_id]
    return scenario, rows, selection


def _delta_map(run: VerifiedRun, scenario_id: str) -> dict[str, Mapping[str, Any]]:
    return {item["optionId"]: item for item in run.simulation_response["data"]["deltas"] if item["scenarioId"] == scenario_id}


def _selected_option(selection: Mapping[str, Any]) -> str:
    if selection["status"] != "selected" or selection["recommendedOptionId"] not in OPTION_IDS:
        _fail("scenario: no feasible selected option; Boardroom projection is unavailable")
    return str(selection["recommendedOptionId"])


def _margin_from_trace(run: VerifiedRun, scenario_id: str, option_id: str) -> dict[str, Any] | None:
    """Compute a margin only from named trace inputs carrying real provenance.

    No raw request text or guessed selling price is considered.  Current released
    traces do not provide these parameter names, so normal projections omit it.
    """
    parameters = run.simulation_response["data"]["traces"][scenario_id][option_id]["parameters"]
    by_key = {parameter["key"]: parameter for parameter in parameters}
    selling = by_key.get("operatingPolicy.sellingPriceUsdPerUnit")
    profit = by_key.get("operatingPolicy.profitUsdPerUnit")
    if not selling or not profit:
        return None
    for parameter in (selling, profit):
        provenance = parameter["provenance"]
        if provenance["kind"] not in {"reviewed_contract", "approved_operating_assumption", "observed_synthetic_dataset"} or not provenance["sourceSha256"]:
            return None
        _number(parameter["value"], f"margin.{parameter['key']}")
    selling_value, profit_value = float(selling["value"]), float(profit["value"])
    if selling_value <= 0:
        return None
    return {"profitUsdPerUnit": profit_value, "sellingPriceUsdPerUnit": selling_value, "marginPct": profit_value / selling_value}


def project_role(run: VerifiedRun, scenario_id: str, role: str) -> dict[str, Any]:
    """Return an explicit typed allowlist for exactly one Boardroom role."""
    verified = _current(run)
    if role not in {"CFO", "COO", "Risk"}:
        _fail("role: expected CFO, COO, or Risk")
    scenario, rows, selection = _scenario_and_rows(verified, scenario_id)
    selected_id = _selected_option(selection)
    deltas = _delta_map(verified, scenario_id)
    common = {"role": role, "scenarioId": scenario_id, "selectedOptionId": selected_id, "selectionStatus": "selected"}
    if role == "CFO":
        options = []
        for oid in OPTION_IDS:
            row, delta = rows[oid], deltas[oid]
            finance = {
                "optionId": oid, "expectedTcoUsd": row["expectedTco"], "deltaTcoUsd": delta["deltaTco"],
                "cashOutflowP90Usd": row["cashOutflowP90"], "deltaCashP90Usd": delta["deltaCashP90"],
                "purchaseUsd": row["breakdown"]["purchase"], "holdingUsd": row["breakdown"]["holding"],
                "stockoutLossUsd": row["breakdown"]["stockoutLoss"], "renewalPremiumUsd": row["breakdown"]["renewalPremium"],
                "terminationFeeUsd": row["breakdown"]["terminationFee"],
            }
            options.append(finance)
        result = common | {"finance": {"options": options}}
        margin = _margin_from_trace(verified, scenario_id, selected_id)
        if margin is not None:
            result["finance"]["selectedMargin"] = margin
        return result
    if role == "COO":
        option_shares = {option["id"]: option["shareA"] for option in verified.simulation_request["options"]}
        parameters = {p["key"]: p for p in verified.simulation_response["data"]["traces"][scenario_id][selected_id]["parameters"]}
        inventory_policy = {}
        for field in ("openingInventoryUnits", "safetyStockUnits", "targetStockUnits"):
            parameter = parameters.get("operatingPolicy." + field)
            if parameter is not None:
                inventory_policy[field] = _number(parameter["value"], "COO.inventoryPolicy." + field, 0)
        return common | {"operations": {
            "scenarioDemandUnits24m": scenario["demandUnits24m"], "leadTimeMultiplier": scenario["leadTimeMultiplier"],
            "inventoryPolicy": inventory_policy,
            "options": [{"optionId": oid, "unitsFromA": rows[oid]["unitsFromA"], "unitsFromB": rows[oid]["unitsFromB"], "serviceLevel": rows[oid]["serviceLevel"], "stockoutProbability": rows[oid]["stockoutProbability"], "allocationShareA": option_shares[oid]} for oid in OPTION_IDS],
        }}
    uncertainty = verified.simulation_response["data"]["simulation"]["monteCarloRuns"]
    risk_evidence = []
    for item in verified.evidence:
        # Do not pass sourceFile/sourceSha256, spans, bboxes, review comments,
        # or manual flags to a role.  The quote and typed value were validated
        # against those private inputs above.
        evidence_id = item["id"]
        if evidence_id == "EV-020":
            continue
        risk_evidence.append({
            "id": evidence_id, "page": item["page"], "quote": item["quote"],
            "extractedField": item.get("extractedField", item.get("extracted_field")),
            "extractedValue": item.get("extractedValue", item.get("extracted_value")),
            "unit": item.get("unit"),
        })
    return common | {"risk": {
        "renewalCondition": {"renewalLocked": verified.contract["renewalLocked"], "forecastBasis": verified.contract["forecastBasis"], "minPurchaseShareA": verified.contract["minPurchaseShareA"], "minPurchaseUnitsA": verified.contract["minPurchaseUnitsA"], "renewalNoticeDays": verified.contract["renewalNoticeDays"]},
        "downside": [{"optionId": oid, "stockoutProbability": rows[oid]["stockoutProbability"], "cashOutflowP90Usd": rows[oid]["cashOutflowP90"]} for oid in OPTION_IDS],
        "uncertainty": {"monteCarloRuns": uncertainty, "stockoutDefinition": "trials_with_at_least_one_lost_unit / monteCarloRuns", "cashP90Method": "nearest_rank_ceil_0.90N"},
        "evidence": risk_evidence,
    }}


def mechanism_for(run: VerifiedRun, scenario_id: str) -> dict[str, Any]:
    """Inject exact CriticIssue mechanism fields from code, never from a provider."""
    verified = _current(run)
    scenario, rows, _selection = _scenario_and_rows(verified, scenario_id)
    contract = verified.contract
    rolling_floor = max(0, int(round(float(contract["minPurchaseShareA"]) * int(scenario["demandUnits24m"]))))
    committed_excess = max(0, int(contract["minPurchaseUnitsA"]) - rolling_floor)
    baseline_holding = rows["D0"]["breakdown"]["holding"]
    return {
        "scenarioId": scenario_id,
        "forecastBasis": contract["forecastBasis"],
        "lockedForecastUnits24m": contract["lockedForecastUnits24m"],
        "minPurchaseUnitsA": contract["minPurchaseUnitsA"],
        "scenarioDemandUnits24m": scenario["demandUnits24m"],
        "committedExcessUnits": committed_excess,
        "holdingCostDeltaUsd": {oid: rows[oid]["breakdown"]["holding"] - baseline_holding for oid in OPTION_IDS},
    }


def numeric_registry(run: VerifiedRun, scenario_id: str, option_id: str) -> dict[str, dict[str, Any]]:
    """Build the small option/scenario-scoped registry used by Numeric Guardrail.

    The three public token refs are intentionally the only generic language-token
    values.  All additional refs are scoped, typed technical references for claim
    offsets; no another-scenario metric is placed in a global pool.
    """
    verified = _current(run)
    if option_id not in OPTION_IDS:
        _fail("option_id: expected D0, D1, or D2")
    scenario, rows, selection = _scenario_and_rows(verified, scenario_id)
    row, delta = rows[option_id], _delta_map(verified, scenario_id)[option_id]
    prefix = f"{scenario_id}.{option_id}"
    registry: dict[str, dict[str, Any]] = {
        "delta_tco": {"value": delta["deltaTco"], "kind": "money", "unit": "USD"},
        "stockout_probability": {"value": row["stockoutProbability"], "kind": "percent", "unit": "fraction"},
        "cash_outflow_p90": {"value": row["cashOutflowP90"], "kind": "money", "unit": "USD"},
        f"{prefix}.scenario_id": {"value": scenario_id, "kind": "id", "unit": "scenario"},
        f"{prefix}.option_id": {"value": option_id, "kind": "id", "unit": "option"},
        f"{prefix}.selected_option_id": {"value": selection["recommendedOptionId"], "kind": "id", "unit": "option"},
        f"{prefix}.scenario_demand_units_24m": {"value": scenario["demandUnits24m"], "kind": "units", "unit": "units/24m"},
        f"{prefix}.expected_tco": {"value": row["expectedTco"], "kind": "money", "unit": "USD"},
        f"{prefix}.delta_cash_p90": {"value": delta["deltaCashP90"], "kind": "money", "unit": "USD"},
        f"{prefix}.service_level": {"value": row["serviceLevel"], "kind": "percent", "unit": "fraction"},
        f"{prefix}.units_from_a": {"value": row["unitsFromA"], "kind": "units", "unit": "units/24m"},
        f"{prefix}.units_from_b": {"value": row["unitsFromB"], "kind": "units", "unit": "units/24m"},
        f"{prefix}.purchase": {"value": row["breakdown"]["purchase"], "kind": "money", "unit": "USD"},
        f"{prefix}.holding": {"value": row["breakdown"]["holding"], "kind": "money", "unit": "USD"},
        f"{prefix}.stockout_loss": {"value": row["breakdown"]["stockoutLoss"], "kind": "money", "unit": "USD"},
        f"{prefix}.renewal_premium": {"value": row["breakdown"]["renewalPremium"], "kind": "money", "unit": "USD"},
        f"{prefix}.termination_fee": {"value": row["breakdown"]["terminationFee"], "kind": "money", "unit": "USD"},
        f"{prefix}.renewal_locked": {"value": verified.contract["renewalLocked"], "kind": "text", "unit": "boolean"},
        f"{prefix}.renewal_date": {"value": verified.contract["renewalDate"], "kind": "date", "unit": "ISO-8601"},
        f"{prefix}.min_purchase_units_a": {"value": verified.contract["minPurchaseUnitsA"], "kind": "units", "unit": "units/24m"},
    }
    for evidence in verified.evidence:
        evidence_prefix = f"{prefix}.evidence.{evidence['id']}"
        registry[f"{evidence_prefix}.id"] = {"value": evidence["id"], "kind": "id", "unit": "evidence"}
        registry[f"{evidence_prefix}.page"] = {"value": evidence["page"], "kind": "integer", "unit": "page"}
        registry[f"{evidence_prefix}.value"] = {
            "value": evidence.get("extractedValue", evidence.get("extracted_value")),
            "kind": "text", "unit": evidence.get("unit", ""),
        }
    return registry


__all__ = [
    "COMPONENT_KEYS",
    "FrozenDict",
    "InputValidationError",
    "OPTION_IDS",
    "PUBLIC_TOKENS",
    "SCENARIO_IDS",
    "VerifiedRun",
    "enrich_evidence",
    "make_verified_run",
    "mechanism_for",
    "numeric_registry",
    "project_role",
    "validate_run",
]
