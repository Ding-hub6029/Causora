"""Generate internal, explicitly pending (NO simulation results) Day 1 JSON."""
from __future__ import annotations

import json
from pathlib import Path

from .schemas import (AgentOutput, CriticIssue, DecisionBriefRef, DecisionOption,
                      EvidenceRecord, EvidenceSummary, MockE2EPayload, PendingMatrixCell, Scenario)


def build(summary: EvidenceSummary) -> MockE2EPayload:
    scenarios = [
        Scenario(id="baseline", demand_multiplier=1.0, supplier_a_lead_time_multiplier=1.0),
        Scenario(id="demand-drop", demand_multiplier=0.85, supplier_a_lead_time_multiplier=1.0),
        Scenario(id="lead-stress", demand_multiplier=1.0, supplier_a_lead_time_multiplier=1.3),
    ]
    options = [
        DecisionOption(id="D0", label="Keep A", allocation_A=1.0, allocation_B=0.0, terminate_A=False),
        DecisionOption(id="D1", label="Minimum A + Diversify B", allocation_A=0.6, allocation_B=0.4, terminate_A=False),
        DecisionOption(id="D2", label="Exit A + Move to B", allocation_A=0.0, allocation_B=1.0, terminate_A=True),
    ]
    if summary.source_file == "supplier_a_agreement.pdf":
        risk_ids = ["EV-014", "EV-021", "EV-024", "EV-027"]
        critic_ids = ["EV-021", "EV-024"]
    else:
        risk_ids = ["EV-002", "EV-004", "EV-005", "EV-006"]
        critic_ids = ["EV-004", "EV-005"]
    agents = [
        AgentOutput(role="CFO", narrative_key="cost_review_pending", reason_text="Wait for a computed simulation before ranking costs or cash outcomes.", option_ids=["D0", "D1", "D2"], metric_refs=["expectedTco", "cashOutflowP90"], evidence_ids=[], status="MOCK"),
        AgentOutput(role="COO", narrative_key="service_review_pending", reason_text="Wait for computed service and lead-time outcomes.", option_ids=["D0", "D1", "D2"], metric_refs=["serviceLevel", "stockoutProbability"], evidence_ids=[], status="MOCK"),
        AgentOutput(role="Risk", narrative_key="contract_review_pending", reason_text="Source terms are quote-matched, not human-approved; test the compound downside after simulation.", option_ids=["D0", "D1", "D2"], metric_refs=["cashOutflowP90"], evidence_ids=risk_ids, status="MOCK"),
    ]
    issues = [CriticIssue(issue_id="CR-001", category="compound_risk",
        explanation="Hypothesis only: demand downside plus locked forecast may increase commitment pressure; no calculated impact yet.",
        agent_refs=["CFO", "COO", "Risk"], evidence_ids=critic_ids,
        metric_refs=["cashOutflowP90", "expectedTco"], status="MOCK")]
    brief = DecisionBriefRef(recommended_option_id=None,
        reason_text="Awaiting simulation, feasibility checks, and manual evidence review; no decision is claimed.",
        metric_refs=[], critic_issue_ids=["CR-001"], status="MOCK")
    return MockE2EPayload(evidence=summary, scenarios=scenarios, options=options,
        matrix=[PendingMatrixCell(option_id=o.id, scenario_id=s.id) for s in scenarios for o in options],
        agents=agents, critic_issues=issues, brief=brief)


def _save(path: Path, payload: MockE2EPayload) -> None:
    path.write_text(json.dumps(payload.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    base = Path("demo_data")
    original = EvidenceSummary.model_validate_json((base / "evidence_summary.json").read_text(encoding="utf-8"))
    _save(base / "mock_e2e.json", build(original))
    integrated = base / "integration_v4.1"
    summary = EvidenceSummary.model_validate_json((integrated / "evidence_summary.json").read_text(encoding="utf-8"))
    _save(integrated / "internal_pending_mock.json", build(summary))
    for name, model in (("EvidenceRecord", EvidenceRecord), ("EvidenceSummary", EvidenceSummary),
                        ("AgentOutput", AgentOutput), ("CriticIssue", CriticIssue),
                        ("DecisionBriefRef", DecisionBriefRef), ("MockE2EPayload", MockE2EPayload)):
        (base / (name + ".schema.json")).write_text(json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8")
    print("Wrote two internal pending mocks and six structural JSON Schemas; no KPIs or recommendation")


if __name__ == "__main__":
    main()
