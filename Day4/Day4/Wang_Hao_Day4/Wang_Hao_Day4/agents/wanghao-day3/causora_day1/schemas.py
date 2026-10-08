"""Wang Hao's strict internal Day 1 contracts; simulation output is NOT built here."""
from __future__ import annotations

import math
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .claim_checks import supported_claim


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EvidenceField(str, Enum):
    renewal_notice_days = "renewal_notice_days"
    auto_renew = "auto_renew"
    renewal_term_months = "renewal_term_months"
    renewal_price_increase_pct = "renewal_price_increase_pct"
    min_purchase_share_A = "min_purchase_share_A"
    termination_fee = "termination_fee"


def parse_evidence_field(value: object) -> object:
    if isinstance(value, str):
        try:
            return EvidenceField(value)
        except ValueError:
            pass
    return value


class EvidenceRecord(StrictModel):
    id: str = Field(pattern=r"^EV-[0-9]{3}$")
    source_file: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    page: int = Field(ge=1)
    quote: str = Field(min_length=5)
    # The actual source text and its [start,end) offsets in NORMALIZED page text.
    source_quote: str | None = None
    source_span: list[int] | None = Field(default=None, min_length=2, max_length=2)
    locator_bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)
    extracted_field: EvidenceField
    extracted_value: int | float | bool
    unit: Literal["days", "months", "percent", "share", "USD", "boolean"]
    match_method: Literal["exact", "fuzzy", "none"]
    # Internal score stays 0..100; frontend adapter explicitly divides by 100.
    match_score: float = Field(ge=0, le=100)
    quote_matched: bool
    manually_verified: bool = False

    @field_validator("extracted_field", mode="before")
    @classmethod
    def decode_field(cls, value: object) -> object:
        return parse_evidence_field(value)

    @field_validator("source_file")
    @classmethod
    def source_is_pdf_basename(cls, value: str) -> str:
        if "/" in value or "\\" in value or value in (".", "..") or not value.lower().endswith(".pdf"):
            raise ValueError("Only a PDF basename is allowed")
        return value

    @field_validator("locator_bbox", mode="before")
    @classmethod
    def finite_ordered_bbox(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, list) or len(value) != 4 or any(type(v) not in (float, int) or not math.isfinite(v) for v in value):
            raise ValueError("Locator must contain four finite coordinates")
        x0, y0, x1, y1 = value
        if not x0 < x1 or not y0 < y1 or x0 < 0 or y0 < 0:
            raise ValueError("Locator bounds must be ordered and nonnegative")
        return [float(v) for v in value]

    @field_validator("source_span", mode="before")
    @classmethod
    def ordered_span(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, list) or len(value) != 2 or any(type(v) is not int for v in value) or not 0 <= value[0] < value[1]:
            raise ValueError("Source span must be ordered integer [start,end) offsets")
        return value

    @model_validator(mode="after")
    def check_claim(self) -> "EvidenceRecord":
        if not supported_claim(self.extracted_field.value, self.extracted_value, self.unit, self.quote):
            raise ValueError("Evidence record quote/value/unit/type is inconsistent")
        if self.quote_matched:
            if (self.match_method == "none" or self.locator_bbox is None or self.match_score < 95
                    or self.source_quote is None or self.source_span is None):
                raise ValueError("A matched claim needs source quote/span, locator and high-confidence match")
            if not supported_claim(self.extracted_field.value, self.extracted_value, self.unit, self.quote,
                                   context=self.source_quote):
                raise ValueError("Quote does not support the typed field, unit, value or exception context")
        elif (self.match_method != "none" or self.locator_bbox is not None or self.match_score != 0
              or self.source_quote is not None or self.source_span is not None):
            raise ValueError("Unmatched claim cannot carry a source locator, span, quote or score")
        if self.manually_verified and not self.quote_matched:
            raise ValueError("An unmatched claim cannot be manually verified")
        return self


