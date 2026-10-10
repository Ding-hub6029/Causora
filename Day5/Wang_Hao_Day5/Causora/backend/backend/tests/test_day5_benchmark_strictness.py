from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[3]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from evaluation.benchmark.benchmark_common import benchmark_context
from evaluation.benchmark.causora_control_runner import build_causora_capture
from evaluation.benchmark.run_offline_benchmark import run as run_benchmark
from evaluation.benchmark.score_shared_benchmark import CaptureValidationError, score_completed_capture, validate_capture


def _external_capture(context: dict) -> dict:
    labels = context["labels"]["labels"]
    rows = [
        {
            "caseId": label["caseId"],
            "answer": copy.deepcopy(label["answer"]),
            "evidenceRefs": list(label["requiredEvidenceRefs"]),
            "poisonPillFlags": list(label["requiredPoisonPillFlags"]),
        }
        for label in labels
    ]
    return {
        "schema": "causora.day5-benchmark-capture.v2",
        "method": "plain_llm",
        "status": "COMPLETED",
        "runId": "test-plain-capture",
        "modelId": "test-model",
        "startedAtUtc": "2026-10-09T00:00:00Z",
        "finishedAtUtc": "2026-10-09T00:00:01Z",
        "commonInputSha256": context["sharedInputsSha256"],
        "promptSha256": context["promptSha256"]["plain_llm"],
        "reproducibility": {
            "executionMode": "plain_llm_no_tools",
            "inputSha256": context["sharedInputsSha256"],
            "promptSha256": context["promptSha256"]["plain_llm"],
            "auditReference": "test-only-redacted-receipt",
        },
        "oracleCaseResults": rows,
    }


def test_completed_capture_rejects_missing_case_results():
    context = benchmark_context()
    capture = _external_capture(context)
    capture["oracleCaseResults"].pop()
    with pytest.raises(CaptureValidationError, match="every canonical case once"):
        validate_capture(capture, "plain_llm", context)


def test_completed_capture_rejects_unknown_case_and_duplicate_case():
    context = benchmark_context()
    capture = _external_capture(context)
    capture["oracleCaseResults"][-1]["caseId"] = "unknown_case"
    with pytest.raises(CaptureValidationError, match="Unknown benchmark case ID"):
        validate_capture(capture, "plain_llm", context)
    capture = _external_capture(context)
    capture["oracleCaseResults"][-1]["caseId"] = capture["oracleCaseResults"][0]["caseId"]
    with pytest.raises(CaptureValidationError, match="Duplicate benchmark case IDs"):
        validate_capture(capture, "plain_llm", context)


def test_completed_capture_is_scored_separately_from_correctness():
    context = benchmark_context()
    capture = _external_capture(context)
    capture["oracleCaseResults"][0]["answer"]["expectedTco"] = 1
    validated = validate_capture(capture, "plain_llm", context)
    score = score_completed_capture(validated, context)
    assert score["completionStatus"] == "COMPLETED"
    assert score["correctnessStatus"] == "COMPLETED_BUT_NOT_FULLY_CORRECT"
    assert score["answerAccuracy"]["incorrectCaseIds"] == ["locked_mixed_cost_rounding"]


def test_causora_runs_and_scores_the_same_six_controls():
    context = benchmark_context()
    capture = validate_capture(build_causora_capture(context), "causora", context)
    score = score_completed_capture(capture, context)
    assert score["correctnessStatus"] == "COMPLETED_AND_FULLY_CORRECT"
    assert score["answerAccuracy"]["correctCaseCount"] == 6
    assert score["evidenceCoverage"]["coveredCaseCount"] == 6
    assert score["poisonPillRecognition"]["recognizedCaseCount"] == 6


def test_offline_result_keeps_historic_golden_out_of_shared_comparison():
    result = run_benchmark()
    assert result["schema"] == "causora.day5-benchmark-result.v2"
    assert result["causora"]["score"]["answerAccuracy"]["correctCaseCount"] == 6
    assert result["historicGoldenAudit"]["classification"].startswith("HISTORIC_CAPTURED_GOLDEN_AUDIT_ONLY")
    assert result["plainLlm"]["captureStatus"] == "NOT_RUN_NO_PAID_AUTHORIZATION"
    assert result["llmPlusCode"]["captureStatus"] == "NOT_RUN_NO_PAID_AUTHORIZATION"


def test_windows_static_preview_checks_current_build_directory_only():
    starter = (PROJECT / "frontend" / "START_PREVIEW.cmd").read_text(encoding="utf-8")
    server = (PROJECT / "frontend" / "scripts" / "serve-static.mjs").read_text(encoding="utf-8")
    assert 'builds\\static\\index.html' in starter
    assert 'out\\index.html' not in starter
    assert 'const root = variant;' in server
    assert 'path.join(frontend, "out")' not in server


def test_dispatch_bundle_script_runs_without_provider_or_expected_labels(tmp_path):
    output = tmp_path / "plain_llm_dispatch.md"
    completed = subprocess.run(
        [sys.executable, str(PROJECT / "evaluation" / "benchmark" / "prepare_dispatch_bundle.py"), "--method", "plain_llm", "--output", str(output)],
        check=True, capture_output=True, text=True,
    )
    assert '"providerCallsMade": 0' in completed.stdout
    material = output.read_text(encoding="utf-8")
    assert "causora.day5-benchmark-shared-inputs.v1" in material
    assert "expected_labels.json" not in material
