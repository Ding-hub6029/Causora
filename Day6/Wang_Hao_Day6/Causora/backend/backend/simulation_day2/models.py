"""Internal Day 2 deterministic data, not the public SimulateSuccess v1 DTO.

A deterministic run has neither a stockout probability nor a cash P90. The
unreviewed demo policy is explicitly marked non-decision and cannot be promoted
by simply changing a field in the request.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Day2Policy(Strict):
    assumptionStatus: Literal["UNAPPROVED_TEST_INPUT"]
    horizonStartDate: date
    openingInventoryEffectiveDate: date
    openingInventoryUnits: Annotated[int, Field(ge=0)]
    openingInventorySource: str
    sellingPriceUsdPerUnit: Annotated[Decimal, Field(gt=0)]
    lostContributionMarginUsdPerUnit: Annotated[Decimal, Field(ge=0)]
    holdingCostUsdPerUnitWeek: Annotated[Decimal, Field(ge=0)]
    safetyStockUnits: Annotated[int, Field(ge=0)]
    targetStockUnits: Annotated[int, Field(gt=0)]
    cashTiming: Literal["at_order"]
    roundingMode: Literal["half_even"]
    demandMode: Literal["history_rescaled_to_scenario_units"]
    leadTimeMode: Literal["seed_rotated_empirical_cycle"]
    leadStressAppliesTo: Literal["A_only", "all_suppliers"]
    commitmentSchedule: Literal["linear_weekly"]
    purchaseRecognition: Literal["at_order"]
    holdingBasis: Literal["available_ending_average"]

    @model_validator(mode="after")
    def nonempty_and_dated(self):
        if self.openingInventoryEffectiveDate != self.horizonStartDate:
            raise ValueError("opening inventory must be supplied as of the simulation horizon start")
        if not self.openingInventorySource.strip():
            raise ValueError("opening inventory source or explicit assumption is required")
        if "public/demo/opening_inventory.csv" in self.openingInventorySource and self.horizonStartDate != date(2026, 10, 4):
            raise ValueError("the 2026-10-04 inventory CSV is not inventory at renewal; supply an explicit bridge estimate")
        return self


class WeekTrace(Strict):
    week: Annotated[int, Field(ge=1)]
    startDate: date
    openingUnits: Annotated[int, Field(ge=0)]
    arrivalsA: Annotated[int, Field(ge=0)]
    arrivalsB: Annotated[int, Field(ge=0)]
    demandUnits: Annotated[int, Field(ge=0)]
    availableUnits: Annotated[int, Field(ge=0)]
    fulfilledUnits: Annotated[int, Field(ge=0)]
    lostUnits: Annotated[int, Field(ge=0)]
    endingUnits: Annotated[int, Field(ge=0)]
    onOrderUnitsBefore: Annotated[int, Field(ge=0)]
    inventoryPositionBefore: Annotated[int, Field(ge=0)]
    reorderPointUnits: Annotated[int, Field(ge=0)]
    orderedA: Annotated[int, Field(ge=0)]
    orderedB: Annotated[int, Field(ge=0)]
    sampledLeadDaysA: int | None
    sampledLeadDaysB: int | None
    plannedArrivalWeekA: int | None
    plannedArrivalWeekB: int | None
    onOrderUnitsAfter: Annotated[int, Field(ge=0)]
    holdingRawUsd: str
    stockoutLossRawUsd: str
    basePurchaseRawUsd: str
    renewalPremiumRawUsd: str
    terminationFeeRawUsd: str


class DeterministicCell(Strict):
    scenarioId: Literal["baseline", "demand-drop", "lead-stress"]
    optionId: Literal["D0", "D1", "D2"]
    demandUnits: Annotated[int, Field(ge=0)]
    fulfilledUnits: Annotated[int, Field(ge=0)]
    lostUnits: Annotated[int, Field(ge=0)]
    orderedUnitsA: Annotated[int, Field(ge=0)]
    orderedUnitsB: Annotated[int, Field(ge=0)]
    deliveredUnitsA: Annotated[int, Field(ge=0)]
    deliveredUnitsB: Annotated[int, Field(ge=0)]
    unitsInTransitAtEnd: Annotated[int, Field(ge=0)]
    endingInventoryUnits: Annotated[int, Field(ge=0)]
    stockoutOccurred: bool
    serviceLevel: Annotated[float, Field(ge=0, le=1)]
    feasible: bool
    revenueUsd: int
    grossProfitUsd: int
    grossMargin: float | None
    grossMarginStatus: Literal["VALID", "INVALID_REVENUE_ZERO"]
    cashOutflowUsd: Annotated[int, Field(ge=0)]
    costBreakdownUsd: dict[Literal["purchase", "holding", "stockoutLoss", "renewalPremium", "terminationFee"], int]
    tcoUsd: Annotated[int, Field(ge=0)]
    weeklyTrace: Annotated[list[WeekTrace], Field(min_length=104, max_length=104)]

    @model_validator(mode="after")
    def totals(self):
        if self.demandUnits != self.fulfilledUnits + self.lostUnits:
            raise ValueError("lost-sales identity failed")
        if self.tcoUsd != sum(self.costBreakdownUsd.values()):
            raise ValueError("TCO does not reconcile")
        if self.grossMarginStatus == "INVALID_REVENUE_ZERO" and self.grossMargin is not None:
            raise ValueError("zero revenue must not have a margin")
        return self


class DeterministicPreview(Strict):
    kind: Literal["CAUSORA_DAY2_INTERNAL_DETERMINISTIC_PREVIEW_V1"]
    status: Literal["UNREVIEWED_TEST_ONLY_NO_RECOMMENDATION", "REVIEWED_SYNTHETIC_POLICY_UNAPPROVED_NO_RECOMMENDATION"]
    decisionReady: Literal[False]
    internalSchemaVersion: Literal["jinzhu.deterministic-preview.v1"]
    referencedContractVersion: Literal["causora.contract.v1"]
    sourceDataVersion: str
    previewId: str
    formulaVersion: Literal["tco-v1"]
    seed: Annotated[int, Field(ge=0)]
    weeks: Literal[104]
    deterministicRuns: Literal[1]
    monteCarloRuns: Literal[0]
    reviewStatus: Literal["PENDING_HUMAN_REVIEW", "SELF_ATTESTED_SYNTHETIC_REVIEW"]
    reviewSha256: str | None
    engineSourceSha256: dict[str, str]
    assumptionStatus: Literal["UNAPPROVED_TEST_INPUT"]
    note: str
    inputHashesSha256: dict[str, str]
    intermediateManifestSha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    unitPricesUsd: dict[Literal["A", "B"], float]
    policy: Day2Policy
    matrix: dict[Literal["baseline", "demand-drop", "lead-stress"], list[DeterministicCell]]

    @model_validator(mode="after")
    def full_matrix(self):
        if (self.reviewStatus == "PENDING_HUMAN_REVIEW") != (self.reviewSha256 is None):
            raise ValueError("review status must agree with the verified review digest")
        if set(self.matrix) != {"baseline", "demand-drop", "lead-stress"}:
            raise ValueError("one deterministic matrix per scenario required")
        for scenario, cells in self.matrix.items():
            if len(cells) != 3 or {c.optionId for c in cells} != {"D0", "D1", "D2"} or any(c.scenarioId != scenario for c in cells):
                raise ValueError("matrix needs exactly one D0/D1/D2 per scenario")
        return self
