"""Final candidate DTO for the release-gated Matrix + Formula Trace v2 response.

The schema is final in shape but endpoint activation remains independently
release-gated. Request and pending/error envelopes stay causora.contract.v1.
"""
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from simulation_day1.wire_models import DecisionDelta, OptionId, ScenarioId, ScenarioSelection, SimulationResult
from simulation_day2.models import WeekTrace

TRACE_SCHEMA_VERSION = "causora.formula-trace.v1"
V2_VERSION = "causora.contract.v2"
COMPONENT_KEYS = {"purchase", "holding", "stockoutLoss", "renewalPremium", "terminationFee"}
REVIEWED_EXECUTION_MODE = "reviewed_release_gated"
UNREVIEWED_DEVELOPMENT_MODE = "unreviewed_development_only"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def _decimal(value: str, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be a finite decimal string") from exc
    if not parsed.is_finite():
        raise ValueError(f"{field} must be finite")
    return parsed


class TraceProvenance(Strict):
    kind: Literal[
        "reviewed_contract", "unreviewed_development_contract",
        "approved_operating_assumption", "unreviewed_development_assumption",
        "observed_synthetic_dataset", "derived_formula",
    ]
    status: Literal["reviewed", "unreviewed_development_only", "approved", "observed", "derived"]
    sourceId: str = Field(min_length=1)
    sourceFile: str | None = None
    # Source hash always identifies the source artifact (for example, a PDF),
    # never the separate human review record.
    sourceSha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    evidenceIds: list[str] = Field(default_factory=list)
    reviewRecordId: str | None = None
    reviewRecordSha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    note: str = Field(min_length=1)

    @model_validator(mode="after")
    def kind_status_and_review_record(self):
        expected = {
            "reviewed_contract": "reviewed",
            "unreviewed_development_contract": "unreviewed_development_only",
            "approved_operating_assumption": "approved",
            "unreviewed_development_assumption": "unreviewed_development_only",
            "observed_synthetic_dataset": "observed",
            "derived_formula": "derived",
        }[self.kind]
        if self.status != expected:
            raise ValueError("trace provenance kind/status mismatch")
        if self.kind == "reviewed_contract":
            if not self.evidenceIds or not self.reviewRecordId or not self.reviewRecordSha256 or not self.sourceSha256:
                raise ValueError("reviewed contract parameters require field evidence, source hash and separate review record")
        elif self.reviewRecordId is not None or self.reviewRecordSha256 is not None:
            raise ValueError("only reviewed contract provenance may contain a review record reference")
        return self


class TraceParameter(Strict):
    key: str = Field(min_length=1)
    value: str | int | float | bool
    unit: str = Field(min_length=1)
    provenance: TraceProvenance


class RoundingAudit(Strict):
    """Keeps raw Monte Carlo means distinct from display/accounting values."""
    rawMeanUsd: str = Field(min_length=1)
    displayedValueUsd: int = Field(ge=0)
    displayedMinusRawMeanUsd: str = Field(min_length=1)
    method: str = Field(min_length=1)

    @model_validator(mode="after")
    def reconcile_display_difference(self):
        raw = _decimal(self.rawMeanUsd, "rawMeanUsd")
        difference = _decimal(self.displayedMinusRawMeanUsd, "displayedMinusRawMeanUsd")
        if difference != Decimal(self.displayedValueUsd) - raw:
            raise ValueError("displayed-minus-raw amount does not reconcile")
        return self


class FormulaComponent(Strict):
    key: Literal["purchase", "holding", "stockoutLoss", "renewalPremium", "terminationFee"]
    formula: str = Field(min_length=1)
    inputKeys: list[str] = Field(min_length=1)
    valueUsd: int = Field(ge=0)
    roundingAudit: RoundingAudit

    @model_validator(mode="after")
    def display_equals_component(self):
        if self.roundingAudit.displayedValueUsd != self.valueUsd:
            raise ValueError("rounding audit displayed value differs from component")
        return self


class StockoutProbabilityBasis(Strict):
    value: float = Field(ge=0, le=1)
    numeratorStockoutRuns: int = Field(ge=0)
    denominatorRuns: int = Field(ge=1)
    definition: Literal["trials_with_at_least_one_lost_unit / monteCarloRuns"]

    @model_validator(mode="after")
    def reconcile_probability(self):
        if self.numeratorStockoutRuns > self.denominatorRuns or abs(self.value - self.numeratorStockoutRuns / self.denominatorRuns) > 1e-12:
            raise ValueError("stockout probability does not reconcile to trial counts")
        return self


class ServiceLevelBasis(Strict):
    value: float = Field(ge=0, le=1)
    fulfilledUnitsAllRuns: int = Field(ge=0)
    demandUnitsAllRuns: int = Field(ge=0)
    definition: Literal["fulfilled_units_all_runs / demand_units_all_runs"]

    @model_validator(mode="after")
    def reconcile_service(self):
        expected = self.fulfilledUnitsAllRuns / self.demandUnitsAllRuns if self.demandUnitsAllRuns else 1.0
        if self.fulfilledUnitsAllRuns > self.demandUnitsAllRuns or abs(self.value - expected) > 1e-12:
            raise ValueError("service level does not reconcile to aggregate quantities")
        return self


class CashP90Basis(Strict):
    valueUsd: int = Field(ge=0)
    method: Literal["nearest_rank_ceil_0.90N"]
    percentile: Literal[0.9]
    rankOneBased: int = Field(ge=1)
    denominatorRuns: int = Field(ge=1)
    includedCashComponents: list[Literal["purchase", "holding", "renewalPremium", "terminationFee"]]
    excludedNonCashComponents: list[Literal["stockoutLoss"]]
    perRunRounding: Literal["whole_usd_half_even"]

    @model_validator(mode="after")
    def reconcile_rank_and_lines(self):
        if self.rankOneBased != (9 * self.denominatorRuns + 9) // 10:
            raise ValueError("cash P90 rank differs from ceil(0.9N)")
        if self.includedCashComponents != ["purchase", "holding", "renewalPremium", "terminationFee"]:
            raise ValueError("cash P90 line inclusion differs from the frozen formula")
        if self.excludedNonCashComponents != ["stockoutLoss"]:
            raise ValueError("cash P90 must explicitly exclude stockout loss")
        return self


class SamplePath(Strict):
    sampleRunIndex: int = Field(ge=0)
    classification: Literal["single_realised_trial_not_aggregate"]
    note: str = Field(min_length=1)
    weeks: list[dict[str, Any]] = Field(min_length=104, max_length=104)

    @model_validator(mode="after")
    def validate_week_wire_rows(self):
        if "not" not in self.note.lower() or not any(word in self.note.lower() for word in ("average", "expectation", "aggregate")):
            raise ValueError("sample path note must explicitly reject aggregate interpretation")
        for row in self.weeks:
            WeekTrace.model_validate_json(json.dumps(row, ensure_ascii=False, allow_nan=False))
        return self


class TraceRunIdentity(Strict):
    executionMode: Literal[REVIEWED_EXECUTION_MODE, UNREVIEWED_DEVELOPMENT_MODE]
    reviewRecordId: str | None = None
    reviewRecordSha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    contractPayloadSha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    policyApprovalReference: str = Field(min_length=1)
    policyConfigurationId: str = Field(min_length=1)
    policySha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    contractApprovalReference: str = Field(min_length=1)
    contractReleaseRecordSha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_mode_identity(self):
        if self.executionMode == REVIEWED_EXECUTION_MODE:
            if not self.reviewRecordId or not self.reviewRecordSha256:
                raise ValueError("reviewed execution requires a separate verified review record")
        elif self.reviewRecordId is not None or self.reviewRecordSha256 is not None:
            raise ValueError("unreviewed development execution must not claim a review record")
        return self


class FormulaTrace(Strict):
    traceSchemaVersion: Literal[TRACE_SCHEMA_VERSION]
    simulationId: str = Field(min_length=1)
    dataVersion: str = Field(min_length=1)
    formulaVersion: Literal["tco-v1"]
    scenarioId: ScenarioId
    optionId: OptionId
    runIdentity: TraceRunIdentity
    parameters: list[TraceParameter] = Field(min_length=1)
    components: list[FormulaComponent] = Field(min_length=5, max_length=5)
    expectedTcoUsd: int = Field(ge=0)
    stockoutProbability: StockoutProbabilityBasis
    serviceLevel: ServiceLevelBasis
    cashOutflowP90: CashP90Basis
    summaryRoundingRule: str = Field(min_length=1)
    samplePath: SamplePath

    @model_validator(mode="after")
    def reconcile_trace(self):
        if {component.key for component in self.components} != COMPONENT_KEYS:
            raise ValueError("trace must contain every TCO component exactly once")
        parameter_keys = [parameter.key for parameter in self.parameters]
        if len(set(parameter_keys)) != len(parameter_keys):
            raise ValueError("trace parameter keys must be unique")
        unresolved = {key for component in self.components for key in component.inputKeys} - set(parameter_keys)
        if unresolved:
            raise ValueError(f"component inputKeys do not resolve: {sorted(unresolved)}")
        for parameter in self.parameters:
            if parameter.key.startswith("contract.") and parameter.provenance.kind not in {"reviewed_contract", "unreviewed_development_contract"}:
                raise ValueError("contract parameter lacks field-specific reviewed or development provenance")
        if sum(component.valueUsd for component in self.components) != self.expectedTcoUsd:
            raise ValueError("trace component sum differs from expected TCO")
        if self.samplePath.sampleRunIndex >= self.stockoutProbability.denominatorRuns:
            raise ValueError("sample path index is outside the Monte Carlo run range")
        if self.stockoutProbability.denominatorRuns != self.cashOutflowP90.denominatorRuns:
            raise ValueError("trace statistics use different trial denominators")
        return self


class SimulateResponseV2(Strict):
    simulation: SimulationResult
    deltas: list[DecisionDelta]
    selections: dict[ScenarioId, ScenarioSelection]
    traces: dict[ScenarioId, dict[OptionId, FormulaTrace]]
    executionContext: "ExecutionContext"

    @model_validator(mode="after")
    def align_trace_matrix(self):
        if set(self.traces) != set(self.simulation.matrix):
            raise ValueError("traces must cover every matrix scenario")
        if len(self.deltas) != 9:
            raise ValueError("v2 response requires nine decision deltas")
        for scenario_id, cells in self.simulation.matrix.items():
            by_option = self.traces[scenario_id]
            if set(by_option) != {"D0", "D1", "D2"}:
                raise ValueError("each scenario requires D0/D1/D2 traces")
            cell_by_option = {cell.optionId: cell for cell in cells}
            for option_id, trace in by_option.items():
                cell = cell_by_option[option_id]
                if (trace.scenarioId, trace.optionId, trace.simulationId, trace.dataVersion, trace.formulaVersion) != (scenario_id, option_id, self.simulation.simulationId, self.simulation.dataVersion, self.simulation.formulaVersion):
                    raise ValueError("trace identity differs from matrix simulation")
                if trace.expectedTcoUsd != cell.expectedTco or trace.stockoutProbability.value != cell.stockoutProbability or trace.serviceLevel.value != cell.serviceLevel or trace.cashOutflowP90.valueUsd != cell.cashOutflowP90:
                    raise ValueError("trace statistics differ from matrix cell")
                for component in trace.components:
                    if component.valueUsd != getattr(cell.breakdown, component.key):
                        raise ValueError("trace component differs from matching matrix breakdown line")
                if trace.runIdentity.executionMode != self.executionContext.mode:
                    raise ValueError("trace execution mode differs from response execution context")
        if self.executionContext.mode == UNREVIEWED_DEVELOPMENT_MODE and "UNREVIEWED_DEV_ONLY" not in self.simulation.dataVersion:
            raise ValueError("unreviewed development results require an explicit dataVersion marker")
        return self


class ExecutionContext(Strict):
    """Response-wide status that prevents development calculations looking reviewed."""
    mode: Literal[REVIEWED_EXECUTION_MODE, UNREVIEWED_DEVELOPMENT_MODE]
    banner: str = Field(min_length=1)
    humanReviewStatus: Literal["reviewed", "not_reviewed_development_only"]
    policyStatus: Literal["approved", "unapproved_development_only"]
    contractReleaseStatus: Literal["released", "not_released_development_only"]
    decisionReady: bool

    @model_validator(mode="after")
    def status_matches_mode(self):
        if self.mode == REVIEWED_EXECUTION_MODE:
            if (self.humanReviewStatus, self.policyStatus, self.contractReleaseStatus, self.decisionReady) != ("reviewed", "approved", "released", True):
                raise ValueError("reviewed execution context has inconsistent statuses")
        elif (self.humanReviewStatus, self.policyStatus, self.contractReleaseStatus, self.decisionReady) != ("not_reviewed_development_only", "unapproved_development_only", "not_released_development_only", False):
            raise ValueError("unreviewed development context must not be decision-ready")
        return self


class ApiSuccessV2(Strict):
    schemaVersion: Literal[V2_VERSION]
    dataVersion: str = Field(min_length=1)
    requestId: str = Field(min_length=1)
    data: SimulateResponseV2
