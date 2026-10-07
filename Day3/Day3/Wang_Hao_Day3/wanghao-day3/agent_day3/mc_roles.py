"""Development-only role analysis for Jinzhu's unreviewed Monte Carlo v2 response.

This adapter consumes an already-computed v2 response.  It never invokes the
simulation engine, changes a frontend DTO, reads a recommendation from
``selections``, or turns an unreviewed development calculation into a decision.
Providers may choose code-authored claim identifiers only; all prose, values,
and JSON Pointer bindings are authored and re-read by this module.
"""
from __future__ import annotations

import asyncio
import copy
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Protocol, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .dev_roles import ClaimSelection, DevClaimStubProvider, response_schema


Role: TypeAlias = Literal["CFO", "COO", "Risk"]
ROLES: tuple[Role, ...] = ("CFO", "COO", "Risk")
KIND = "CAUSORA_WANG_DAY3_MC_DEV_ANALYSIS_V1"
SOURCE_MODE = "UNREVIEWED_MONTE_CARLO_SERVICE"
_UNREVIEWED_MODE = "unreviewed_development_only"
_UNREVIEWED_REVIEW = "not_reviewed_development_only"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_NUMBER_WORDS = re.compile(
    r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
    r"single|double|triple|percentile)\b",
    re.IGNORECASE,
)


