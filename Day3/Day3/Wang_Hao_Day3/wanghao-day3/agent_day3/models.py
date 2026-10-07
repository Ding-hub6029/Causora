"""Internal Day 3 models.

They are deliberately narrower than the frozen frontend contract: this module
emits role drafts only, never a BoardroomResponse, Critic decision, or Brief.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator
from .narrative_safety import assert_no_free_numeric_language

from .wire_models import (BoardroomSnapshot, ContractConstraint, DecisionOption,
                          EvidenceRecord, MetricCell, OptionId, Role,
                          Scenario, ScenarioSelection, SimulationResult,
                          StrictModel)

Mode = Literal["LOCAL_MOCK", "SIMULATION_READY"]
ProviderKind = Literal["OFFLINE_STUB", "MODEL_PROXY", "TEST_DOUBLE"]


class CfoOption(StrictModel):
    optionId: OptionId
    expectedTcoUsd: int
    cashOutflowP90Usd: int
    deltaTcoUsd: int
    purchaseUsd: int
    holdingUsd: int
    stockoutLossUsd: int
    renewalPremiumUsd: int
    terminationFeeUsd: int


class CfoView(StrictModel):
    role: Literal["CFO"] = "CFO"
    scenarioId: str
    sourceMode: Mode
    options: list[CfoOption] = Field(min_length=3, max_length=3)


class CooOption(StrictModel):
    optionId: OptionId
    stockoutProbability: float = Field(ge=0, le=1)
    serviceLevel: float = Field(ge=0, le=1)
    unitsFromA: int = Field(ge=0)
    unitsFromB: int = Field(ge=0)


class CooView(StrictModel):
    role: Literal["COO"] = "COO"
    scenarioId: str
    sourceMode: Mode
    demandUnits24m: int = Field(ge=0)
    leadTimeMultiplier: float = Field(gt=0)
    options: list[CooOption] = Field(min_length=3, max_length=3)


class RiskContract(StrictModel):
    """Only clause-derived values / derived contract state; never evidence quotes."""

    renewalLocked: bool
    renewalNoticeDays: int = Field(ge=0)
    renewalTermMonths: int = Field(gt=0)
    renewalPriceIncreasePct: float = Field(ge=0)
    minPurchaseShareA: float = Field(ge=0, le=1)
    forecastBasis: Literal["locked-at-renewal", "rolling"]
    lockedForecastUnits24m: int = Field(ge=0)
    minPurchaseUnitsA: int = Field(ge=0)
    terminationFeeUsd: int = Field(ge=0)


class RiskOption(StrictModel):
    optionId: OptionId
    feasible: bool
    cashOutflowP90Usd: int
    stockoutProbability: float = Field(ge=0, le=1)


class RiskView(StrictModel):
    role: Literal["Risk"] = "Risk"
    scenarioId: str
    sourceMode: Mode
    contractReview: Literal["PENDING_LOCAL_MOCK", "HUMAN_APPROVED"]
    matchedEvidenceIds: list[str] = Field(min_length=1)
    demandShockPercent: float
    leadTimeMultiplier: float = Field(gt=0)
    monteCarloRuns: int = Field(ge=0)
    contract: RiskContract
    options: list[RiskOption] = Field(min_length=3, max_length=3)


class AgentDraft(StrictModel):
    """Strict provider result. Numbers belong in typed refs, never prose."""

    role: Role
    headline: str = Field(min_length=5, max_length=120)
    reason_text: str = Field(min_length=10, max_length=700)
    option_ids: list[OptionId] = Field(min_length=1, max_length=3)
    metric_refs: list[str] = Field(min_length=1, max_length=8)
    evidence_ids: list[str] = Field(max_length=6)
    status: Literal["Aligned", "Watch"]

    @field_validator("headline", "reason_text")
    @classmethod
    def no_free_numeric_claims(cls, value: str) -> str:
        return assert_no_free_numeric_language(value)

    @model_validator(mode="after")
    def unique_structured_references(self) -> "AgentDraft":
        for values in (self.option_ids, self.metric_refs, self.evidence_ids):
            if len(values) != len(set(values)):
                raise ValueError("Structured references must be unique")
        return self


class InternalAgentOutput(StrictModel):
    """Local-only result. Mapping to frontend-shaped AgentOutput happens in adapter.py."""

    role: Role
    narrativeKey: str = Field(min_length=1)
    reasonText: str = Field(min_length=10, max_length=700)
    optionIds: list[OptionId]
    metricRefs: list[str]
    evidenceIds: list[str]
    availability: Literal["MOCK", "LIVE", "UNAVAILABLE"]


class AgentResult(StrictModel):
    role: Role
    headline: str
    output: InternalAgentOutput
    stance: Literal["Aligned", "Watch"] | None = None
    failure: Literal["provider_unavailable", "timeout", "invalid_response"] | None = None

    @model_validator(mode="after")
    def failure_and_output_agree(self) -> "AgentResult":
        if self.role != self.output.role:
            raise ValueError("Agent result role must equal output role")
        unavailable = self.output.availability == "UNAVAILABLE"
        if (self.failure is None) == unavailable:
            raise ValueError("Failure and output availability disagree")
        if (self.stance is None) == (self.failure is None):
            raise ValueError("Completed results require stance; failed results cannot set it")
        return self


class ParallelRun(StrictModel):
    simulationId: str
    dataVersion: str
    scenarioId: str
    sourceMode: Mode
    providerKind: ProviderKind
    state: Literal["ALL_READY", "PARTIAL", "UNAVAILABLE", "NO_FEASIBLE_OPTION"]
    outputs: list[AgentResult]
    criticStatus: Literal["NOT_IMPLEMENTED_DAY3"] = "NOT_IMPLEMENTED_DAY3"
    decisionReady: Literal[False] = False

    @model_validator(mode="after")
    def ordered_role_results(self) -> "ParallelRun":
        if self.state == "NO_FEASIBLE_OPTION":
            if self.outputs:
                raise ValueError("No-feasible selection must not call agents")
        elif [item.role for item in self.outputs] != ["CFO", "COO", "Risk"]:
            raise ValueError("A parallel run must retain all three ordered role results")
        return self


def cells_for(snapshot: BoardroomSnapshot) -> list[MetricCell]:
    return snapshot.simulation.matrix[snapshot.scenario.id]


__all__ = [
    "AgentDraft", "AgentResult", "BoardroomSnapshot", "CfoOption", "CfoView", "ContractConstraint",
    "CooOption", "CooView", "DecisionOption", "EvidenceRecord", "InternalAgentOutput", "MetricCell",
    "Mode", "OptionId", "ParallelRun", "ProviderKind", "RiskContract", "RiskOption", "RiskView", "Role",
    "Scenario", "ScenarioSelection", "SimulationResult", "cells_for",
]