class BusinessVariable(StrictModel):
    name: EvidenceField
    value: int | float | bool
    unit: Literal["days", "months", "fraction", "share", "USD", "boolean"]
    evidence_id: str = Field(pattern=r"^EV-[0-9]{3}$")
    quote_matched: Literal[True]
    manually_verified: Literal[True]
    source: Literal["synthetic_contract"] = "synthetic_contract"

    @field_validator("name", mode="before")
    @classmethod
    def decode_field(cls, value: object) -> object:
        return parse_evidence_field(value)

    @model_validator(mode="after")
    def check_simulation_unit(self) -> "BusinessVariable":
        f, v = self.name, self.value
        rules = {
            EvidenceField.renewal_notice_days: ("days", int, lambda x: 1 <= x <= 3650),
            EvidenceField.auto_renew: ("boolean", bool, lambda x: x is True),
            EvidenceField.renewal_term_months: ("months", int, lambda x: 1 <= x <= 120),
            EvidenceField.renewal_price_increase_pct: ("fraction", float, lambda x: 0 <= x <= 1),
            EvidenceField.min_purchase_share_A: ("share", float, lambda x: 0 <= x <= 1),
            EvidenceField.termination_fee: ("USD", int, lambda x: 0 <= x <= 1_000_000_000),
        }
        unit, kind, allowed = rules[f]
        if self.unit != unit or type(v) is not kind or not allowed(v) or (type(v) is float and not math.isfinite(v)):
            raise ValueError("Business variable must use the field-specific unit, type and range")
        return self


class AgentOutput(StrictModel):
    role: Literal["CFO", "COO", "Risk"]
    narrative_key: str
    reason_text: str
    option_ids: list[Literal["D0", "D1", "D2"]]
    metric_refs: list[str]
    evidence_ids: list[str]
    status: Literal["MOCK", "LIVE", "UNAVAILABLE"]


class CriticIssue(StrictModel):
    issue_id: str = Field(pattern=r"^CR-[0-9]{3}$")
    category: Literal["omission", "conflict", "compound_risk"]
    explanation: str
    agent_refs: list[Literal["CFO", "COO", "Risk"]]
    evidence_ids: list[str]
    metric_refs: list[str]
    status: Literal["MOCK", "LIVE"]


class DecisionBriefRef(StrictModel):
    recommended_option_id: Literal["D0", "D1", "D2"] | None
    reason_text: str
    metric_refs: list[str]
    critic_issue_ids: list[str]
    status: Literal["MOCK", "LIVE", "UNAVAILABLE"]

    @field_validator("reason_text")
    @classmethod
    def no_free_numbers(cls, value: str) -> str:
        if any(char.isdigit() for char in value):
            raise ValueError("Brief narrative cannot contain free-form numbers; use metric_refs")
        return value

    @model_validator(mode="after")
    def status_is_consistent(self) -> "DecisionBriefRef":
        if self.status == "LIVE" and self.recommended_option_id is None:
            raise ValueError("A live recommendation must identify a selected option")
        if self.status != "LIVE" and self.recommended_option_id is not None:
            raise ValueError("Only a live, simulated selection may recommend an option")
        return self


class EvidenceSummary(StrictModel):
    dataset_id: str
    source_file: str
    records: list[EvidenceRecord]
    business_variables: list[BusinessVariable]
    scenario_assumptions: dict[str, int | float | bool | str]
    status: Literal["MOCK_QUOTE_MATCHED_SYNTHETIC", "LIVE_VERIFIED"]

    @model_validator(mode="after")
    def check_provenance(self) -> "EvidenceSummary":
        by_id = {record.id: record for record in self.records}
        if not self.records or len(by_id) != len(self.records):
            raise ValueError("Evidence IDs must be present and unique")
        if any(record.source_file != self.source_file for record in self.records):
            raise ValueError("Source file mismatch in evidence summary")
        if len({record.source_sha256 for record in self.records}) != 1:
            raise ValueError("Evidence records must share one source hash")
        variable_ids: set[str] = set()
        for variable in self.business_variables:
            record = by_id.get(variable.evidence_id)
            if (record is None or not record.quote_matched or not record.manually_verified
                    or record.extracted_field != variable.name or variable.evidence_id in variable_ids):
                raise ValueError("BusinessVariable needs a distinct matching HUMAN-reviewed EvidenceRecord")
            variable_ids.add(variable.evidence_id)
            if variable.name == EvidenceField.renewal_price_increase_pct:
                consistent = (record.unit == "percent" and variable.unit == "fraction" and
                              abs(float(variable.value) - float(record.extracted_value) / 100) < 1e-12)
            else:
                consistent = (type(record.extracted_value) is type(variable.value) and
                              record.extracted_value == variable.value and record.unit == variable.unit)
            if not consistent:
                raise ValueError("BusinessVariable value/unit differs from its human-approved source")
        if self.status == "LIVE_VERIFIED" and (
            any(not r.quote_matched or not r.manually_verified for r in self.records)
            or variable_ids != set(by_id)
        ):
            raise ValueError("LIVE_VERIFIED requires every record human-reviewed and promoted; text match alone is insufficient")
        return self


