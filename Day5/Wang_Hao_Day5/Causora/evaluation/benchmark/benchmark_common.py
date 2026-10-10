"""Shared Day 5 benchmark fixture loading and identity checks.

The model-facing controls and scorer-only labels deliberately live in separate
files. The labels must never be copied into an LLM prompt or a provider capture.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SHARED_INPUTS_PATH = ROOT / "evaluation" / "benchmark" / "shared_control_inputs.json"
EXPECTED_LABELS_PATH = ROOT / "evaluation" / "benchmark" / "expected_labels.json"
PROMPT_PATHS = {
    "plain_llm": ROOT / "evaluation" / "benchmark" / "prompts" / "plain_llm_control_prompt.md",
    "llm_plus_code": ROOT / "evaluation" / "benchmark" / "prompts" / "llm_plus_code_control_prompt.md",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path.name}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return data


def _nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def load_shared_inputs(path: Path = SHARED_INPUTS_PATH) -> dict[str, Any]:
    data = _load_json(path)
    if data.get("schema") != "causora.day5-benchmark-shared-inputs.v1":
        raise ValueError("Unsupported shared benchmark input schema")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Shared benchmark inputs require at least one case")
    ids: list[str] = []
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Each shared benchmark case must be an object")
        case_id = _nonempty_text(case.get("caseId"), "caseId")
        if case.get("kind") not in {"cost", "p90", "selection"}:
            raise ValueError(f"Unsupported shared benchmark case kind for {case_id}")
        if not isinstance(case.get("input"), dict):
            raise ValueError(f"Shared benchmark case {case_id} needs object input")
        if case.get("evidenceRef") != f"control:{case_id}":
            raise ValueError(f"Shared benchmark case {case_id} has an invalid control evidence reference")
        ids.append(case_id)
    if len(ids) != len(set(ids)):
        raise ValueError("Shared benchmark case IDs must be unique")
    return data


def load_expected_labels(shared_sha256: str, path: Path = EXPECTED_LABELS_PATH) -> dict[str, Any]:
    data = _load_json(path)
    if data.get("schema") != "causora.day5-benchmark-expected-labels.v1":
        raise ValueError("Unsupported benchmark expected-label schema")
    if data.get("sharedInputsSha256") != shared_sha256:
        raise ValueError("Expected labels do not bind to the current shared benchmark inputs")
    labels = data.get("labels")
    if not isinstance(labels, list) or not labels:
        raise ValueError("Expected benchmark labels require at least one label")
    ids: list[str] = []
    for label in labels:
        if not isinstance(label, dict):
            raise ValueError("Each expected benchmark label must be an object")
        case_id = _nonempty_text(label.get("caseId"), "label.caseId")
        if not isinstance(label.get("answer"), dict):
            raise ValueError(f"Expected label {case_id} needs an object answer")
        for key in ("requiredEvidenceRefs", "requiredPoisonPillFlags"):
            values = label.get(key)
            if not isinstance(values, list) or not all(isinstance(item, str) and item for item in values):
                raise ValueError(f"Expected label {case_id} has invalid {key}")
            if len(values) != len(set(values)):
                raise ValueError(f"Expected label {case_id} duplicates {key}")
        ids.append(case_id)
    if len(ids) != len(set(ids)):
        raise ValueError("Expected benchmark label case IDs must be unique")
    return data


def benchmark_context() -> dict[str, Any]:
    shared = load_shared_inputs()
    shared_sha = sha256_file(SHARED_INPUTS_PATH)
    labels = load_expected_labels(shared_sha)
    shared_ids = [case["caseId"] for case in shared["cases"]]
    label_ids = [label["caseId"] for label in labels["labels"]]
    if shared_ids != label_ids:
        raise ValueError("Shared benchmark case IDs and expected labels must have the same canonical order")
    return {
        "shared": shared,
        "labels": labels,
        "sharedInputsSha256": shared_sha,
        "promptSha256": {method: sha256_file(path) for method, path in PROMPT_PATHS.items()},
        "caseIds": shared_ids,
    }