class StrictModel(BaseModel):
    """Strict, immutable role views and claim records."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class McIdentity(StrictModel):
    simulationId: str = Field(min_length=1)
    dataVersion: str = Field(min_length=1)
    scenarioId: str = Field(min_length=1)


class CfoBreakdown(StrictModel):
    purchase: int = Field(ge=0)
    holding: int = Field(ge=0)
    stockoutLoss: int = Field(ge=0)
    renewalPremium: int = Field(ge=0)
    terminationFee: int = Field(ge=0)


class CfoOption(StrictModel):
    optionId: Literal["D0", "D1", "D2"]
    expectedTco: int = Field(ge=0)
    breakdown: CfoBreakdown
    cashOutflowP90: int = Field(ge=0)
    deltaTco: int
    deltaCashP90: int

    @model_validator(mode="after")
    def reconciles_expected_tco(self) -> "CfoOption":
        if self.expectedTco != sum(self.breakdown.model_dump().values()):
            raise ValueError("CFO expected TCO must reconcile to its displayed breakdown")
        return self


class CfoProjection(McIdentity):
    role: Literal["CFO"] = "CFO"
    options: tuple[CfoOption, CfoOption, CfoOption]

    @model_validator(mode="after")
    def ordered_options(self) -> "CfoProjection":
        if [item.optionId for item in self.options] != ["D0", "D1", "D2"]:
            raise ValueError("CFO options must retain D0/D1/D2 ordering")
        return self


class CooScenario(StrictModel):
    demandShock: float
    demandUnits24m: int = Field(ge=0)
    leadTime: str = Field(min_length=1)
    leadTimeMultiplier: float = Field(gt=0)


class CooOption(StrictModel):
    optionId: Literal["D0", "D1", "D2"]
    unitsFromA: int = Field(ge=0)
    unitsFromB: int = Field(ge=0)
    reorderPoint: int = Field(ge=0)
    stockoutProbability: float = Field(ge=0, le=1)
    serviceLevel: float = Field(ge=0, le=1)
    deltaStockoutPp: float
    deltaServicePp: float


class CooProjection(McIdentity):
    role: Literal["COO"] = "COO"
    scenario: CooScenario
    options: tuple[CooOption, CooOption, CooOption]

    @model_validator(mode="after")
    def ordered_options(self) -> "CooProjection":
        if [item.optionId for item in self.options] != ["D0", "D1", "D2"]:
            raise ValueError("COO options must retain D0/D1/D2 ordering")
        return self


class RiskRequestLimits(StrictModel):
    riskThreshold: float = Field(ge=0, le=1)
    budgetCeilingUsd: int = Field(ge=0)


class RiskContract(StrictModel):
    renewalLocked: bool
    renewalPriceIncreasePct: float = Field(ge=0)
    minPurchaseUnitsA: int = Field(ge=0)
    terminationFeeUsd: int = Field(ge=0)


class RiskOption(StrictModel):
    optionId: Literal["D0", "D1", "D2"]
    stockoutProbability: float = Field(ge=0, le=1)
    cashOutflowP90: int = Field(ge=0)
    feasible: bool


class RiskProjection(McIdentity):
    role: Literal["Risk"] = "Risk"
    humanReviewStatus: Literal["not_reviewed_development_only"]
    decisionReady: Literal[False]
    requestLimits: RiskRequestLimits
    contract: RiskContract
    options: tuple[RiskOption, RiskOption, RiskOption]

    @model_validator(mode="after")
    def ordered_options(self) -> "RiskProjection":
        if [item.optionId for item in self.options] != ["D0", "D1", "D2"]:
            raise ValueError("Risk options must retain D0/D1/D2 ordering")
        return self


McProjection: TypeAlias = CfoProjection | CooProjection | RiskProjection
MetricPrimitive: TypeAlias = str | int | float | bool | None


class MetricBinding(StrictModel):
    """A typed, hash-bound value re-read from one immutable captured document."""

    pointer: str = Field(pattern=r"^/")
    document: Literal["response", "request"]
    simulationId: str = Field(min_length=1)
    dataVersion: str = Field(min_length=1)
    scenarioId: str = Field(min_length=1)
    optionId: Literal["D0", "D1", "D2"] | None = None
    metric: str = Field(min_length=1)
    value: MetricPrimitive
    responseSha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class McClaim(StrictModel):
    """Code-authored selectable claim; provider prose and numeric values are impossible."""

    id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    role: Role
    headlineTemplate: str = Field(min_length=5, max_length=200)
    reasonTemplate: str = Field(min_length=10, max_length=500)
    metricRefs: tuple[str, ...] = Field(min_length=1)
    metricBindings: dict[str, MetricBinding] = Field(min_length=1)

    @field_validator("headlineTemplate", "reasonTemplate")
    @classmethod
    def safe_templates(cls, value: str) -> str:
        if any(char.isdigit() for char in value) or _NUMBER_WORDS.search(value):
            raise ValueError("code claim templates cannot contain numeric language")
        return value

    @model_validator(mode="after")
    def complete_reference_bindings(self) -> "McClaim":
        if len(self.metricRefs) != len(set(self.metricRefs)):
            raise ValueError("claim metric references must be unique")
        if set(self.metricRefs) != set(self.metricBindings):
            raise ValueError("each claim reference must have one typed metric binding")
        return self


class McRoleOutput(StrictModel):
    role: Role
    availability: Literal["DEV_ONLY", "UNAVAILABLE"]
    headline: str = Field(min_length=5, max_length=300)
    reasonText: str = Field(min_length=10, max_length=3000)
    claimIds: tuple[str, ...]
    metricRefs: tuple[str, ...]
    metricBindings: dict[str, MetricBinding]
    status: Literal["Aligned", "Watch"] | None
    failure: Literal["timeout", "provider_error", "cancelled", "invalid_response"] | None

    @field_validator("headline", "reasonText")
    @classmethod
    def safe_rendered_text(cls, value: str) -> str:
        if any(char.isdigit() for char in value) or _NUMBER_WORDS.search(value):
            raise ValueError("role text must be code-authored and cannot contain numeric language")
        return value

    @model_validator(mode="after")
    def outcome_shape(self) -> "McRoleOutput":
        unavailable = self.availability == "UNAVAILABLE"
        if unavailable != (self.failure is not None):
            raise ValueError("availability and failure must agree")
        if (self.status is None) == (self.failure is None):
            raise ValueError("successful outputs require status and failed outputs cannot have status")
        if unavailable and (self.claimIds or self.metricRefs or self.metricBindings):
            raise ValueError("unavailable output cannot invent claims or metric bindings")
        if len(self.claimIds) != len(set(self.claimIds)) or len(self.metricRefs) != len(set(self.metricRefs)):
            raise ValueError("role output identifiers must be unique")
        if set(self.metricRefs) != set(self.metricBindings):
            raise ValueError("role output bindings must exactly cover its references")
        return self


class Provider(Protocol):
    kind: str

    async def complete(self, *, role: Role, system: str, payload: dict[str, Any],
                       schema: dict[str, Any]) -> dict[str, Any]: ...


def _validation_helpers() -> tuple[Any, Any, Any]:
    """Import the separately-owned validation API only at the execution boundary."""
    try:
        from .mc_validation import canonical_sha, resolve_pointer, validate_mc_response
    except ImportError as exc:  # Do not substitute a weaker local validator.
        raise RuntimeError("agent_day3.mc_validation is required before MC role analysis can run") from exc
    return validate_mc_response, canonical_sha, resolve_pointer


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _require_int(value: Any, label: str, *, nonnegative: bool = False) -> int:
    if type(value) is not int or (nonnegative and value < 0):
        raise ValueError(f"{label} must be an integer")
    return value


def _require_number(value: Any, label: str) -> float | int:
    if type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite JSON number")
    return value


def _request_scenario(request: dict[str, Any], scenario_id: str) -> tuple[int, dict[str, Any]]:
    scenarios = _array(request.get("scenarios"), "request.scenarios")
    found = [(index, value) for index, value in enumerate(scenarios)
             if isinstance(value, dict) and value.get("id") == scenario_id]
    if len(found) != 1:
        raise ValueError("scenario_id must resolve exactly once in request.scenarios")
    return found[0]


def _cell_rows(response_data: dict[str, Any], scenario_id: str) -> list[dict[str, Any]]:
    matrix = _object(_object(response_data.get("simulation"), "data.simulation").get("matrix"), "data.simulation.matrix")
    rows = _array(matrix.get(scenario_id), f"matrix.{scenario_id}")
    if len(rows) != 3 or [item.get("optionId") if isinstance(item, dict) else None for item in rows] != ["D0", "D1", "D2"]:
        raise ValueError("selected matrix scenario must retain ordered D0/D1/D2 cells")
    return [_object(item, "matrix cell") for item in rows]


def _scenario_deltas(response_data: dict[str, Any], scenario_id: str) -> dict[str, tuple[int, dict[str, Any]]]:
    found: dict[str, tuple[int, dict[str, Any]]] = {}
    for index, raw in enumerate(_array(response_data.get("deltas"), "data.deltas")):
        delta = _object(raw, "decision delta")
        if delta.get("scenarioId") == scenario_id:
            option_id = delta.get("optionId")
            if option_id in found:
                raise ValueError("selected scenario has duplicate decision deltas")
            found[option_id] = (index, delta)
    if list(found) != ["D0", "D1", "D2"]:
        raise ValueError("selected scenario must retain ordered D0/D1/D2 deltas")
    return found


def _trace_parameter_index(trace: dict[str, Any], key: str) -> int:
    matches = [index for index, raw in enumerate(_array(trace.get("parameters"), "trace.parameters"))
               if isinstance(raw, dict) and raw.get("key") == key]
    if len(matches) != 1:
        raise ValueError(f"trace must have exactly one parameter named {key}")
    return matches[0]


def _trace_for(response_data: dict[str, Any], scenario_id: str, option_id: str) -> dict[str, Any]:
    traces = _object(response_data.get("traces"), "data.traces")
    by_scenario = _object(traces.get(scenario_id), f"traces.{scenario_id}")
    trace = _object(by_scenario.get(option_id), f"traces.{scenario_id}.{option_id}")
    if trace.get("scenarioId") != scenario_id or trace.get("optionId") != option_id:
        raise ValueError("trace identity does not match its matrix location")
    return trace


def _assert_request_response_binding(request: dict[str, Any], response: dict[str, Any], scenario_id: str) -> None:
    """Reject a stale request before a provider can see a payload.

    The validator owns complete v2 contract validation.  This adapter additionally
    checks the request facts duplicated in selected trace parameters and all option
    facts, which protects the role boundary when a same-shaped stale response is
    accidentally paired with a changed request.
    """
    data = _object(response.get("data"), "response.data")
    simulation = _object(data.get("simulation"), "data.simulation")
    if simulation.get("seed") != request.get("seed"):
        raise ValueError("response simulation seed does not bind the supplied request")
    scenario_index, scenario = _request_scenario(request, scenario_id)
    del scenario_index
    for option in ("D0", "D1", "D2"):
        trace = _trace_for(data, scenario_id, option)
        expected = {
            "scenario.demandShock": scenario.get("demandShock"),
            "scenario.demandUnits24m": scenario.get("demandUnits24m"),
            "scenario.leadTimeMultiplier": scenario.get("leadTimeMultiplier"),
        }
        request_options = [item for item in _array(request.get("options"), "request.options")
                           if isinstance(item, dict) and item.get("id") == option]
        if len(request_options) != 1:
            raise ValueError("request option identities must be unique and complete")
        expected.update({
            "option.shareA": request_options[0].get("shareA"),
            "option.terminateA": request_options[0].get("terminateA"),
        })
        for key, expected_value in expected.items():
            parameter = _array(trace.get("parameters"), "trace.parameters")[_trace_parameter_index(trace, key)]
            if not isinstance(parameter, dict) or parameter.get("value") != expected_value:
                raise ValueError("response trace is stale for the supplied request")


def _capture_validated(request: dict[str, Any], response: dict[str, Any], *, headers: dict[str, Any] | None,
                       scenario_id: str) -> tuple[dict[str, Any], dict[str, Any], str, str, Any]:
    """Validate before projection/provider work and then capture immutable JSON snapshots."""
    if not isinstance(request, dict) or not isinstance(response, dict):
        raise ValueError("request and response must be JSON objects")
    validate_mc_response, canonical_sha, resolve_pointer = _validation_helpers()
    audit = validate_mc_response(request, response, headers)
    if not isinstance(audit, dict):
        raise ValueError("mc validation must return its audit object")
    request_sha = canonical_sha(request)
    response_sha = canonical_sha(response)
    if not isinstance(request_sha, str) or not _SHA256.fullmatch(request_sha):
        raise ValueError("mc canonical request hash is invalid")
    if not isinstance(response_sha, str) or not _SHA256.fullmatch(response_sha):
        raise ValueError("mc canonical response hash is invalid")
    frozen_request, frozen_response = copy.deepcopy(request), copy.deepcopy(response)
    execution = _object(_object(frozen_response.get("data"), "response.data").get("executionContext"), "executionContext")
    expected_context = {
        "mode": _UNREVIEWED_MODE,
        "humanReviewStatus": _UNREVIEWED_REVIEW,
        "policyStatus": "unapproved_development_only",
        "contractReleaseStatus": "not_released_development_only",
        "decisionReady": False,
    }
    for field, expected in expected_context.items():
        if execution.get(field) != expected or type(execution.get(field)) is not type(expected):
            raise ValueError("response executionContext is not the current unreviewed development context")
    simulation = _object(_object(frozen_response.get("data"), "response.data").get("simulation"), "data.simulation")
    if _require_int(simulation.get("monteCarloRuns"), "simulation.monteCarloRuns", nonnegative=True) < 1:
        raise ValueError("MC role analysis requires a positive actual trial count")
    _request_scenario(frozen_request, scenario_id)
    _assert_request_response_binding(frozen_request, frozen_response, scenario_id)
    return frozen_request, frozen_response, request_sha, response_sha, resolve_pointer


def _identity(response: dict[str, Any], scenario_id: str) -> McIdentity:
    envelope_version = _require_string(response.get("dataVersion"), "response.dataVersion")
    data = _object(response.get("data"), "response.data")
    simulation = _object(data.get("simulation"), "data.simulation")
    simulation_id = _require_string(simulation.get("simulationId"), "simulation.simulationId")
    data_version = _require_string(simulation.get("dataVersion"), "simulation.dataVersion")
    if data_version != envelope_version:
        raise ValueError("response data version differs from simulation data version")
    return McIdentity(simulationId=simulation_id, dataVersion=data_version, scenarioId=scenario_id)


def _binding(*, pointer: str, document: Literal["response", "request"], metric: str,
             identity: McIdentity, option_id: str | None, request: dict[str, Any], response: dict[str, Any],
             response_sha: str, resolve_pointer: Any) -> MetricBinding:
    document_value = response if document == "response" else request
    try:
        value = resolve_pointer(document_value, pointer)
    except Exception as exc:
        raise ValueError(f"metric pointer does not resolve: {document}:{pointer}") from exc
    if type(value) not in (str, int, float, bool) and value is not None:
        raise ValueError("metric binding values must remain typed JSON primitives")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("metric binding values must be finite")
    return MetricBinding(pointer=pointer, document=document, simulationId=identity.simulationId,
                         dataVersion=identity.dataVersion, scenarioId=identity.scenarioId,
                         optionId=option_id, metric=metric, value=copy.deepcopy(value),
                         responseSha256=response_sha)


def _response_ref(pointer: str) -> str:
    return "response:" + pointer


def _request_ref(pointer: str) -> str:
    return "request:" + pointer


def _add_binding(bindings: dict[str, MetricBinding], *, ref: str, pointer: str,
                 document: Literal["response", "request"], metric: str, identity: McIdentity,
                 option_id: str | None, request: dict[str, Any], response: dict[str, Any],
                 response_sha: str, resolve_pointer: Any) -> None:
    if ref in bindings:
        raise ValueError("metric references must be canonical and unique")
    bindings[ref] = _binding(pointer=pointer, document=document, metric=metric, identity=identity,
                             option_id=option_id, request=request, response=response,
                             response_sha=response_sha, resolve_pointer=resolve_pointer)


def _recheck_captured_bindings(claims: Sequence[McClaim], *, request: dict[str, Any], response: dict[str, Any],
                               identity: McIdentity, response_sha: str, resolve_pointer: Any) -> None:
    """Re-read every catalog value from the private immutable captures before rendering."""
    for claim in claims:
        for reference, binding in claim.metricBindings.items():
            if reference not in claim.metricRefs:
                raise ValueError("claim binding is outside the code-authored reference allowlist")
            document = response if binding.document == "response" else request
            captured_value = resolve_pointer(document, binding.pointer)
            if type(captured_value) is not type(binding.value) or captured_value != binding.value:
                raise ValueError("captured metric value changed after catalog construction")
            if (binding.simulationId, binding.dataVersion, binding.scenarioId, binding.responseSha256) != (
                identity.simulationId, identity.dataVersion, identity.scenarioId, response_sha,
            ):
                raise ValueError("captured metric binding identity differs from the analysis identity")


def _validate_component_value(cell: dict[str, Any], trace: dict[str, Any], key: str) -> None:
    breakdown = _object(cell.get("breakdown"), "matrix breakdown")
    value = _require_int(breakdown.get(key), f"matrix breakdown.{key}", nonnegative=True)
    components = _array(trace.get("components"), "trace.components")
    matches = [raw for raw in components if isinstance(raw, dict) and raw.get("key") == key]
    if len(matches) != 1 or matches[0].get("valueUsd") != value:
        raise ValueError("matrix breakdown is not bound to the matching trace component")


def _build_projections_and_bindings(request: dict[str, Any], response: dict[str, Any], *, scenario_id: str,
                                    request_sha: str, response_sha: str, resolve_pointer: Any) -> tuple[
                                        dict[Role, McProjection], dict[Role, dict[str, MetricBinding]]]:
    del request_sha  # Request SHA is output lineage; each request binding remains response-hash-bound too.
    identity = _identity(response, scenario_id)
    data = _object(response["data"], "response.data")
    rows = _cell_rows(data, scenario_id)
    deltas = _scenario_deltas(data, scenario_id)
    scenario_index, scenario = _request_scenario(request, scenario_id)
    cfo_bindings: dict[str, MetricBinding] = {}
    coo_bindings: dict[str, MetricBinding] = {}
    risk_bindings: dict[str, MetricBinding] = {}
    cfo_options: list[CfoOption] = []
    coo_options: list[CooOption] = []
    risk_options: list[RiskOption] = []

    for index, cell in enumerate(rows):
        option_id = cell.get("optionId")
        if option_id not in ("D0", "D1", "D2"):
            raise ValueError("matrix contains an unsupported option")
        option = str(option_id)
        trace = _trace_for(data, scenario_id, option)
        delta_index, delta = deltas[option]
        cell_pointer = f"/data/simulation/matrix/{scenario_id}/{index}"
        delta_pointer = f"/data/deltas/{delta_index}"
        trace_pointer = f"/data/traces/{scenario_id}/{option}"
        for component in ("purchase", "holding", "stockoutLoss", "renewalPremium", "terminationFee"):
            _validate_component_value(cell, trace, component)
            _add_binding(cfo_bindings, ref=_response_ref(f"{cell_pointer}/breakdown/{component}"),
                         pointer=f"{cell_pointer}/breakdown/{component}", document="response",
                         metric=f"breakdown.{component}", identity=identity, option_id=option,
                         request=request, response=response, response_sha=response_sha, resolve_pointer=resolve_pointer)
        for metric in ("expectedTco", "cashOutflowP90"):
            _add_binding(cfo_bindings, ref=_response_ref(f"{cell_pointer}/{metric}"), pointer=f"{cell_pointer}/{metric}",
                         document="response", metric=metric, identity=identity, option_id=option,
                         request=request, response=response, response_sha=response_sha, resolve_pointer=resolve_pointer)
        for metric in ("deltaTco", "deltaCashP90"):
            _add_binding(cfo_bindings, ref=_response_ref(f"{delta_pointer}/{metric}"), pointer=f"{delta_pointer}/{metric}",
                         document="response", metric=metric, identity=identity, option_id=option,
                         request=request, response=response, response_sha=response_sha, resolve_pointer=resolve_pointer)
        for metric in ("unitsFromA", "unitsFromB", "stockoutProbability", "serviceLevel"):
            _add_binding(coo_bindings, ref=_response_ref(f"{cell_pointer}/{metric}"), pointer=f"{cell_pointer}/{metric}",
                         document="response", metric=metric, identity=identity, option_id=option,
                         request=request, response=response, response_sha=response_sha, resolve_pointer=resolve_pointer)
        for metric in ("deltaStockoutPp", "deltaServicePp"):
            _add_binding(coo_bindings, ref=_response_ref(f"{delta_pointer}/{metric}"), pointer=f"{delta_pointer}/{metric}",
                         document="response", metric=metric, identity=identity, option_id=option,
                         request=request, response=response, response_sha=response_sha, resolve_pointer=resolve_pointer)
        reorder_index = _trace_parameter_index(trace, "reorderPointUnits")
        _add_binding(coo_bindings, ref=_response_ref(f"{trace_pointer}/parameters/{reorder_index}/value"),
                     pointer=f"{trace_pointer}/parameters/{reorder_index}/value", document="response",
                     metric="reorderPoint", identity=identity, option_id=option, request=request, response=response,
                     response_sha=response_sha, resolve_pointer=resolve_pointer)
        for metric in ("stockoutProbability", "cashOutflowP90", "feasible"):
            _add_binding(risk_bindings, ref=_response_ref(f"{cell_pointer}/{metric}"), pointer=f"{cell_pointer}/{metric}",
                         document="response", metric=metric, identity=identity, option_id=option,
                         request=request, response=response, response_sha=response_sha, resolve_pointer=resolve_pointer)
        cfo_options.append(CfoOption(optionId=option, expectedTco=_require_int(cell.get("expectedTco"), "expectedTco", nonnegative=True),
            breakdown=CfoBreakdown.model_validate(_object(cell.get("breakdown"), "breakdown")),
            cashOutflowP90=_require_int(cell.get("cashOutflowP90"), "cashOutflowP90", nonnegative=True),
            deltaTco=_require_int(delta.get("deltaTco"), "deltaTco"), deltaCashP90=_require_int(delta.get("deltaCashP90"), "deltaCashP90")))
        coo_options.append(CooOption(optionId=option, unitsFromA=_require_int(cell.get("unitsFromA"), "unitsFromA", nonnegative=True),
            unitsFromB=_require_int(cell.get("unitsFromB"), "unitsFromB", nonnegative=True),
            reorderPoint=_require_int(_array(trace["parameters"], "trace.parameters")[reorder_index].get("value"), "reorderPoint", nonnegative=True),
            stockoutProbability=float(_require_number(cell.get("stockoutProbability"), "stockoutProbability")),
            serviceLevel=float(_require_number(cell.get("serviceLevel"), "serviceLevel")),
            deltaStockoutPp=float(_require_number(delta.get("deltaStockoutPp"), "deltaStockoutPp")),
            deltaServicePp=float(_require_number(delta.get("deltaServicePp"), "deltaServicePp"))))
        risk_options.append(RiskOption(optionId=option,
            stockoutProbability=float(_require_number(cell.get("stockoutProbability"), "stockoutProbability")),
            cashOutflowP90=_require_int(cell.get("cashOutflowP90"), "cashOutflowP90", nonnegative=True),
            feasible=cell.get("feasible") if type(cell.get("feasible")) is bool else (_ for _ in ()).throw(ValueError("feasible must be boolean"))))

    for metric in ("demandShock", "demandUnits24m", "leadTime", "leadTimeMultiplier"):
        _add_binding(coo_bindings, ref=_request_ref(f"/scenarios/{scenario_index}/{metric}"),
                     pointer=f"/scenarios/{scenario_index}/{metric}", document="request", metric=metric,
                     identity=identity, option_id=None, request=request, response=response, response_sha=response_sha,
                     resolve_pointer=resolve_pointer)
    for metric in ("riskThreshold", "budgetCeilingUsd"):
        _add_binding(risk_bindings, ref=_request_ref(f"/{metric}"), pointer=f"/{metric}", document="request",
                     metric=metric, identity=identity, option_id=None, request=request, response=response,
                     response_sha=response_sha, resolve_pointer=resolve_pointer)
    first_trace = _trace_for(data, scenario_id, "D0")
    for key, metric in (("contract.renewalLocked", "contract.renewalLocked"),
                        ("contract.renewalPriceIncreasePct", "contract.renewalPriceIncreasePct"),
                        ("contract.minPurchaseUnitsA", "contract.minPurchaseUnitsA"),
                        ("contract.terminationFeeUsd", "contract.terminationFeeUsd")):
        index = _trace_parameter_index(first_trace, key)
        parameter = _object(_array(first_trace["parameters"], "trace.parameters")[index], "trace parameter")
        provenance = _object(parameter.get("provenance"), "trace parameter provenance")
        if provenance.get("kind") != "unreviewed_development_contract" or provenance.get("status") != _UNREVIEWED_MODE:
            raise ValueError("risk contract parameter lacks unreviewed development trace provenance")
        pointer = f"/data/traces/{scenario_id}/D0/parameters/{index}/value"
        _add_binding(risk_bindings, ref=_response_ref(pointer), pointer=pointer, document="response", metric=metric,
                     identity=identity, option_id="D0", request=request, response=response, response_sha=response_sha,
                     resolve_pointer=resolve_pointer)
    execution = _object(data.get("executionContext"), "executionContext")
    for field in ("mode", "humanReviewStatus", "policyStatus", "contractReleaseStatus", "decisionReady"):
        pointer = f"/data/executionContext/{field}"
        _add_binding(risk_bindings, ref=_response_ref(pointer), pointer=pointer, document="response", metric=field,
                     identity=identity, option_id=None, request=request, response=response, response_sha=response_sha,
                     resolve_pointer=resolve_pointer)

    projections: dict[Role, McProjection] = {
        "CFO": CfoProjection(**identity.model_dump(), options=tuple(cfo_options)),
        "COO": CooProjection(**identity.model_dump(), scenario=CooScenario(
            demandShock=float(_require_number(scenario.get("demandShock"), "request demandShock")),
            demandUnits24m=_require_int(scenario.get("demandUnits24m"), "request demandUnits24m", nonnegative=True),
            leadTime=_require_string(scenario.get("leadTime"), "request leadTime"),
            leadTimeMultiplier=float(_require_number(scenario.get("leadTimeMultiplier"), "request leadTimeMultiplier")),
        ), options=tuple(coo_options)),
        "Risk": RiskProjection(**identity.model_dump(), humanReviewStatus=execution["humanReviewStatus"],
            decisionReady=execution["decisionReady"], requestLimits=RiskRequestLimits(
                riskThreshold=float(_require_number(request.get("riskThreshold"), "request riskThreshold")),
                budgetCeilingUsd=_require_int(request.get("budgetCeilingUsd"), "request budgetCeilingUsd", nonnegative=True),
            ), contract=RiskContract(
                renewalLocked=bool(risk_bindings[_response_ref(f"/data/traces/{scenario_id}/D0/parameters/{_trace_parameter_index(first_trace, 'contract.renewalLocked')}/value")].value),
                renewalPriceIncreasePct=float(risk_bindings[_response_ref(f"/data/traces/{scenario_id}/D0/parameters/{_trace_parameter_index(first_trace, 'contract.renewalPriceIncreasePct')}/value")].value),
                minPurchaseUnitsA=int(risk_bindings[_response_ref(f"/data/traces/{scenario_id}/D0/parameters/{_trace_parameter_index(first_trace, 'contract.minPurchaseUnitsA')}/value")].value),
                terminationFeeUsd=int(risk_bindings[_response_ref(f"/data/traces/{scenario_id}/D0/parameters/{_trace_parameter_index(first_trace, 'contract.terminationFeeUsd')}/value")].value),
            ), options=tuple(risk_options)),
    }
    return projections, {"CFO": cfo_bindings, "COO": coo_bindings, "Risk": risk_bindings}


def build_mc_projections(request: dict[str, Any], response: dict[str, Any], scenario_id: str, *,
                         headers: dict[str, Any] | None = None) -> dict[Role, McProjection]:
    """Validate the actual v2 response and return three narrow immutable role views."""
    frozen_request, frozen_response, request_sha, response_sha, resolver = _capture_validated(
        request, response, headers=headers, scenario_id=scenario_id)
    projections, _bindings = _build_projections_and_bindings(
        frozen_request, frozen_response, scenario_id=scenario_id, request_sha=request_sha,
        response_sha=response_sha, resolve_pointer=resolver)
    return projections


def _claim(*, claim_id: str, role: Role, headline: str, reason: str, refs: Sequence[str],
           bindings: Mapping[str, MetricBinding]) -> McClaim:
    references = tuple(refs)
    return McClaim(id=claim_id, role=role, headlineTemplate=headline, reasonTemplate=reason,
                   metricRefs=references, metricBindings={ref: copy.deepcopy(bindings[ref]) for ref in references})


def build_mc_claim_catalog(view: McProjection, bindings: Mapping[str, MetricBinding]) -> list[McClaim]:
    """Build only claims that are true from the validated narrow role view."""
    if isinstance(view, CfoProjection):
        refs = list(bindings)
        claims = [_claim(claim_id="cfo_financial_metrics_bound", role="CFO",
                         headline="Financial Monte Carlo development analysis",
                         reason="Expected total cost, tail cash exposure, and cost components are bound to listed simulation metrics.",
                         refs=refs, bindings=bindings)]
        lower_cost_higher_cash = [item for item in view.options
                                  if item.deltaTco < 0 and item.deltaCashP90 > 0]
        if lower_cost_higher_cash:
            # Canonical matrix/delta pointers use indices, so retain the complete validated CFO set.
            claims.append(_claim(claim_id="cfo_lower_cost_higher_tail_cash", role="CFO",
                headline="Financial Monte Carlo development analysis",
                reason="A lower expected total cost coincides with higher tail cash exposure in bound alternatives.",
                refs=refs, bindings=bindings))
        return claims
    if isinstance(view, CooProjection):
        refs = list(bindings)
        claims = [_claim(claim_id="coo_operational_metrics_bound", role="COO",
                         headline="Operational Monte Carlo development analysis",
                         reason="Demand and lead conditions, procurement units, reorder thresholds, and service statistics are bound to listed simulation metrics.",
                         refs=refs, bindings=bindings)]
        if any(item.deltaStockoutPp != 0 or item.deltaServicePp != 0 for item in view.options):
            claims.append(_claim(claim_id="coo_noncausal_probability_service_comparison", role="COO",
                headline="Operational Monte Carlo development analysis",
                reason="Probability and service differences are displayed as noncausal scenario comparisons.",
                refs=refs, bindings=bindings))
        return claims
    if isinstance(view, RiskProjection):
        refs = list(bindings)
        claims = [_claim(claim_id="risk_unreviewed_development_status", role="Risk",
                         headline="Risk Monte Carlo development analysis",
                         reason="Development-only execution remains not reviewed and not decision ready.",
                         refs=refs, bindings=bindings)]
        if any(item.stockoutProbability > view.requestLimits.riskThreshold for item in view.options):
            claims.append(_claim(claim_id="risk_probability_threshold_exceeded", role="Risk",
                headline="Risk Monte Carlo development analysis",
                reason="A bound option exceeds the request risk threshold without a decision conclusion.",
                refs=refs, bindings=bindings))
        if any(item.cashOutflowP90 > view.requestLimits.budgetCeilingUsd for item in view.options):
            claims.append(_claim(claim_id="risk_budget_ceiling_exceeded", role="Risk",
                headline="Risk Monte Carlo development analysis",
                reason="A bound option exceeds the request budget ceiling without a decision conclusion.",
                refs=refs, bindings=bindings))
        return claims
    raise ValueError("unsupported MC projection")


def _provider_payload(role: Role, view: McProjection, claims: Sequence[McClaim]) -> dict[str, Any]:
    """Send one role's detached typed view and a code-authored selector catalog only."""
    return copy.deepcopy({
        "role": role,
        "view": view.model_dump(mode="json"),
        "claimCatalog": [{
            "id": claim.id,
            "headlineTemplate": claim.headlineTemplate,
            "reasonTemplate": claim.reasonTemplate,
            "metricRefs": list(claim.metricRefs),
        } for claim in claims],
    })