class Scenario(StrictModel):
    id: Literal["baseline", "demand-drop", "lead-stress"]
    demand_multiplier: float = Field(gt=0)
    supplier_a_lead_time_multiplier: float = Field(gt=0)
    # External shocks only: no allocation or termination field.


class DecisionOption(StrictModel):
    id: Literal["D0", "D1", "D2"]
    label: str
    allocation_A: float = Field(ge=0, le=1)
    allocation_B: float = Field(ge=0, le=1)
    terminate_A: bool

    @model_validator(mode="after")
    def fixed_meaning(self) -> "DecisionOption":
        expected = {"D0": (1.0, 0.0, False), "D1": (0.6, 0.4, False), "D2": (0.0, 1.0, True)}[self.id]
        if (abs(self.allocation_A - expected[0]) > 1e-9 or abs(self.allocation_B - expected[1]) > 1e-9
                or self.terminate_A is not expected[2]):
            raise ValueError("D0/D1/D2 meanings are fixed by the integration contract")
        return self


class PendingMatrixCell(StrictModel):
    option_id: Literal["D0", "D1", "D2"]
    scenario_id: Literal["baseline", "demand-drop", "lead-stress"]
    status: Literal["AWAITING_SIMULATION"] = "AWAITING_SIMULATION"
    # Never include fabricated KPI values in a Day 1 handoff.


class MockE2EPayload(StrictModel):
    fixture_only: Literal[True] = True
    display_label: Literal["DAY 1 MOCK · NOT A SIMULATION"] = "DAY 1 MOCK · NOT A SIMULATION"
    evidence: EvidenceSummary
    scenarios: list[Scenario]
    options: list[DecisionOption]
    matrix: list[PendingMatrixCell]
    agents: list[AgentOutput]
    critic_issues: list[CriticIssue]
    brief: DecisionBriefRef

    @model_validator(mode="after")
    def check_mock_links(self) -> "MockE2EPayload":
        option_ids = [option.id for option in self.options]
        scenario_ids = [scenario.id for scenario in self.scenarios]
        if sorted(option_ids) != ["D0", "D1", "D2"] or sorted(scenario_ids) != ["baseline", "demand-drop", "lead-stress"]:
            raise ValueError("Mock requires exactly the v4.1 fixed options and scenarios")
        keys = [(c.scenario_id, c.option_id) for c in self.matrix]
        if len(keys) != len(set(keys)) or set(keys) != {(s, o) for s in scenario_ids for o in option_ids}:
            raise ValueError("Pending matrix must cover all nine scenario-option cells exactly once")
        if self.brief.recommended_option_id is not None or self.brief.status != "MOCK":
            raise ValueError("Pending mock cannot recommend or imply no feasible option")
        if sorted(a.role for a in self.agents) != ["CFO", "COO", "Risk"] or any(a.status != "MOCK" for a in self.agents):
            raise ValueError("All three mock agent roles are required")
        if len({i.issue_id for i in self.critic_issues}) != len(self.critic_issues) or any(i.status != "MOCK" for i in self.critic_issues):
            raise ValueError("Critic issue IDs must be unique and MOCK")
        if (len(self.brief.critic_issue_ids) != len(set(self.brief.critic_issue_ids))
                or not set(self.brief.critic_issue_ids) <= {i.issue_id for i in self.critic_issues}):
            raise ValueError("Brief references an unknown Critic issue")
        matched = {r.id for r in self.evidence.records if r.quote_matched}
        refs = [eid for agent in self.agents for eid in agent.evidence_ids]
        refs += [eid for issue in self.critic_issues for eid in issue.evidence_ids]
        if not set(refs) <= matched:
            raise ValueError("Agents/Critic may only cite matched evidence")
        return self
