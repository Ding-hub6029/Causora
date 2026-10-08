"""Internal draft adapter; explicitly not the frozen BoardroomResponse contract."""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .models import ParallelRun, ProviderKind
from .wire_models import Role, StrictModel

_DISPLAY = {
    "CFO": ("cobalt", "Financial exposure"),
    "COO": ("aqua", "Service continuity"),
    "Risk": ("coral", "Contract downside"),
}


class AgentOutput(StrictModel):
    """The frozen contract's AgentOutput shape, held only inside a Day 3 draft."""

    role: Role
    accent: str = Field(min_length=1)
    focus: str = Field(min_length=1)
    headline: str = Field(min_length=5, max_length=120)
    body: str = Field(min_length=10, max_length=700)
    metrics: list[str] = Field(min_length=1, max_length=8)
    status: Literal["Aligned", "Watch"]


class Day3AgentDraft(StrictModel):
    """A handoff containing only three role AgentOutput values.

    No Critic, Brief, numeric guardrail, API envelope, or decision approval is
    included. Consumers must not cast this model to BoardroomResponse.
    """

    kind: Literal["CAUSORA_WANG_DAY3_AGENT_DRAFT_V1"] = "CAUSORA_WANG_DAY3_AGENT_DRAFT_V1"
    schemaVersion: Literal["causora.contract.v1"] = "causora.contract.v1"
    dataVersion: str = Field(min_length=1)
    simulationId: str = Field(min_length=1)
    scenarioId: str = Field(min_length=1)
    sourceMode: Literal["LOCAL_MOCK", "SIMULATION_READY"]
    providerKind: ProviderKind
    agentOutputs: list[AgentOutput] = Field(min_length=3, max_length=3)
    criticStatus: Literal["NOT_IMPLEMENTED_DAY3"] = "NOT_IMPLEMENTED_DAY3"
    decisionReady: Literal[False] = False

    @model_validator(mode="after")
    def ordered_roles_and_no_live_stub(self) -> "Day3AgentDraft":
        if [item.role for item in self.agentOutputs] != ["CFO", "COO", "Risk"]:
            raise ValueError("Draft must contain exactly ordered CFO, COO, Risk outputs")
        if self.decisionReady is not False:
            raise ValueError("Day 3 drafts can never be decision-ready")
        return self


def to_frontend_draft(run: ParallelRun) -> Day3AgentDraft:
    """Map a complete run without inventing UI metrics or a synthetic Brief."""
    if run.state != "ALL_READY" or any(item.failure is not None for item in run.outputs):
        raise ValueError("Cannot portray a failed role as a complete agent draft")
    outputs: list[AgentOutput] = []
    for item in run.outputs:
        if item.stance is None or item.output.availability == "UNAVAILABLE":
            raise ValueError("Incomplete agent result cannot be adapted")
        accent, focus = _DISPLAY[item.role]
        # Use the actually validated provider refs rather than unrelated hard-coded display metric IDs.
        outputs.append(AgentOutput(role=item.role, accent=accent, focus=focus, headline=item.headline,
                                   body=item.output.reasonText, metrics=item.output.metricRefs,
                                   status=item.stance))
    return Day3AgentDraft(dataVersion=run.dataVersion, simulationId=run.simulationId,
                          scenarioId=run.scenarioId, sourceMode=run.sourceMode,
                          providerKind=run.providerKind, agentOutputs=outputs)
