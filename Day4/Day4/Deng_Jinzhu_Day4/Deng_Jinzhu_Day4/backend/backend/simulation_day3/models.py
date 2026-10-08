"""Non-public statistics schema; deliberately NOT an embeddable v1 success.

Individual cell and delta names mirror the shared v1 DTO, but this preview
contains neither SimulateResponse nor a recommendedOptionId/selected result.
"""
from __future__ import annotations

from math import isclose
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from simulation_day1.wire_models import (
    ConstraintViolation, DecisionDelta, MetricCell, OptionId, ScenarioId, UnitPrices,
)
from simulation_day2.models import WeekTrace


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CellTrace(Strict):
    scenarioId: ScenarioId
    optionId: OptionId
    sampleRunIndex: Literal[0]
    sampleRunNote: str
    weeks: Annotated[list[WeekTrace], Field(min_length=104, max_length=104)]
    reorderPointUnits: Annotated[int, Field(ge=0)]
    leadTimeSourceA: str
    leadTimeSourceB: str
    stockoutRuns: Annotated[int, Field(ge=0)]
    monteCarloRuns: Annotated[int, Field(ge=1)]
    fulfilledUnitsAllRuns: Annotated[int, Field(ge=0)]
    demandUnitsAllRuns: Annotated[int, Field(ge=0)]
    p90CashRankOneBased: Annotated[int, Field(ge=1)]
    cashOutflowP90Usd: Annotated[int, Field(ge=0)]
    meanOrderedAExact: str
    meanOrderedBExact: str
    rawMeanCostsUsd: dict[str, str]
    displayedWholeUsdBreakdown: dict[str, int]
    rawMeanRevenueUsd: str
    expectedRevenueUsd: Annotated[int, Field(ge=0)]
    expectedGrossProfitUsd: int
    grossMargin: float | None
    grossMarginStatus: Literal["VALID", "INVALID_REVENUE_ZERO"]
    summaryRoundingRule: str
    runCashSha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]

    @model_validator(mode="after")
    def basic_count_consistency(self):
        if self.stockoutRuns > self.monteCarloRuns or self.fulfilledUnitsAllRuns > self.demandUnitsAllRuns:
            raise ValueError("trial counts or fulfilled demand exceed totals")
        if self.p90CashRankOneBased != (9 * self.monteCarloRuns + 9) // 10:
            raise ValueError("P90 nearest rank differs from ceil(0.9 * runs)")
        if self.expectedGrossProfitUsd != self.expectedRevenueUsd - sum(self.displayedWholeUsdBreakdown.values()):
            raise ValueError("gross profit differs from computed revenue minus exact five-line TCO")
        if not self.expectedRevenueUsd:
            if self.grossMargin is not None or self.grossMarginStatus != "INVALID_REVENUE_ZERO":
                raise ValueError("zero revenue has no valid gross margin")
        elif (self.grossMarginStatus != "VALID" or self.grossMargin is None or
              not isclose(self.grossMargin, self.expectedGrossProfitUsd / self.expectedRevenueUsd,
                          rel_tol=0, abs_tol=1e-12)):
            raise ValueError("gross margin differs from computed gross profit / revenue")
        return self


class DistributionProvenance(Strict):
    demand: str
    supplierA: str
    supplierB: str
    supplierBParameters: dict[str, str | int]
    sellingPrice: str
    unitPrices: str
    randomGenerator: str
    drawsSha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    cashP90: Literal["nearest_rank_ceil_0.90N"]


class ConstraintScreening(Strict):
    scenarioId: ScenarioId
    status: Literal["screening_only_unapproved"]
    eligibleOptionIds: list[OptionId]
    constraintViolations: list[ConstraintViolation]

    @model_validator(mode="after")
    def unique_and_ordered(self):
        if self.eligibleOptionIds != [oid for oid in ("D0", "D1", "D2") if oid in self.eligibleOptionIds]:
            raise ValueError("eligible IDs must be unique and in D0/D1/D2 order")
        failed = {v.optionId for v in self.constraintViolations}
        if set(self.eligibleOptionIds) & failed or set(self.eligibleOptionIds) | failed != {"D0", "D1", "D2"}:
            raise ValueError("screening must account for every option without picking a winner")
        return self


class MonteCarloPreview(Strict):
    kind: Literal["CAUSORA_DAY3_INTERNAL_MONTE_CARLO_PREVIEW_V1"]
    internalSchemaVersion: Literal["jinzhu.mc-preview.v1"]
    referencedContractVersion: Literal["causora.contract.v1"]
    status: Literal["UNREVIEWED_SYNTHETIC_TEST_ONLY_NO_PUBLIC_SUCCESS"]
    decisionReady: Literal[False]
    reviewStatus: Literal["PENDING_11_HUMAN_REVIEW_ROWS"]
    policyStatus: Literal["UNAPPROVED_TEST_INPUT"]
    sourceDataVersion: str
    formulaVersion: Literal["tco-v1"]
    previewId: str
    seed: Annotated[int, Field(ge=0)]
    weeks: Literal[104]
    monteCarloRuns: Annotated[int, Field(ge=1, le=10000)]
    distributionProvenance: DistributionProvenance
    inputHashesSha256: dict[str, str]
    intermediateManifestSha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    engineSourceSha256: dict[str, str]
    note: str
    unitPricesUsd: UnitPrices
    computedMatrix: dict[ScenarioId, list[MetricCell]]
    decisionDeltas: list[DecisionDelta]
    constraintScreening: dict[ScenarioId, ConstraintScreening]
    formulaTraces: dict[ScenarioId, dict[OptionId, CellTrace]]

    @model_validator(mode="after")
    def matrix_and_trace(self):
        if set(self.computedMatrix) != {"baseline", "demand-drop", "lead-stress"}:
            raise ValueError("exactly three computed scenarios required")
        for cells in self.computedMatrix.values():
            if len(cells) != 3 or {c.optionId for c in cells} != {"D0", "D1", "D2"}:
                raise ValueError("exactly three fixed options per computed scenario required")
        if len(self.decisionDeltas) != 9 or {(d.scenarioId, d.optionId) for d in self.decisionDeltas} != {
                (sid, oid) for sid in self.computedMatrix for oid in ("D0", "D1", "D2")}:
            raise ValueError("each computed cell requires its own D0-based delta")
        if set(self.constraintScreening) != set(self.computedMatrix):
            raise ValueError("one non-decision screening per computed scenario")
        if any(key != row.scenarioId for key, row in self.constraintScreening.items()):
            raise ValueError("screening key differs from its scenario")
        if set(self.formulaTraces) != {"baseline", "demand-drop", "lead-stress"}:
            raise ValueError("exactly three independent scenario traces required")
        for sid, options in self.formulaTraces.items():
            if set(options) != {"D0", "D1", "D2"}:
                raise ValueError("one stochastic formula trace per fixed option")
            for oid, trace in options.items():
                if (trace.scenarioId, trace.optionId, trace.monteCarloRuns) != (sid, oid, self.monteCarloRuns):
                    raise ValueError("formula trace not bound to its matrix cell")
        return self
