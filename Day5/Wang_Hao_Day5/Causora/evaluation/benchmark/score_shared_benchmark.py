"""Strict capture validator and scorer for the shared Day 5 benchmark.

This module never imports the Causora simulation engine or the independent oracle.
It validates structure/identity first, then scores answers separately so a
COMPLETED provider response is never conflated with a correct response.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


class CaptureValidationError(ValueError):
    """A capture is malformed, uncorrelated, or unsuitable for scoring."""


_CAPTURE_SCHEMA = "causora.day5-benchmark-capture.v2"
_METHODS = {"plain_llm", "llm_plus_code", "causora"}
_STATUSES = {"COMPLETED", "FAILED", "TIMED_OUT", "CANCELLED"}
_CAPTURE_KEYS = {
    "schema", "method", "status", "runId", "modelId", "startedAtUtc", "finishedAtUtc",
    "commonInputSha256", "promptSha256", "reproducibility", "providerUsage",
    "oracleCaseResults", "notes", "coreSourceSha256",
}
_RESULT_KEYS = {"caseId", "answer", "evidenceRefs", "poisonPillFlags", "codeSummary", "codeArtifactSha256"}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CaptureValidationError(f"{field} must be a non-empty string")
    return value


def _utc_timestamp(value: Any, field: str) -> str:
    text = _text(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureValidationError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise CaptureValidationError(f"{field} must include timezone")
    return text


def _sha256(value: Any, field: str) -> str:
    text = _text(value, field)
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise CaptureValidationError(f"{field} must be a lowercase SHA-256 hex string")
    return text


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise CaptureValidationError(f"{field} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise CaptureValidationError(f"{field} must not contain duplicates")
    return list(value)


def _validate_reproducibility(value: Any, method: str, context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CaptureValidationError("reproducibility must be an object")
    required = {"executionMode", "inputSha256", "auditReference"}
    if method != "causora":
        required.add("promptSha256")
    if method == "llm_plus_code":
        required.update({"codeArtifactSha256", "executionLogSha256"})
    if not required.issubset(value):
        raise CaptureValidationError("reproducibility is missing required fields")
    allowed = required
    if set(value) - allowed:
        raise CaptureValidationError("reproducibility has unknown fields")
    expected_mode = {
        "plain_llm": "plain_llm_no_tools",
        "llm_plus_code": "llm_plus_local_code",
        "causora": "causora_core_control_runner",
    }[method]
    if value["executionMode"] != expected_mode:
        raise CaptureValidationError("reproducibility.executionMode does not match method")
    if _sha256(value["inputSha256"], "reproducibility.inputSha256") != context["sharedInputsSha256"]:
        raise CaptureValidationError("reproducibility input hash does not match the shared controls")
    if method != "causora":
        expected_prompt = context["promptSha256"][method]
        if _sha256(value["promptSha256"], "reproducibility.promptSha256") != expected_prompt:
            raise CaptureValidationError("reproducibility prompt hash does not match the frozen prompt")
    for field in ("codeArtifactSha256", "executionLogSha256"):
        if field in value:
            _sha256(value[field], f"reproducibility.{field}")
    _text(value["auditReference"], "reproducibility.auditReference")
    return value


def _validate_case_results(value: Any, context: dict[str, Any], *, completed: bool) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise CaptureValidationError("oracleCaseResults must be a list")
    expected_ids = context["caseIds"]
    results: list[dict[str, Any]] = []
    seen: list[str] = []
    for row in value:
        if not isinstance(row, dict):
            raise CaptureValidationError("Each oracleCaseResults entry must be an object")
        if set(row) - _RESULT_KEYS:
            raise CaptureValidationError("An oracleCaseResults entry has unknown fields")
        required = {"caseId", "answer", "evidenceRefs", "poisonPillFlags"}
        if not required.issubset(row):
            raise CaptureValidationError("An oracleCaseResults entry is missing required fields")
        case_id = _text(row["caseId"], "oracleCaseResults.caseId")
        if case_id not in expected_ids:
            raise CaptureValidationError(f"Unknown benchmark case ID: {case_id}")
        if not isinstance(row["answer"], dict):
            raise CaptureValidationError(f"Benchmark answer for {case_id} must be an object")
        _string_list(row["evidenceRefs"], f"evidenceRefs for {case_id}")
        _string_list(row["poisonPillFlags"], f"poisonPillFlags for {case_id}")
        if "codeSummary" in row:
            _text(row["codeSummary"], f"codeSummary for {case_id}")
        if "codeArtifactSha256" in row:
            _sha256(row["codeArtifactSha256"], f"codeArtifactSha256 for {case_id}")
        seen.append(case_id)
        results.append(row)
    if len(seen) != len(set(seen)):
        raise CaptureValidationError("Duplicate benchmark case IDs are not allowed")
    if completed and seen != expected_ids:
        missing = sorted(set(expected_ids) - set(seen))
        unexpected = sorted(set(seen) - set(expected_ids))
        raise CaptureValidationError(f"A COMPLETED capture must contain every canonical case once; missing={missing}, unexpected={unexpected}")
    return results


def validate_capture(payload: Any, method: str, context: dict[str, Any]) -> dict[str, Any]:
    """Return a strict, correlated capture or raise before any score is assigned."""
    if method not in _METHODS:
        raise CaptureValidationError(f"Unsupported method: {method}")
    if not isinstance(payload, dict):
        raise CaptureValidationError("Benchmark capture must be an object")
    required = {"schema", "method", "status", "runId", "modelId", "startedAtUtc", "finishedAtUtc", "commonInputSha256", "oracleCaseResults"}
    if not required.issubset(payload):
        raise CaptureValidationError("Benchmark capture is missing required top-level fields")
    if set(payload) - _CAPTURE_KEYS:
        raise CaptureValidationError("Benchmark capture has unknown top-level fields")
    if payload["schema"] != _CAPTURE_SCHEMA:
        raise CaptureValidationError("Benchmark capture schema is not supported")
    if payload["method"] != method:
        raise CaptureValidationError("Benchmark capture method does not match its file")
    if payload["status"] not in _STATUSES:
        raise CaptureValidationError("Benchmark capture has an invalid status")
    _text(payload["runId"], "runId")
    _text(payload["modelId"], "modelId")
    _utc_timestamp(payload["startedAtUtc"], "startedAtUtc")
    _utc_timestamp(payload["finishedAtUtc"], "finishedAtUtc")
    if _sha256(payload["commonInputSha256"], "commonInputSha256") != context["sharedInputsSha256"]:
        raise CaptureValidationError("Capture input hash does not match the frozen shared controls")
    if method != "causora":
        if "promptSha256" not in payload:
            raise CaptureValidationError("External-method capture is missing promptSha256")
        if _sha256(payload["promptSha256"], "promptSha256") != context["promptSha256"][method]:
            raise CaptureValidationError("Capture prompt hash does not match the frozen prompt")
    if payload["status"] == "COMPLETED":
        if "reproducibility" not in payload:
            raise CaptureValidationError("A COMPLETED capture requires reproducibility evidence")
        _validate_reproducibility(payload["reproducibility"], method, context)
    elif "reproducibility" in payload:
        _validate_reproducibility(payload["reproducibility"], method, context)
    if "providerUsage" in payload:
        usage = payload["providerUsage"]
        if not isinstance(usage, dict) or set(usage) - {"inputTokens", "outputTokens", "costUsd"}:
            raise CaptureValidationError("providerUsage has an unsupported shape")
        for name, amount in usage.items():
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
                raise CaptureValidationError(f"providerUsage.{name} must be non-negative number")
    if "coreSourceSha256" in payload:
        if method != "causora" or not isinstance(payload["coreSourceSha256"], dict) or not payload["coreSourceSha256"]:
            raise CaptureValidationError("coreSourceSha256 is reserved for a non-empty Causora source-hash record")
        for source_name, source_hash in payload["coreSourceSha256"].items():
            _text(source_name, "coreSourceSha256 key")
            _sha256(source_hash, f"coreSourceSha256.{source_name}")
    if "notes" in payload:
        _text(payload["notes"], "notes")
    _validate_case_results(payload["oracleCaseResults"], context, completed=payload["status"] == "COMPLETED")
    return payload


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def exact_answer_equal(expected: Any, actual: Any) -> bool:
    """Compare JSON answers while accepting equivalent JSON numeric encodings."""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(expected) == set(actual) and all(exact_answer_equal(expected[key], actual[key]) for key in expected)
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(exact_answer_equal(left, right) for left, right in zip(expected, actual))
    if expected is None:
        return actual is None
    expected_decimal = _decimal(expected)
    actual_decimal = _decimal(actual)
    if expected_decimal is not None and actual_decimal is not None:
        return expected_decimal == actual_decimal
    return type(expected) is type(actual) and expected == actual


def score_completed_capture(capture: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Score a *validated* completed capture against scorer-only expected labels."""
    if capture.get("status") != "COMPLETED":
        raise ValueError("Only COMPLETED captures may be scored")
    by_id = {row["caseId"]: row for row in capture["oracleCaseResults"]}
    labels = context["labels"]["labels"]
    answer_failures: list[str] = []
    evidence_failures: list[str] = []
    poison_failures: list[str] = []
    for label in labels:
        case_id = label["caseId"]
        row = by_id[case_id]
        if not exact_answer_equal(label["answer"], row["answer"]):
            answer_failures.append(case_id)
        if not set(label["requiredEvidenceRefs"]).issubset(row["evidenceRefs"]):
            evidence_failures.append(case_id)
        if not set(label["requiredPoisonPillFlags"]).issubset(row["poisonPillFlags"]):
            poison_failures.append(case_id)
    total = len(labels)
    correct = total - len(answer_failures)
    evidence_covered = total - len(evidence_failures)
    poison_recognized = total - len(poison_failures)
    all_correct = not answer_failures and not evidence_failures and not poison_failures
    return {
        "scoringStatus": "SCORED",
        "completionStatus": "COMPLETED",
        "correctnessStatus": "COMPLETED_AND_FULLY_CORRECT" if all_correct else "COMPLETED_BUT_NOT_FULLY_CORRECT",
        "answerAccuracy": {"correctCaseCount": correct, "totalCaseCount": total, "incorrectCaseIds": answer_failures},
        "evidenceCoverage": {"coveredCaseCount": evidence_covered, "totalCaseCount": total, "missingCoverageCaseIds": evidence_failures},
        "poisonPillRecognition": {"recognizedCaseCount": poison_recognized, "totalCaseCount": total, "missedCaseIds": poison_failures},
        "reproducibilityStatus": "VALIDATED_CAPTURE_IDENTITY",
    }