_SYSTEM = (
    "Select only allowed claim identifiers. Return exactly the requested JSON object. "
    "Do not return prose, reasons, headlines, metric values, recommendations, decisions, approvals, "
    "selections, or additional fields."
)


def _render_selection(role: Role, selection: ClaimSelection, claims: Sequence[McClaim]) -> McRoleOutput:
    by_id = {claim.id: claim for claim in claims}
    if selection.role != role or not set(selection.claim_ids) <= set(by_id):
        raise ValueError("provider selected a claim outside the code-authored role allowlist")
    selected = [by_id[claim_id] for claim_id in selection.claim_ids]
    refs: list[str] = []
    bindings: dict[str, MetricBinding] = {}
    for claim in selected:
        for ref in claim.metricRefs:
            if ref not in bindings:
                refs.append(ref)
                bindings[ref] = copy.deepcopy(claim.metricBindings[ref])
    return McRoleOutput(role=role, availability="DEV_ONLY", headline=selected[0].headlineTemplate,
                        reasonText=" ".join(claim.reasonTemplate for claim in selected),
                        claimIds=tuple(claim.id for claim in selected), metricRefs=tuple(refs),
                        metricBindings=bindings, status=selection.status, failure=None)


def _failure(role: Role, failure: Literal["timeout", "provider_error", "cancelled", "invalid_response"]) -> McRoleOutput:
    return McRoleOutput(role=role, availability="UNAVAILABLE", headline="Development analysis unavailable",
                        reasonText="No development claim selection was returned.", claimIds=(), metricRefs=(),
                        metricBindings={}, status=None, failure=failure)


