"""v4.1 frontend adapter. Reuses Xiangfeng's numeric LOCAL MOCK, NEVER simulates."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from .evidence import BASELINE_VALUES, verify_source
from .schemas import EvidenceSummary, MockE2EPayload

SCHEMA_VERSION = "causora.contract.v1"
DATA_VERSION = "demo-2026.10.04-v4-wang-evidence-v1"  # changed evidence = new immutable snapshot
FRONT_IDS = ("EV-014", "EV-019", "EV-021", "EV-024", "EV-027")


def front_value(record) -> str:
    f, v = record.extracted_field.value, record.extracted_value
    if f == "renewal_notice_days":
        return f"{v} days"
    if f == "renewal_term_months":
        return f"{v} months"
    if f == "renewal_price_increase_pct":
        return f"{v:g}%"
    if f == "min_purchase_share_A":
        return f"{v * 100:g}%"
    if f == "termination_fee":
        return f"${v:,}"
    raise ValueError(f"{f}: not a v4.1 frontend evidence field")


def adapt(summary: EvidenceSummary, baseline: dict, pdf: Path, pending: MockE2EPayload) -> tuple[dict, dict]:
    if summary.source_file != "supplier_a_agreement.pdf" or summary.dataset_id != "ds-001":
        raise ValueError("This adapter requires the independent v4.1 PDF summary, not Wang's one-page fixture")
    if baseline["meta"]["schemaVersion"] != SCHEMA_VERSION or baseline["meta"]["dataVersion"] != "demo-2026.10.04-v4":
        raise ValueError("Unknown v4.1 baseline version; review contract changes instead of guessing")
    if pending.evidence != summary or pending.brief.recommended_option_id is not None:
        raise ValueError("Pending AI/evidence state cannot become a simulated recommendation")
    verify_source(summary, pdf)
    by_id = {rec.id: rec for rec in summary.records}
    if set(by_id) != set(FRONT_IDS) | {"EV-020"}:
        raise ValueError("Five v4.1 display records and internal auto-renew EV-020 are required")
    if any(not rec.quote_matched or rec.manually_verified for rec in summary.records) or summary.business_variables:
        raise ValueError("Day 1 LOCAL MOCK must not silently promote/unreview records")
    if by_id["EV-020"].extracted_value is not True or by_id["EV-020"].quote != by_id["EV-019"].quote:
        raise ValueError("Auto-renew provenance must remain tied to the genuine v4.1 clause")
    base_by_id = {r["id"]: r for r in baseline["evidence"]}
    output = copy.deepcopy(baseline)
    evidence = []
    for eid in FRONT_IDS:
        rec = by_id[eid]
        expected_field, expected_value = BASELINE_VALUES[eid]
        base = base_by_id[eid]
        if (rec.extracted_field != expected_field or type(rec.extracted_value) is not type(expected_value)
                or rec.extracted_value != expected_value or rec.page != base["page"]
                or rec.quote != base["quote"] or rec.source_file != base["sourceFile"]
                or front_value(rec) != base["extractedValue"]):
            raise ValueError(f"{eid}: typed source or PDF page differs from the v4.1 contract")
        evidence.append({
            "id": eid, "sourceFile": rec.source_file, "page": rec.page, "quote": rec.quote,
            # v4.1 app/page.tsx directly imports JSON as MockData; TS infers
            # number[] rather than the tuple type, so non-null JSON fails build.
            # The exact rect remains in the full hash-bound provenance ledger.
            "locatorBbox": None, "extractedField": rec.extracted_field.value,
            "extractedValue": front_value(rec), "matchMethod": rec.match_method,
            "matchScore": rec.match_score / 100.0, "quoteMatched": rec.quote_matched,
        })
    output["evidence"] = evidence
    output["meta"]["dataVersion"] = DATA_VERSION
    output["simulation"]["dataVersion"] = DATA_VERSION
    output["meta"]["status"] = "LOCAL MOCK · Wang evidence adapter"
    output["meta"]["notice"] = (
        "LOCAL MOCK: simulation metrics, variables and selected Brief are Xiangfeng v4.1 illustrative mock data; "
        "not calculated by Wang or Jinzhu. Wang evidence is PDF quote-matched, NOT human-reviewed. "
        "Wang's pending Brief has no recommendation; this selected D1 is baseline mock copy only."
    )
    # Wang's agent hypotheses are adapted to the correct frontend type without borrowing
    # metric values. All numeric simulation/selected Brief fields still come from Xiangfeng.
    agent_by_role = {a.role: a for a in pending.agents}
    for row in output["boardroom"]:
        row["body"] = agent_by_role[row["role"]].reason_text
        row["headline"] = "LOCAL MOCK: review pending simulation"
        row["status"] = "Watch"
    output["critic"]["severity"] = "LOCAL MOCK hypothesis"
    output["critic"]["headline"] = "Possible compound risk; simulation not yet run by Wang"
    output["critic"]["body"] = pending.critic_issues[0].explanation
    output["critic"]["evidenceIds"] = pending.critic_issues[0].evidence_ids
    # The baseline mock mechanism and selected Brief are kept intact and visibly labelled.
    # Null pending != API no_feasible_option; never cast one into the other.
    output["brief"]["guardrail"] = (
        "LOCAL MOCK selection copied from Xiangfeng v4.1, not Wang/Jinzhu computation or approval. "
        "Pending Wang Brief remains null in internal_pending_mock.json."
    )
    # Freeze this particular Xiangfeng static sample, not the wire contract:
    # a genuinely computed deterministic run may also have zero MC draws.
    if (set(output["simulation"]["matrix"]) != {"baseline", "demand-drop", "lead-stress"}
            or [o["id"] for o in output["options"]] != ["D0", "D1", "D2"]
            or output["simulation"]["monteCarloRuns"] != 0):
        raise ValueError("Baseline simulation is not the fixed three-scenario local mock")
    provenance = {
        "kind": "WANG_DAY1_INTERNAL_PROVENANCE_NOT_FRONTEND_DTO",
        "schemaVersion": SCHEMA_VERSION, "dataVersion": DATA_VERSION,
        "baselineDataVersion": baseline["meta"]["dataVersion"],
        "baselineMockSha256": None,  # populated by CLI from exact baseline file bytes
        "sourceFile": pdf.name, "sourceSha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "bboxCoordinateSystem": "PyMuPDF page points, top-left origin",
        "frontendBboxPolicy": "null in static JSON to preserve v4.1 TS build; actual source rects remain in evidenceRecords. UI opens page 4 but does NOT highlight a region",
        "evidenceRecords": [r.model_dump(mode="json") for r in summary.records],
        "scenarioAssumptions": summary.scenario_assumptions,
        "businessVariablesPromoted": [], "humanSignoff": "PENDING",
        "numericSimulationOrigin": "Xiangfeng v4.1 LOCAL MOCK ONLY",
        "wangPendingRecommendation": None,
        "matchScoreConversion": "frontend matchScore = internal match_score / 100",
        "wireUnits": {"renewalPriceIncreasePct": 0.14, "minPurchaseShareA": 0.6,
                      "demandShock": "whole percent (-15)", "money": "integer USD"},
    }
    return output, provenance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", type=Path, default=Path("demo_data/integration_v4.1"))
    args = parser.parse_args()
    folder = args.base_dir
    pdf = folder / "public/demo/supplier_a_agreement.pdf"
    baseline_file = folder / "causora_day1_mock_baseline.json"
    baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
    summary = EvidenceSummary.model_validate_json((folder / "evidence_summary.json").read_text(encoding="utf-8"))
    pending = MockE2EPayload.model_validate_json((folder / "internal_pending_mock.json").read_text(encoding="utf-8"))
    output, provenance = adapt(summary, baseline, pdf, pending)
    provenance["baselineMockSha256"] = hashlib.sha256(baseline_file.read_bytes()).hexdigest()
    (folder / "frontend_compatible_local_mock.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (folder / "provenance_ledger.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Adapted v4.1 LOCAL MOCK: 5 display records, 1 preserved auto-renew record, 9 copied baseline metric cells; 0 human approvals")


if __name__ == "__main__":
    main()
