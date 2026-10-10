"""Day 3 stochastic policy model.

`UNAPPROVED_TEST_INPUT` remains the only state accepted by the internal
preview. `TEAM_APPROVED` can be used only after the HTTP gate has obtained the
policy from an externally configured team verifier; a local JSON flag is never
trusted as approval.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PolicyStatus = Literal["UNAPPROVED_TEST_INPUT", "TEAM_APPROVED"]
LeadProvenance = Literal["USER_ASSUMED_UNAPPROVED", "TEAM_APPROVED_ASSUMPTION"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TriangularLead(Strict):
    minDays: Annotated[int, Field(ge=1, le=365)]
    modeDays: Annotated[int, Field(ge=1, le=365)]
    maxDays: Annotated[int, Field(ge=1, le=365)]
    provenance: LeadProvenance
    explanation: Annotated[str, Field(min_length=12)]

    @model_validator(mode="after")
    def ordered(self):
        if not self.minDays < self.maxDays or not self.minDays <= self.modeDays <= self.maxDays:
            raise ValueError("triangular fallback needs min < max and min <= mode <= max")
        return self


class OperatingPolicy(Strict):
    """Explicit operating assumptions; no deterministic lead-time mode leaks in."""
    assumptionStatus: PolicyStatus
    horizonStartDate: date
    openingInventoryEffectiveDate: date
    openingInventoryUnits: Annotated[int, Field(ge=0, le=1000000)]
    openingInventorySource: Annotated[str, Field(min_length=1)]
    sellingPriceUsdPerUnit: Annotated[Decimal, Field(gt=0)]
    lostContributionMarginUsdPerUnit: Annotated[Decimal, Field(ge=0)]
    holdingCostUsdPerUnitWeek: Annotated[Decimal, Field(ge=0)]
    safetyStockUnits: Annotated[int, Field(ge=0, le=1000000)]
    targetStockUnits: Annotated[int, Field(gt=0, le=1000000)]
    cashTiming: Literal["at_order"]
    roundingMode: Literal["half_even"]
    demandMode: Literal["empirical_weekly_bootstrap"]
    leadTimeMode: Literal["empirical_po_bootstrap_with_explicit_B_fallback"]
    leadStressAppliesTo: Literal["A_only", "all_suppliers"]
    commitmentSchedule: Literal["linear_weekly"]
    purchaseRecognition: Literal["at_order"]
    holdingBasis: Literal["available_ending_average"]

    @model_validator(mode="after")
    def dated_and_sourced(self):
        if self.openingInventoryEffectiveDate != self.horizonStartDate:
            raise ValueError("renewal-date opening inventory requires an explicit bridge estimate")
        if "public/demo/opening_inventory.csv" in self.openingInventorySource and self.horizonStartDate != date(2026, 10, 4):
            raise ValueError("the decision-date inventory CSV is not a renewal-date opening balance")
        if any(value > 10000 for value in (
                self.sellingPriceUsdPerUnit, self.lostContributionMarginUsdPerUnit,
                self.holdingCostUsdPerUnitWeek)):
            raise ValueError("unbounded monetary assumption exceeds internal safe arithmetic range")
        return self


class Day3Policy(Strict):
    policyStatus: PolicyStatus
    operatingPolicy: OperatingPolicy
    supplierBLeadFallback: TriangularLead
    monteCarloRuns: Annotated[int, Field(ge=1, le=10000)]
    demandMethod: Literal["empirical_weekly_bootstrap"]
    supplierALeadMethod: Literal["empirical_po_bootstrap"]
    supplierBLeadMethod: Literal["user_assumed_triangular"]
    cashP90Method: Literal["nearest_rank_ceil_0.90N"]
    meanCostRounding: Literal["whole_usd_half_even_after_mean"]

    @model_validator(mode="after")
    def consistent_approval_state(self):
        if self.operatingPolicy.assumptionStatus != self.policyStatus:
            raise ValueError("stochastic policy and physical policy approval status disagree")
        if ((self.policyStatus == "UNAPPROVED_TEST_INPUT" and self.supplierBLeadFallback.provenance != "USER_ASSUMED_UNAPPROVED") or
                (self.policyStatus == "TEAM_APPROVED" and self.supplierBLeadFallback.provenance != "TEAM_APPROVED_ASSUMPTION")):
            raise ValueError("supplier B fallback provenance differs from the policy approval state")
        return self
