"""Typed Day 1 DTOs mirroring lib/contracts.ts and lib/types.ts exactly.

Wire names remain camelCase. This is a validation boundary, not an HTTP app or
104-week simulator; schemaVersion stays causora.contract.v1. No fields are added
to the shared payload and LOCAL MOCK remains labelled as such.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


OptionId = Literal["D0", "D1", "D2"]
ScenarioId = Literal["baseline", "demand-drop", "lead-stress"]
Version = Literal["causora.contract.v1"]
Money = Annotated[int, Field(ge=0)]
Units = Annotated[int, Field(ge=0)]
Fraction = Annotated[float, Field(ge=0, le=1)]


class Scenario(WireModel):
    id: ScenarioId
    label: str
    tag: str
    demandShock: Annotated[float, Field(ge=-100, le=1000)]
    demandUnits24m: Units
    leadTime: str
    leadTimeMultiplier: Annotated[float, Field(gt=0)]
    description: str


class DecisionOption(WireModel):
    id: OptionId
    label: str
    shareA: Fraction
    terminateA: bool
    allocation: str
    short: str
    description: str

    @model_validator(mode="after")
    def frozen_meaning(self):
        if (self.shareA, self.terminateA) != {"D0": (1.0, False), "D1": (0.6, False), "D2": (0.0, True)}[self.id]:
            raise ValueError(f"{self.id}: fixed allocation/exit meaning changed")
        return self


class EvidenceRecord(WireModel):
    id: str
    sourceFile: str
    page: Annotated[int, Field(ge=1)]
    quote: str
    locatorBbox: tuple[float, float, float, float] | None
    extractedField: str
    extractedValue: str
    matchMethod: Literal["exact", "fuzzy"]
    matchScore: Fraction
    quoteMatched: bool

    @model_validator(mode="after")
    def quote_contains_claim_when_matched(self):
        if self.quoteMatched and self.extractedValue not in self.quote:
            raise ValueError("quoteMatched cannot be true when quote omits extractedValue")
        if self.locatorBbox is not None:
            x0, y0, x1, y1 = self.locatorBbox
            if x1 <= x0 or y1 <= y0:
                raise ValueError("inverted PDF locator rectangle")
        return self


class ContractConstraint(WireModel):
    decisionDate: date
    renewalDate: date
    daysToRenewal: Annotated[int, Field(ge=0)]
    renewalNoticeDays: Annotated[int, Field(ge=0)]
    noticeDeadline: date
    noticeSent: bool
    noticeRecordSource: str
    renewalLocked: bool
    renewalTermMonths: Annotated[int, Field(ge=0)]
    renewalPriceIncreasePct: Fraction
    minPurchaseShareA: Fraction
    forecastBasis: Literal["locked-at-renewal", "rolling"]
    lockedForecastUnits24m: Units
    minPurchaseUnitsA: Units
    terminationFeeUsd: Money
    evidenceIds: list[str]

    @model_validator(mode="after")
    def dates_and_commitment(self):
        if (self.renewalDate - self.decisionDate).days != self.daysToRenewal:
            raise ValueError("daysToRenewal differs from dates")
        if self.renewalDate - timedelta(days=self.renewalNoticeDays) != self.noticeDeadline:
            raise ValueError("noticeDeadline differs from renewal notice window")
        if self.renewalLocked != (self.decisionDate > self.noticeDeadline and not self.noticeSent):
            raise ValueError("renewalLocked requires explicit noticeSent and dated deadline")
        if self.minPurchaseUnitsA != round(self.lockedForecastUnits24m * self.minPurchaseShareA):
            raise ValueError("minPurchaseUnitsA inconsistent with forecast and share")
        return self


class VariableInput(WireModel):
    name: str
    value: str
    source: str


class BusinessVariable(WireModel):
    key: str
    name: str
    value: str
    unit: str
    source: str
    meaning: str
    inputs: list[VariableInput]


class CostBreakdown(WireModel):
    purchase: Money
    holding: Money
    stockoutLoss: Money
    renewalPremium: Money
    terminationFee: Money


class MetricCell(WireModel):
    optionId: OptionId
    feasible: bool
    expectedTco: Money
    stockoutProbability: Fraction
    serviceLevel: Fraction
    cashOutflowP90: Money
    breakdown: CostBreakdown
    unitsFromA: Units
    unitsFromB: Units
    tone: Literal["neutral", "recommended", "risk"]

    @model_validator(mode="after")
    def sum_five_lines(self):
        if self.expectedTco != sum(self.breakdown.model_dump().values()):
            raise ValueError("expectedTco must equal its five cost components")
        return self


class UnitPrices(WireModel):
    A: Annotated[float, Field(ge=0)]
    B: Annotated[float, Field(ge=0)]


class SimulationResult(WireModel):
    simulationId: str
    seed: Annotated[int, Field(ge=0)]
    dataVersion: str
    formulaVersion: Literal["tco-v1"]
    weeks: Literal[104]
    monteCarloRuns: Annotated[int, Field(ge=0)]
    unitPricesUsd: UnitPrices
    matrix: dict[ScenarioId, list[MetricCell]]

    @model_validator(mode="after")
    def unique_cells(self):
        if set(self.matrix) != {"baseline", "demand-drop", "lead-stress"}:
            raise ValueError("demo matrix must contain three scenarios")
        for cells in self.matrix.values():
            if len(cells) != 3 or {c.optionId for c in cells} != {"D0", "D1", "D2"}:
                raise ValueError("every scenario needs one cell for each D0/D1/D2")
        return self


class DecisionDelta(WireModel):
    scenarioId: ScenarioId
    optionId: OptionId
    baselineOptionId: Literal["D0"]
    deltaTco: int
    deltaStockoutPp: float
    deltaServicePp: float
    deltaCashP90: int


class AgentOutput(WireModel):
    role: Literal["CFO", "COO", "Risk"]
    accent: str
    focus: str
    headline: str
    body: str
    metrics: list[str]
    status: Literal["Aligned", "Watch"]


class CriticMechanism(WireModel):
    scenarioId: ScenarioId
    forecastBasis: Literal["locked-at-renewal", "rolling"]
    lockedForecastUnits24m: Units
    minPurchaseUnitsA: Units
    scenarioDemandUnits24m: Units
    committedExcessUnits: int
    holdingCostDeltaUsd: dict[OptionId, int]

    @model_validator(mode="after")
    def all_options_present(self):
        if set(self.holdingCostDeltaUsd) != {"D0", "D1", "D2"}:
            raise ValueError("Critic mechanism needs exactly D0/D1/D2 deltas")
        return self


class CriticIssue(WireModel):
    severity: str
    headline: str
    body: str
    evidenceIds: list[str]
    mechanism: CriticMechanism


class ConstraintViolation(WireModel):
    optionId: OptionId
    code: Literal["infeasible", "stockout_threshold", "cash_ceiling"]


class ScenarioSelection(WireModel):
    scenarioId: ScenarioId
    status: Literal["selected", "no_feasible_option"]
    recommendedOptionId: OptionId | None
    constraintViolations: list[ConstraintViolation]

    @model_validator(mode="after")
    def match_status(self):
        if (self.status == "selected") != (self.recommendedOptionId is not None):
            raise ValueError("selected requires option ID; no_feasible_option requires null")
        return self


class LocalSelectedBrief(WireModel):
    recommendedOptionId: OptionId
    recommendation: str
    rationale: str
    metricRefs: list[str]
    formula: str
    formulaVersion: Literal["tco-v1"]
    formulaNotes: list[str]
    guardrail: str


class SelectedDecisionBriefRef(LocalSelectedBrief):
    scenarioId: ScenarioId
    status: Literal["selected"]


class NoFeasibleBrief(WireModel):
    scenarioId: ScenarioId
    status: Literal["no_feasible_option"]
    recommendedOptionId: None
    constraintViolations: list[ConstraintViolation]
    message: str


DecisionBriefRef = Annotated[SelectedDecisionBriefRef | NoFeasibleBrief, Field(discriminator="status")]


class IntakeFile(WireModel):
    id: str
    label: str
    type: str
    detail: str
    size: str
    status: str
    icon: str
    path: str


class MockMeta(WireModel):
    schemaVersion: Version
    product: str
    version: str
    dataVersion: str
    status: str
    seed: Annotated[int, Field(ge=0)]
    notice: str


class MockData(WireModel):
    meta: MockMeta
    intake: list[IntakeFile]
    evidence: list[EvidenceRecord]
    contract: ContractConstraint
    variables: list[BusinessVariable]
    scenarios: list[Scenario]
    options: list[DecisionOption]
    simulation: SimulationResult
    boardroom: list[AgentOutput]
    critic: CriticIssue
    brief: LocalSelectedBrief

    @model_validator(mode="after")
    def local_snapshot_matches(self):
        if self.meta.dataVersion != self.simulation.dataVersion or self.meta.seed != self.simulation.seed:
            raise ValueError("mock metadata and simulation differ")
        return self


class GoldenRequest(WireModel):
    scenario: ScenarioId
    options: list[OptionId]
    # Legacy local Golden UI snapshot uses whole slider percent (12), not
    # SimulateRequest's wire fraction (0.12); do not silently change its data.
    riskThreshold: Annotated[float, Field(ge=0, le=100)]


class GoldenResponse(WireModel):
    recommendedOptionId: OptionId
    status: str


class GoldenRun(WireModel):
    label: str
    verifiedAt: str
    verifiedAtNote: str
    dataVersion: str
    seed: Annotated[int, Field(ge=0)]
    snapshotHash: str
    request: GoldenRequest
    response: GoldenResponse
    snapshot: MockData
    notice: str


class SimulateRequest(WireModel):
    schemaVersion: Version
    datasetId: str
    scenarios: list[Scenario]
    options: list[DecisionOption]
    seed: Annotated[int, Field(ge=0)]
    riskThreshold: Fraction
    budgetCeilingUsd: Money

    @model_validator(mode="after")
    def demo_ids(self):
        if len(self.scenarios) != 3 or {s.id for s in self.scenarios} != {"baseline", "demand-drop", "lead-stress"}:
            raise ValueError("Day 1 demo requires exactly three unique scenarios")
        if len(self.options) != 3 or {o.id for o in self.options} != {"D0", "D1", "D2"}:
            raise ValueError("Day 1 demo requires exactly D0/D1/D2 once")
        return self


class SimulateResponse(WireModel):
    simulation: SimulationResult
    deltas: list[DecisionDelta]
    selections: dict[ScenarioId, ScenarioSelection]

    @model_validator(mode="after")
    def one_selection_per_scenario(self):
        if set(self.selections) != set(self.simulation.matrix):
            raise ValueError("missing scenario selection")
        if any(k != v.scenarioId for k, v in self.selections.items()):
            raise ValueError("selection key and scenarioId differ")
        if len(self.deltas) != 9 or {(d.scenarioId, d.optionId) for d in self.deltas} != {(s, o) for s in self.simulation.matrix for o in ("D0", "D1", "D2")}:
            raise ValueError("missing or duplicate scenario-option deltas")
        return self


class DatasetResult(WireModel):
    datasetId: str
    preprocessStatus: Literal["ready"]
    dataVersion: str
    intake: list[IntakeFile]
    evidence: list[EvidenceRecord]
    contract: ContractConstraint
    variables: list[BusinessVariable]


class BoardroomRequest(WireModel):
    schemaVersion: Version
    simulationId: str
    dataVersion: str
    scenarioId: ScenarioId


class NumericGuardrail(WireModel):
    passed: bool
    rejectedClaims: list[str]


class BoardroomResponse(WireModel):
    scenarioId: ScenarioId
    agentOutputs: list[AgentOutput]
    criticIssues: list[CriticIssue]
    brief: DecisionBriefRef
    numericGuardrail: NumericGuardrail

    @model_validator(mode="after")
    def bind_scenario(self):
        if self.brief.scenarioId != self.scenarioId:
            raise ValueError("Boardroom brief scenario mismatch")
        if isinstance(self.brief, NoFeasibleBrief) and (self.agentOutputs or self.criticIssues):
            raise ValueError("no-feasible boardroom must not invent agent outputs")
        return self


class EvidenceResponse(WireModel):
    evidence: EvidenceRecord


class HealthData(WireModel):
    service: str
    simulation: str
    evidence: str
    provider: str


class ApiError(WireModel):
    code: Literal["validation_error", "not_found", "provider_timeout", "simulation_failed", "internal_error"]
    message: str
    details: dict[str, object] = Field(default_factory=dict)
    requestId: str


T = TypeVar("T")


class ApiSuccess(WireModel, Generic[T]):
    schemaVersion: Version
    dataVersion: str
    requestId: str
    data: T


class ApiFailure(WireModel):
    schemaVersion: Version
    requestId: str
    error: ApiError


# Schema root models below mirror the complete v1 API envelope families.
DatasetSuccess = ApiSuccess[DatasetResult]
SimulateSuccess = ApiSuccess[SimulateResponse]
BoardroomSuccess = ApiSuccess[BoardroomResponse]
EvidenceSuccess = ApiSuccess[EvidenceResponse]
HealthSuccess = ApiSuccess[HealthData]
GoldenSuccess = ApiSuccess[GoldenRun]