async def run_mc_parallel(request: dict[str, Any], response: dict[str, Any], *, provider: Provider,
                          scenario_id: str, enabled: bool = False, headers: dict[str, Any] | None = None,
                          timeout_seconds: float = 45) -> dict[str, Any]:
    """Run CFO, COO, and Risk claim selection concurrently after complete validation.

    Per-role provider faults are isolated.  Validation faults are raised before any
    task exists, and cancellation of this outer coroutine is always propagated.
    """
    if enabled is not True:
        raise PermissionError("unreviewed Monte Carlo role analysis requires enabled=True")
    if type(timeout_seconds) not in (int, float) or isinstance(timeout_seconds, bool) or not math.isfinite(float(timeout_seconds)) or not 0 < float(timeout_seconds) <= 45:
        raise ValueError("timeout_seconds must be finite and in the range (0, 45]")
    provider_kind = getattr(provider, "kind", None)
    if not isinstance(provider_kind, str) or not provider_kind:
        raise ValueError("provider must declare a non-empty actual kind")

    frozen_request, frozen_response, request_sha, response_sha, resolver = _capture_validated(
        request, response, headers=headers, scenario_id=scenario_id)
    projections, source_bindings = _build_projections_and_bindings(
        frozen_request, frozen_response, scenario_id=scenario_id, request_sha=request_sha,
        response_sha=response_sha, resolve_pointer=resolver)
    catalogs: dict[Role, tuple[McClaim, ...]] = {
        role: tuple(build_mc_claim_catalog(projections[role], source_bindings[role])) for role in ROLES
    }
    if any(not catalog for catalog in catalogs.values()):
        raise ValueError("every MC role must have a non-empty code-authored claim catalog")

    async def one(role: Role) -> McRoleOutput:
        claims = catalogs[role]
        allowed = tuple(claim.id for claim in claims)
        payload = _provider_payload(role, projections[role], claims)
        schema = response_schema(role, allowed)
        try:
            raw = await asyncio.wait_for(provider.complete(role=role, system=_SYSTEM, payload=payload, schema=schema),
                                         timeout=float(timeout_seconds))
        except asyncio.TimeoutError:
            return _failure(role, "timeout")
        except asyncio.CancelledError:
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                raise
            return _failure(role, "cancelled")
        except Exception:
            return _failure(role, "provider_error")
        try:
            selection = ClaimSelection.model_validate(raw)
            if selection.role != role or not set(selection.claim_ids) <= set(allowed):
                raise ValueError("provider crossed a role claim boundary")
            _recheck_captured_bindings(claims, request=frozen_request, response=frozen_response,
                                       identity=_identity(frozen_response, scenario_id), response_sha=response_sha,
                                       resolve_pointer=resolver)
            return _render_selection(role, selection, claims)
        except Exception:
            return _failure(role, "invalid_response")

    tasks = [asyncio.create_task(one(role)) for role in ROLES]
    outputs = await asyncio.gather(*tasks)
    ready = sum(output.failure is None for output in outputs)
    state: Literal["ALL_READY", "PARTIAL", "UNAVAILABLE"] = (
        "ALL_READY" if ready == 3 else "UNAVAILABLE" if ready == 0 else "PARTIAL"
    )
    identity = _identity(frozen_response, scenario_id)
    data = _object(frozen_response["data"], "response.data")
    result = {
        "kind": KIND,
        "sourceMode": SOURCE_MODE,
        "executionContext": copy.deepcopy(data["executionContext"]),
        "humanReviewStatus": _UNREVIEWED_REVIEW,
        "decisionReady": False,
        "simulationId": identity.simulationId,
        "dataVersion": identity.dataVersion,
        "scenarioId": scenario_id,
        "requestId": _require_string(frozen_response.get("requestId"), "response.requestId"),
        "requestSha256": request_sha,
        "responseSha256": response_sha,
        "monteCarloRuns": _require_int(_object(data["simulation"], "simulation").get("monteCarloRuns"), "monteCarloRuns", nonnegative=True),
        "modelProvider": {"kind": provider_kind},
        "state": state,
        "outputs": [output.model_dump(mode="json") for output in outputs],
    }
    if result["executionContext"].get("decisionReady") is not False:
        raise ValueError("an MC development analysis cannot become decision ready")
    return result


__all__ = [
    "CfoProjection", "CooProjection", "DevClaimStubProvider", "KIND", "McClaim", "McRoleOutput",
    "MetricBinding", "ROLES", "RiskProjection", "SOURCE_MODE", "build_mc_claim_catalog",
    "build_mc_projections", "response_schema", "run_mc_parallel",
]
