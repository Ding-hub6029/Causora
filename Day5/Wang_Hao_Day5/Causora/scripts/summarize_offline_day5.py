#!/usr/bin/env python3
"""Summarise audited offline controls only; never label them model metrics."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "verification/wang-day5"


def ratio(numerator, denominator, scope):
    return {"numerator": numerator, "denominator": denominator, "value": numerator / denominator if denominator else None,
            "status": "OK_OFFLINE_CONTROLS_ONLY" if denominator else "N/A", "sampleScope": scope}


def main():
    rows = [json.loads(line) for line in (BASE / "ai/final-offline-evaluation/offline-ai-evidence.jsonl").read_text().splitlines()]
    numbers = json.loads((BASE / "ai/numeric-statements.json").read_text())
    supported = json.loads((BASE / "local-http/http-smoke.json").read_text())
    faulty = [row for row in rows if row["label"]["expected"].startswith("rejected")]
    clean = [row for row in rows if row["sampleId"] in ("clean_complete_fixture", "mc_matrix_trace_immutable")]
    tp = sum(row["observed"]["outcome"] == "rejected" for row in faulty)
    fp = sum(row["observed"]["outcome"] == "rejected" for row in clean)
    attempts = [row for row in rows if row["sampleId"] != "no_feasible_zero_calls"]
    success = sum(row["observed"]["outcome"] == "accepted" for row in attempts)
    citations = [row for row in supported["requests"] if row["route"].startswith("/api/evidence/")]
    # The six original lookup quotes are checked. A later availability re-check
    # is not a seventh distinct evidence citation or a support assertion.
    distinct = {row["response"]["data"]["evidence"]["id"]: row for row in citations if row["status"] == 200}
    source_good = sum(row["response"]["data"]["evidence"]["quoteMatched"] is True for row in distinct.values())
    actual = {"scope": "NO_CURRENT_REAL_MODEL_RUNS", "modelCalls": 0,
              "criticDetectionRate": ratio(0, 0, "No authorised new real-model Critic runs"),
              "falsePositiveRate": ratio(0, 0, "No authorised new real-model Critic runs"),
              "numericFidelity": ratio(0, 0, "No inspected new real-model numerical statements"),
              "evidenceValidity": ratio(0, 0, "No inspected new real-model claim-citation entailment"),
              "completeWorkflow": ratio(0, 0, "No attempted new real-model complete runs")}
    result = {"kind": "DAY5_OFFLINE_SUMMARY_NOT_UNSEEN_MODEL_EVALUATION", "realModelMetrics": actual,
              "offlineControlMetrics": {
                  "maliciousOrMalformedPipelineRejection": ratio(tp, len(faulty), "Eight deterministic known cases labeled rejected; local pipeline, NOT Critic model detection."),
                  "cleanFixtureFalseRejection": ratio(fp, len(clean), "Two clean complete-flow fixture controls only, not representative unseen clean sample."),
                  "numericStatementsPassingValidation": ratio(numbers["numericValidationPassCount"], numbers["checkedNumericStatementCount"], "Nineteen author-visible number statements: five valid controls and fourteen intentionally invalid; NOT model fidelity."),
                  "numericExpectedControlOutcomesMet": ratio(numbers["expectedOutcomesMet"], numbers["checkedNumericStatementCount"], "All nineteen deterministic numeric controls; correct invalid rejection counts as correct control outcome."),
                  "sourceQuoteExistenceAndMatch": ratio(source_good, len(distinct), "Six source-backed evidence lookups; proves quote matching, NOT support for arbitrary model conclusions."),
                  "generalEvidenceEntailment": ratio(0, 0, "No independent general natural-language entailment checker or actual model citations inspected."),
                  "fixtureCompleteWorkflow": ratio(success, len(attempts), "Thirteen injected pipeline attempts excluding code-only no-feasible; deliberate failures retained; all five required stages needed."),
              },
              "allOriginalFailuresRetained": True,
              "residualLimitations": ["Targeted English evidence support policy is not universal entailment or multilingual semantic proof.", "Historical dev/heldout sets are not new independently unseen sets.", "No-feasible is correct zero-call outcome, not complete-AI success."]}
    (BASE / "OFFLINE_AND_REAL_METRICS.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result["offlineControlMetrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
