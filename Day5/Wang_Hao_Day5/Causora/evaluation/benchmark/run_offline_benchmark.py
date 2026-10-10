#!/usr/bin/env python3
"""Score the shared Day 5 Causora/plain-LLM/LLM+code benchmark without dispatching.

This command never imports an AI client, reads an API key, or sends a network
request. It runs Causora core helpers on shared controls, validates manually
supplied redacted external captures strictly, and scores completion separately
from answer correctness, control-evidence coverage, poison-pill recognition,
and reproducibility identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.benchmark.benchmark_common import ROOT as BENCHMARK_ROOT, benchmark_context, sha256_file
from evaluation.benchmark.causora_control_runner import build_causora_capture
from evaluation.benchmark.score_shared_benchmark import CaptureValidationError, score_completed_capture, validate_capture
from evaluation.oracle.independent_oracle import evaluate_document, selection_control

CONTROL_PATH = ROOT / "evaluation" / "oracle" / "frozen_control_cases.json"
GOLDEN_PATH = ROOT / "verification" / "g4-final" / "verified_golden_e2e.json"
CAPTURE_DIR = ROOT / "evaluation" / "benchmark" / "captured"
SECRET_MARKERS = ("sk-or-v1-", "authorization: bearer", "openrouter_api_key", "api_key=")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def golden_audit(document: dict[str, Any]) -> dict[str, Any]:
    """Keep historic-Golden reconciliation separate from the shared comparison."""
    request = document["simulationRequest"]
    response = document["simulationResponse"]
    data = response["data"]
    simulation = data["simulation"]
    checks: list[str] = []
    audited_cells = 0
    for scenario in request["scenarios"]:
        scenario_id = scenario["id"]
        rows = simulation["matrix"][scenario_id]
        expected_selection = selection_control({
            "riskThreshold": request["riskThreshold"],
            "budgetCeilingUsd": request["budgetCeilingUsd"],
            "options": [{
                "optionId": row["optionId"], "feasible": row["feasible"],
                "stockoutProbability": str(row["stockoutProbability"]),
                "cashOutflowP90": row["cashOutflowP90"], "expectedTco": row["expectedTco"],
            } for row in rows],
        })
        actual_selection = data["selections"][scenario_id]
        if {key: actual_selection[key] for key in ("status", "recommendedOptionId", "constraintViolations")} != expected_selection:
            raise ValueError(f"Golden selection does not reconcile for {scenario_id}")
        checks.append(f"selection:{scenario_id}")
        by_option = {row["optionId"]: row for row in rows}
        for option_id, trace in data["traces"][scenario_id].items():
            cell = by_option[option_id]
            if trace["simulationId"] != simulation["simulationId"] or trace["dataVersion"] != response["dataVersion"]:
                raise ValueError(f"Golden trace identity mismatch for {scenario_id}/{option_id}")
            if trace["expectedTcoUsd"] != cell["expectedTco"]:
                raise ValueError(f"Golden TCO mismatch for {scenario_id}/{option_id}")
            components = {entry["key"]: entry["valueUsd"] for entry in trace["components"]}
            if components != cell["breakdown"] or sum(components.values()) != cell["expectedTco"]:
                raise ValueError(f"Golden component mismatch for {scenario_id}/{option_id}")
            if trace["stockoutProbability"]["value"] != cell["stockoutProbability"]:
                raise ValueError(f"Golden stockout mismatch for {scenario_id}/{option_id}")
            if trace["serviceLevel"]["value"] != cell["serviceLevel"]:
                raise ValueError(f"Golden service mismatch for {scenario_id}/{option_id}")
            if trace["cashOutflowP90"]["valueUsd"] != cell["cashOutflowP90"]:
                raise ValueError(f"Golden P90 mismatch for {scenario_id}/{option_id}")
            audited_cells += 1
            checks.append(f"trace:{scenario_id}/{option_id}")
    return {
        "status": "PASS",
        "classification": "HISTORIC_CAPTURED_GOLDEN_AUDIT_ONLY_NOT_A_SHARED_CASE_SCORE_OR_NEW_SIMULATION",
        "simulationId": simulation["simulationId"],
        "dataVersion": response["dataVersion"],
        "auditedCells": audited_cells,
        "checks": checks,
    }


def _capture_row(method: str, context: dict[str, Any]) -> dict[str, Any]:
    path = CAPTURE_DIR / f"{method}.json"
    if not path.is_file():
        return {
            "method": method,
            "captureStatus": "NOT_RUN_NO_PAID_AUTHORIZATION",
            "captureValidationStatus": "NOT_APPLICABLE",
            "scoringStatus": "NOT_SCORED",
            "capturePath": None,
        }
    raw = path.read_text(encoding="utf-8")
    if any(marker in raw.casefold() for marker in SECRET_MARKERS):
        raise CaptureValidationError(f"Benchmark capture {path.name} contains a prohibited secret marker")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CaptureValidationError(f"Benchmark capture {path.name} is not valid JSON") from exc
    capture = validate_capture(payload, method, context)
    row: dict[str, Any] = {
        "method": method,
        "captureStatus": capture["status"],
        "captureValidationStatus": "VALID",
        "capturePath": str(path.relative_to(ROOT)),
        "runId": capture["runId"],
        "modelId": capture["modelId"],
    }
    if capture["status"] == "COMPLETED":
        row["score"] = score_completed_capture(capture, context)
        row["scoringStatus"] = row["score"]["scoringStatus"]
    else:
        row["scoringStatus"] = "NOT_SCORED_NON_COMPLETED_CAPTURE"
    return row


def _causora_row(context: dict[str, Any]) -> dict[str, Any]:
    capture = validate_capture(build_causora_capture(context), "causora", context)
    return {
        "method": "causora",
        "captureStatus": capture["status"],
        "captureValidationStatus": "VALID",
        "scoringStatus": "SCORED",
        "runId": capture["runId"],
        "modelId": capture["modelId"],
        "coreSourceSha256": capture["coreSourceSha256"],
        "score": score_completed_capture(capture, context),
        "classification": "SHARED_CONTROLS_THROUGH_CAUSORA_CORE_HELPERS_NOT_A_MONTE_CARLO_RUN_OR_GOLDEN_AUDIT",
    }


def _overall_status(rows: list[dict[str, Any]]) -> str:
    if any(row["captureStatus"] == "NOT_RUN_NO_PAID_AUTHORIZATION" for row in rows):
        return "PARTIAL_CAUSORA_SCORED_PENDING_EXPLICIT_PAID_LLM_AUTHORIZATION"
    if any(row["captureStatus"] != "COMPLETED" for row in rows):
        return "INCOMPLETE_EXTERNAL_CAPTURE"
    if any(row.get("score", {}).get("correctnessStatus") != "COMPLETED_AND_FULLY_CORRECT" for row in rows):
        return "COMPLETED_BUT_NOT_ALL_METHODS_FULLY_CORRECT"
    return "COMPLETE_ALL_METHODS_SCORED"


def run() -> dict[str, Any]:
    context = benchmark_context()
    oracle_document = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    oracle_result = evaluate_document(oracle_document)
    if oracle_result["failed"]:
        raise ValueError("Frozen independent oracle controls failed")
    golden_document = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    causora = _causora_row(context)
    plain = _capture_row("plain_llm", context)
    code = _capture_row("llm_plus_code", context)
    rows = [causora, plain, code]
    return {
        "schema": "causora.day5-benchmark-result.v2",
        "networkCallsMade": 0,
        "providerCallsMade": 0,
        "sharedControls": {
            "input": "evaluation/benchmark/shared_control_inputs.json",
            "inputSha256": context["sharedInputsSha256"],
            "caseIds": context["caseIds"],
            "scorerOnlyLabels": "evaluation/benchmark/expected_labels.json",
            "scorerOnlyLabelsSha256": sha256_file(BENCHMARK_ROOT / "evaluation" / "benchmark" / "expected_labels.json"),
            "promptSha256": context["promptSha256"],
        },
        "oracleTechnicalCheck": {"input": str(CONTROL_PATH.relative_to(ROOT)), "sha256": sha256(CONTROL_PATH), **oracle_result},
        "historicGoldenAudit": {"input": str(GOLDEN_PATH.relative_to(ROOT)), "sha256": sha256(GOLDEN_PATH), **golden_audit(golden_document)},
        "causora": causora,
        "plainLlm": plain,
        "llmPlusCode": code,
        "overallStatus": _overall_status(rows),
        "completionRule": "All three methods must have validated COMPLETED captures and COMPLETED_AND_FULLY_CORRECT scores. A capture completion status alone is never correctness evidence.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "verification" / "day5" / "benchmark_shared_score.json")
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "overallStatus": result["overallStatus"],
        "causoraCorrect": result["causora"]["score"]["answerAccuracy"],
        "plainLlmStatus": result["plainLlm"]["captureStatus"],
        "llmPlusCodeStatus": result["llmPlusCode"]["captureStatus"],
        "providerCallsMade": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
