"""Offline-only Day5 fair-evaluation primitives.

Nothing in this module imports a provider SDK, reads environment credentials, or
opens the network.  A separately authorised operator may *import* an external
actual capture; fixtures and synthetic responses are intentionally rejected
from the performance path.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

INPUT_SCHEMA = "causora.day5.fair-inputs.v1"
LABEL_SCHEMA = "causora.day5.fair-labels.v1"
FREEZE_SCHEMA = "causora.day5.evaluation-freeze.v1"
RAW_CAPTURE_SCHEMA = "causora.day5.external-actual-capture.v1"
PREDICTION_SCHEMA = "causora.day5.bound-predictions.v1"
SEAL_SCHEMA = "causora.day5.prediction-seal.v1"
METRICS_SCHEMA = "causora.day5.fair-metrics.v1"
ANSWER_SCHEMA = "causora.day5.fair-answer.v1"
EVIDENCE_REGISTRY_SCHEMA = "causora.day5.independent-evidence-registry.v1"
PROVIDER_RECEIPT_SCHEMA = "causora.day5.provider-audit-receipt.v1"
STAGE_RECEIPT_SCHEMA = "causora.day5.independent-stage-validation.v1"

METHODS = {"causora_pipeline", "plain_llm", "llm_plus_code"}
STATUSES = {"ok", "timeout", "error", "cancelled"}
FORBIDDEN_INPUT_KEYS = {
    "label", "labels", "expected", "expectedissues", "correctanswer",
    "severitylabel", "ground_truth", "groundtruth", "answer", "annotations",
    "faulty", "category", "referencereason", "inputsha256",
}


class EvaluationError(ValueError):
    """Raised when an evaluation artifact is malformed, unbound, or tampered."""


def canonical_json(value: Any) -> str:
    """Stable JSON representation used for all identity binding."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvaluationError(f"{field} must be a non-empty string")
    return value


def _sha(value: Any, field: str) -> str:
    if not _is_sha(value):
        raise EvaluationError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _json_object(path: Path | str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvaluationError(f"Invalid JSON: {Path(path).name}") from exc
    if not isinstance(value, dict):
        raise EvaluationError(f"{Path(path).name} must contain a JSON object")
    return value


def _write_new_json(path: Path | str, value: Any) -> Path:
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite evaluation evidence: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def _read_jsonl(path: Path | str) -> list[dict[str, Any]]:
    target = Path(path)
    records: list[dict[str, Any]] = []
    for number, line in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvaluationError(f"Invalid JSONL in {target.name}:{number}") from exc
        if not isinstance(row, dict):
            raise EvaluationError(f"{target.name}:{number} must be an object")
        records.append(row)
    if not records:
        raise EvaluationError(f"{target.name} contains no records")
    return records


def _write_new_jsonl(path: Path | str, rows: Iterable[dict[str, Any]]) -> Path:
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite evaluation evidence: {target}")
    material = list(rows)
    if not material:
        raise EvaluationError("Cannot write an empty prediction artifact")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(canonical_json(row) + "\n" for row in material), encoding="utf-8")
    return target


def _reject_input_labels(value: Any, path: tuple[str | int, ...] = ()) -> None:
    """Reject answer-bearing fields anywhere in an input-side object."""
    if isinstance(value, dict):
        bad = [key for key in value if str(key).lower() in FORBIDDEN_INPUT_KEYS]
        if bad:
            location = ".".join(map(str, path)) or "root"
            raise EvaluationError(f"Input label leakage at {location}: {sorted(bad)}")
        for key, item in value.items():
            _reject_input_labels(item, path + (str(key),))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_input_labels(item, path + (index,))


def case_id(record: dict[str, Any]) -> str:
    return _text(record.get("caseId"), "caseId")


def input_record_sha256(record: dict[str, Any]) -> str:
    """Hash the full input record, including its opaque ID and declared split."""
    return sha256_bytes(canonical_json(record).encode("utf-8"))


def model_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Return the only object permitted to leave the scorer: the answer-free input.

    It deliberately excludes IDs, split names, source metadata, labels, and hashes.
    """
    if not isinstance(record, dict):
        raise EvaluationError("Input record must be an object")
    case_id(record)
    payload = record.get("input")
    if not isinstance(payload, dict) or not payload:
        raise EvaluationError("Input record requires a non-empty object input")
    _reject_input_labels(payload, ("input",))
    return json.loads(canonical_json(payload))


def load_inputs(path: Path | str) -> list[dict[str, Any]]:
    """Load input-only JSONL and reject labels before any dispatch can happen."""
    records = _read_jsonl(path)
    ids: list[str] = []
    for record in records:
        allowed = {"caseId", "split", "source", "input"}
        unknown = set(record) - allowed
        if unknown:
            raise EvaluationError(f"Input record has unsupported keys: {sorted(unknown)}")
        if not {"caseId", "input"}.issubset(record):
            raise EvaluationError("Input record requires caseId and input")
        # Top-level source/split may exist, but label vocabulary cannot.
        _reject_input_labels({key: value for key, value in record.items() if key not in {"caseId", "split", "source"}})
        model_payload(record)
        ids.append(case_id(record))
    if len(ids) != len(set(ids)):
        raise EvaluationError("Duplicate input caseId")
    return records


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise EvaluationError(f"{field} must be a finite decimal-compatible value")
    try:
        answer = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise EvaluationError(f"{field} must be a finite decimal-compatible value") from exc
    if not answer.is_finite():
        raise EvaluationError(f"{field} must be finite")
    return answer


def _validate_expected(expected: Any, ident: str) -> dict[str, Any]:
    if not isinstance(expected, dict):
        raise EvaluationError(f"Label {ident}.expected must be an object")
    required = {"criticShouldReject", "numericStatements", "evidenceCitations", "requiredStages"}
    if set(expected) != required:
        raise EvaluationError(f"Label {ident}.expected must have exactly {sorted(required)}")
    if type(expected["criticShouldReject"]) is not bool:
        raise EvaluationError(f"Label {ident} criticShouldReject must be boolean")
    numeric = expected["numericStatements"]
    evidence = expected["evidenceCitations"]
    stages = expected["requiredStages"]
    if not isinstance(numeric, list) or not isinstance(evidence, list) or not isinstance(stages, list):
        raise EvaluationError(f"Label {ident} expected collections must be lists")
    statement_ids: set[str] = set()
    for item in numeric:
        if not isinstance(item, dict) or set(item) != {"statementId", "value", "precision", "roundingTrapId"}:
            raise EvaluationError(f"Label {ident} numeric statement has invalid schema")
        statement_id = _text(item.get("statementId"), "statementId")
        _decimal(item.get("value"), f"Label {ident}.{statement_id}.value")
        precision = item.get("precision")
        if not isinstance(precision, dict) or set(precision) != {"scale", "rounding"}:
            raise EvaluationError(f"Label {ident}.{statement_id}.precision is invalid")
        if isinstance(precision["scale"], bool) or not isinstance(precision["scale"], int) or precision["scale"] < 0:
            raise EvaluationError(f"Label {ident}.{statement_id}.precision.scale is invalid")
        if precision["rounding"] != "ROUND_HALF_EVEN":
            raise EvaluationError(f"Label {ident}.{statement_id}.precision.rounding must be ROUND_HALF_EVEN")
        _text(item.get("roundingTrapId"), "roundingTrapId")
        if statement_id in statement_ids:
            raise EvaluationError(f"Label {ident} duplicates numeric statementId")
        statement_ids.add(statement_id)
    citation_ids: set[str] = set()
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"citationId", "evidenceRef", "claimId"}:
            raise EvaluationError(f"Label {ident} evidence citation has invalid schema")
        citation_id = _text(item.get("citationId"), "citationId")
        _text(item.get("evidenceRef"), "evidenceRef")
        _text(item.get("claimId"), "claimId")
        if citation_id in citation_ids:
            raise EvaluationError(f"Label {ident} duplicates citationId")
        citation_ids.add(citation_id)
    if not all(isinstance(stage, str) and stage.strip() for stage in stages) or len(stages) != len(set(stages)):
        raise EvaluationError(f"Label {ident} requiredStages must be unique non-empty strings")
    return expected


def load_labels(path: Path | str, inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Load scorer-only labels and bind every row to the exact input record hash."""
    labels = _read_jsonl(path)
    input_by_id = {case_id(row): row for row in inputs}
    ids: list[str] = []
    for row in labels:
        required = {"caseId", "inputSha256", "labelStatus", "expected"}
        if set(row) != required:
            raise EvaluationError(f"Label record has unsupported or missing keys: {sorted(set(row) ^ required)}")
        ident = case_id(row)
        if ident not in input_by_id:
            raise EvaluationError(f"Label contains unknown caseId: {ident}")
        if _sha(row.get("inputSha256"), f"Label {ident}.inputSha256") != input_record_sha256(input_by_id[ident]):
            raise EvaluationError(f"Label input fingerprint mismatch: {ident}")
        _text(row.get("labelStatus"), f"Label {ident}.labelStatus")
        _validate_expected(row.get("expected"), ident)
        ids.append(ident)
    if len(ids) != len(set(ids)):
        raise EvaluationError("Duplicate label caseId")
    if set(ids) != set(input_by_id):
        raise EvaluationError("Labels must cover exactly the frozen input case IDs")
    return labels


def load_evidence_registry(path: Path | str) -> dict[tuple[str, str], dict[str, Any]]:
    """Load source-side support facts, never a model-provided `supported` flag."""
    registry = _json_object(path)
    if set(registry) != {"schema", "entries"} or registry.get("schema") != EVIDENCE_REGISTRY_SCHEMA:
        raise EvaluationError("Evidence registry has unsupported schema")
    entries = registry.get("entries")
    if not isinstance(entries, list):
        raise EvaluationError("Evidence registry entries must be a list")
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        required = {"evidenceRef", "claimId", "quote", "supportStatus"}
        if not isinstance(entry, dict) or set(entry) != required:
            raise EvaluationError("Evidence registry entry has invalid schema")
        evidence_ref = _text(entry["evidenceRef"], "evidence registry evidenceRef")
        claim_id = _text(entry["claimId"], "evidence registry claimId")
        _text(entry["quote"], "evidence registry quote")
        if entry["supportStatus"] not in {"SUPPORTS", "DOES_NOT_SUPPORT"}:
            raise EvaluationError("Evidence registry supportStatus is invalid")
        key = (evidence_ref, claim_id)
        if key in indexed:
            raise EvaluationError("Evidence registry duplicates evidenceRef/claimId")
        indexed[key] = entry
    return indexed


def _formal_corpus_eligible(source: dict[str, Any]) -> bool:
    """Return only the corpus author's *claim* of formal eligibility.

    This is deliberately not an approval decision.  The source-identity file is
    imported evidence and can be written by any caller; an offline evaluator has
    no trusted identity or human-review service with which to authenticate it.
    """
    eligibility = source.get("formalEligibility")
    required = {"freshIndependent", "labelsHeldSeparately", "notUsedForDebug", "evaluatorHasNotSeenLabels"}
    return isinstance(eligibility, dict) and set(eligibility) == required and all(eligibility[key] is True for key in required)


def _json_config(path: Path | str) -> dict[str, Any]:
    config = _json_object(path)
    def reject_credentials(value: Any, trail: tuple[str, ...] = ()) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                lower = key.lower()
                # Deliberately use exact names: maxOutputTokens is a harmless
                # reproducibility parameter, not a credential merely because
                # it contains the word "token".
                if lower in {"api_key", "apikey", "secret", "password", "credential", "credentials", "access_token", "bearer_token", "auth_token"}:
                    raise EvaluationError(f"Model configuration must not contain credentials: {'.'.join(trail + (key,))}")
                reject_credentials(item, trail + (key,))
        elif isinstance(value, list):
            for item in value:
                reject_credentials(item, trail)
    reject_credentials(config)
    required = {"schema", "method", "modelId", "parameters"}
    if set(config) != required or config["schema"] != "causora.day5.model-config.v1":
        raise EvaluationError("Model configuration has unsupported schema")
    if config["method"] not in METHODS:
        raise EvaluationError("Model configuration method is unsupported")
    _text(config["modelId"], "modelId")
    if not isinstance(config["parameters"], dict):
        raise EvaluationError("Model configuration parameters must be an object")
    return config


def _file_record(path: Path | str, *, base_dir: Path) -> dict[str, str]:
    target = Path(path).resolve()
    # Never serialize a sandbox-specific absolute path.  A copied freeze remains
    # valid when its relative artifact layout is copied with it.
    return {"path": os.path.relpath(target, start=base_dir.resolve()), "sha256": sha256_file(target)}


def _resolve_file_record(record: Any, *, base_dir: Path, field: str) -> Path:
    if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
        raise EvaluationError(f"{field} record is invalid")
    relative = Path(_text(record["path"], f"{field}.path"))
    if relative.is_absolute():
        raise EvaluationError(f"{field}.path must be relative to its manifest")
    target = (base_dir.resolve() / relative).resolve()
    if not target.is_file():
        raise EvaluationError(f"Frozen artifact missing: {field}")
    if sha256_file(target) != _sha(record["sha256"], f"{field}.sha256"):
        raise EvaluationError(f"Frozen artifact hash mismatch: {field}")
    return target


def _freeze_paths(freeze_path: Path | str, manifest: dict[str, Any]) -> dict[str, Path]:
    artifacts = manifest.get("artifacts")
    expected = {"inputs", "labels", "prompt", "modelConfig", "scoringSource", "sourceCorpus", "evidenceRegistry"}
    if not isinstance(artifacts, dict) or set(artifacts) != expected:
        raise EvaluationError("Freeze artifact inventory is invalid")
    base = Path(freeze_path).resolve().parent
    return {name: _resolve_file_record(record, base_dir=base, field=name) for name, record in artifacts.items()}


def _validate_evidence_registry_bindings(*, labels: list[dict[str, Any]], registry: dict[tuple[str, str], dict[str, Any]]) -> None:
    """Require every labelled evidence obligation to name an actual registry quote.

    A model emits only a citation ID and evidence reference.  Whether that
    reference supports the separately labelled claim is decided here from the
    frozen source-side registry, never from a model ``supported`` flag.
    """
    for label in labels:
        for citation in label["expected"]["evidenceCitations"]:
            key = (citation["evidenceRef"], citation["claimId"])
            source_fact = registry.get(key)
            if source_fact is None:
                raise EvaluationError(
                    f"Evidence registry lacks labelled source quote for {label['caseId']}.{citation['citationId']}"
                )
            if source_fact["supportStatus"] != "SUPPORTS":
                raise EvaluationError(
                    f"Labelled evidence obligation is not supported by its independent source quote: "
                    f"{label['caseId']}.{citation['citationId']}"
                )


def create_freeze(*, inputs_path: Path | str, labels_path: Path | str, prompt_path: Path | str,
                  model_config_path: Path | str, scoring_source_path: Path | str,
                  source_corpus_path: Path | str, evidence_registry_path: Path | str, output_path: Path | str,
                  author: str, authorization_status: str = "NO_NEW_PROVIDER_AUTHORIZATION") -> dict[str, Any]:
    """Freeze all evaluator inputs without creating an approval or a provider run."""
    inputs_path, labels_path = Path(inputs_path), Path(labels_path)
    inputs = load_inputs(inputs_path)
    labels = load_labels(labels_path, inputs)
    config = _json_config(model_config_path)
    prompt = Path(prompt_path).read_text(encoding="utf-8")
    if not prompt.strip():
        raise EvaluationError("Frozen prompt must not be empty")
    source = _json_object(source_corpus_path)
    if source.get("schema") != "causora.day5.source-corpus-identity.v1":
        raise EvaluationError("Source corpus identity has unsupported schema")
    _text(source.get("corpusStatus"), "source corpus status")
    evidence_registry = load_evidence_registry(evidence_registry_path)
    _validate_evidence_registry_bindings(labels=labels, registry=evidence_registry)
    label_statuses = sorted({row["labelStatus"] for row in labels})
    labels_claim_independently_reviewed = label_statuses == ["INDEPENDENTLY_REVIEWED"]
    corpus_self_declares_eligible = _formal_corpus_eligible(source)
    # Neither a status string inside imported labels/source nor the freeze
    # caller's author string is proof of an independent human review.  This
    # offline module intentionally has no trust anchor with which to elevate an
    # imported declaration into an official candidate.
    if not corpus_self_declares_eligible:
        eligibility = "INELIGIBLE_CORPUS_NOT_FRESH_INDEPENDENT_OR_DEBUG_FREE"
    elif not labels_claim_independently_reviewed:
        eligibility = "INELIGIBLE_LABELS_NOT_INDEPENDENTLY_REVIEWED"
    else:
        eligibility = "INELIGIBLE_SELF_DECLARED_REVIEW_NOT_INDEPENDENTLY_VERIFIABLE"
    output_parent = Path(output_path).resolve().parent
    manifest = {
        "schema": FREEZE_SCHEMA,
        "createdAtUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "author": _text(author, "author"),
        "approval": {
            "status": "AUTHOR_PROGRAM_DRAFT_PENDING_INDEPENDENT_REVIEW",
            "note": "This freeze does not create, replace, or imply a human approval.",
        },
        "executionAuthorization": _text(authorization_status, "authorization status"),
        "method": config["method"],
        "answerSchema": ANSWER_SCHEMA,
        "artifacts": {
            "inputs": _file_record(inputs_path, base_dir=output_parent),
            "labels": _file_record(labels_path, base_dir=output_parent),
            "prompt": _file_record(prompt_path, base_dir=output_parent),
            "modelConfig": _file_record(model_config_path, base_dir=output_parent),
            "scoringSource": _file_record(scoring_source_path, base_dir=output_parent),
            "sourceCorpus": _file_record(source_corpus_path, base_dir=output_parent),
            "evidenceRegistry": _file_record(evidence_registry_path, base_dir=output_parent),
        },
        "inputCount": len(inputs),
        "labelStatus": label_statuses,
        "labelsClaimIndependentlyReviewed": labels_claim_independently_reviewed,
        "corpusSelfDeclaredEligibility": corpus_self_declares_eligible,
        "corpusFormalEligibility": False,
        "officialScoreEligibility": eligibility,
        "officialEligibilityNote": (
            "Imported corpus fields, labelStatus strings, and the freeze author are not human approval. "
            "This offline evaluator has no trusted independent-review record or identity authority; "
            "its output cannot become an official model-performance score."
        ),
        "dispatchRule": "Only artifacts.inputs model_payload values, in canonical order, may be dispatched; labels, caseId, split, source, and hashes are scorer-only.",
        "captureRule": "Only separately authorised external ACTUAL_CAPTURE imports can be sealed and reported as performance; fixture/mock/test data are rejected.",
    }
    _write_new_json(output_path, manifest)
    return manifest


def verify_freeze(path: Path | str) -> dict[str, Any]:
    """Fail closed when any artifact frozen into a manifest has changed."""
    manifest_path = Path(path)
    manifest = _json_object(manifest_path)
    if manifest.get("schema") != FREEZE_SCHEMA:
        raise EvaluationError("Unsupported freeze manifest")
    for field in ("method", "answerSchema", "artifacts", "inputCount", "approval", "executionAuthorization", "labelStatus", "labelsClaimIndependentlyReviewed", "corpusSelfDeclaredEligibility", "corpusFormalEligibility", "officialScoreEligibility", "officialEligibilityNote"):
        if field not in manifest:
            raise EvaluationError(f"Freeze manifest missing {field}")
    if manifest["method"] not in METHODS or manifest["answerSchema"] != ANSWER_SCHEMA:
        raise EvaluationError("Freeze method or answer schema mismatch")
    resolved = _freeze_paths(path, manifest)
    inputs = load_inputs(resolved["inputs"])
    labels = load_labels(resolved["labels"], inputs)
    config = _json_config(resolved["modelConfig"])
    if config["method"] != manifest["method"]:
        raise EvaluationError("Frozen method differs from model configuration")
    source = _json_object(resolved["sourceCorpus"])
    if source.get("schema") != "causora.day5.source-corpus-identity.v1":
        raise EvaluationError("Frozen source corpus identity is invalid")
    if _formal_corpus_eligible(source) is not manifest["corpusSelfDeclaredEligibility"]:
        raise EvaluationError("Frozen corpus self-declared eligibility differs from source identity")
    if manifest["corpusFormalEligibility"] is not False:
        raise EvaluationError("Offline freeze may not self-certify formal corpus eligibility")
    registry = load_evidence_registry(resolved["evidenceRegistry"])
    _validate_evidence_registry_bindings(labels=labels, registry=registry)
    if len(inputs) != manifest["inputCount"] or len(labels) != len(inputs):
        raise EvaluationError("Frozen input/label count mismatch")
    return manifest


def build_dispatch_bundle(*, freeze_path: Path | str, output_path: Path | str) -> dict[str, Any]:
    """Create a model-facing file with input objects only—no IDs, labels, or metadata."""
    manifest = verify_freeze(freeze_path)
    input_path = _freeze_paths(freeze_path, manifest)["inputs"]
    inputs = load_inputs(input_path)
    bundle = {
        "schema": "causora.day5.model-dispatch.v1",
        "method": manifest["method"],
        "answerSchema": ANSWER_SCHEMA,
        "payloads": [model_payload(record) for record in inputs],
        "frozenManifestSha256": sha256_file(freeze_path),
        "rule": "Payload order is canonical. This bundle intentionally contains no labels, case IDs, split names, source metadata, or hashes for individual cases.",
    }
    # Assert the promise made above, including no accidental identifier field.
    for payload in bundle["payloads"]:
        _reject_input_labels(payload)
        if "caseId" in payload or "id" in payload:
            raise EvaluationError("Model payload leaks an identifier")
    _write_new_json(output_path, bundle)
    return bundle


def _validate_answer(answer: Any) -> dict[str, Any]:
    if not isinstance(answer, dict):
        raise EvaluationError("Model answer must be an object")
    expected_keys = {"schema", "criticVerdict", "criticReasons", "numericStatements", "evidenceCitations", "stageStatus"}
    if set(answer) != expected_keys or answer.get("schema") != ANSWER_SCHEMA:
        raise EvaluationError("Model answer does not use the frozen fair-answer schema")
    if answer["criticVerdict"] not in {"REJECT", "ACCEPT"}:
        raise EvaluationError("criticVerdict must be REJECT or ACCEPT")
    if not isinstance(answer["criticReasons"], list) or not all(isinstance(reason, str) and reason for reason in answer["criticReasons"]):
        raise EvaluationError("criticReasons must be string list")
    numeric_ids: set[str] = set()
    for row in answer["numericStatements"]:
        if not isinstance(row, dict) or set(row) != {"statementId", "value", "precision", "roundingTrapId"}:
            raise EvaluationError("numericStatements entry has invalid schema")
        ident = _text(row["statementId"], "numeric statementId")
        _decimal(row["value"], f"numeric {ident}.value")
        if not isinstance(row["precision"], dict) or set(row["precision"]) != {"scale", "rounding"}:
            raise EvaluationError("numeric precision has invalid schema")
        if isinstance(row["precision"]["scale"], bool) or not isinstance(row["precision"]["scale"], int) or row["precision"]["scale"] < 0:
            raise EvaluationError("numeric precision scale is invalid")
        if row["precision"]["rounding"] != "ROUND_HALF_EVEN":
            raise EvaluationError("numeric precision rounding is invalid")
        _text(row["roundingTrapId"], "roundingTrapId")
        if ident in numeric_ids:
            raise EvaluationError("duplicate numeric statementId")
        numeric_ids.add(ident)
    citation_ids: set[str] = set()
    for row in answer["evidenceCitations"]:
        # A model can nominate a citation, but it cannot self-attest that the
        # source supports a claim.  The frozen independent registry decides it.
        if not isinstance(row, dict) or set(row) != {"citationId", "evidenceRef"}:
            raise EvaluationError("evidenceCitations entry has invalid schema")
        ident = _text(row["citationId"], "citationId")
        _text(row["evidenceRef"], "evidenceRef")
        if ident in citation_ids:
            raise EvaluationError("duplicate citationId")
        citation_ids.add(ident)
    if not isinstance(answer["stageStatus"], dict) or not answer["stageStatus"]:
        raise EvaluationError("stageStatus must be a non-empty object")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in answer["stageStatus"].items()):
        raise EvaluationError("stageStatus must map strings to strings")
    return answer


def _receipt_file(record: Any, *, raw_path: Path, field: str) -> Path:
    """Resolve and hash a capture-side receipt relative to the capture file."""
    return _resolve_file_record(record, base_dir=raw_path.resolve().parent, field=field)


def _contains_test_fixture_marker(value: Any) -> bool:
    """Recognise explicit contract-test evidence without guessing from normal text."""
    if isinstance(value, str):
        return "TEST_FIXTURE_ONLY" in value
    if isinstance(value, dict):
        return any(_contains_test_fixture_marker(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_test_fixture_marker(item) for item in value)
    return False


def _capture_attestation(execution: dict[str, Any]) -> str:
    # A readable receipt file and a digest demonstrate local binding only.  They
    # cannot prove that a provider network call occurred.
    if _contains_test_fixture_marker(execution):
        return "TEST_FIXTURE_ONLY_VALIDATION_NOT_PERFORMANCE"
    return "EXTERNAL_CAPTURE_ATTESTED_UNVERIFIED"


def _validate_provider_receipt(path: Path, execution: dict[str, Any]) -> None:
    receipt = _json_object(path)
    required = {"schema", "externalRunId", "authorizationReference", "provider", "modelId", "providerCallCount"}
    if set(receipt) != required or receipt.get("schema") != PROVIDER_RECEIPT_SCHEMA:
        raise EvaluationError("Provider audit receipt has unsupported schema")
    for field in ("externalRunId", "authorizationReference", "provider", "modelId", "providerCallCount"):
        if receipt.get(field) != execution.get(field):
            raise EvaluationError(f"Provider audit receipt does not bind execution.{field}")


def _validate_stage_receipt(path: Path, *, raw: dict[str, Any], freeze_hash: str, count: int,
                            external_run_id: str, required_stages_by_ordinal: list[list[str]]) -> list[dict[str, Any]]:
    receipt = _json_object(path)
    required = {"schema", "frozenManifestSha256", "externalRunId", "orderedResponsesSha256", "validatorId", "validationStatus", "roleStageResults"}
    if set(receipt) != required or receipt.get("schema") != STAGE_RECEIPT_SCHEMA:
        raise EvaluationError("Independent stage-validation receipt has unsupported schema")
    if receipt.get("frozenManifestSha256") != freeze_hash or receipt.get("externalRunId") != external_run_id:
        raise EvaluationError("Stage-validation receipt is bound to another freeze or run")
    response_hash = sha256_bytes(canonical_json(raw["responses"]).encode("utf-8"))
    if _sha(receipt.get("orderedResponsesSha256"), "stage receipt orderedResponsesSha256") != response_hash:
        raise EvaluationError("Stage-validation receipt response fingerprint mismatch")
    _text(receipt.get("validatorId"), "stage receipt validatorId")
    if receipt.get("validationStatus") != "INDEPENDENTLY_VALIDATED":
        raise EvaluationError("Stage-validation receipt must be independently validated")
    rows = receipt.get("roleStageResults")
    if not isinstance(rows, list) or len(rows) != count:
        raise EvaluationError("Stage-validation receipt must cover every ordered response")
    seen: list[int] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"ordinal", "stages"}:
            raise EvaluationError("Stage-validation result has invalid schema")
        ordinal = row.get("ordinal")
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0 or ordinal >= count:
            raise EvaluationError("Stage-validation ordinal is invalid")
        stages = row.get("stages")
        if not isinstance(stages, dict) or not stages or not all(isinstance(k, str) and v in {"PASSED", "FAILED", "NOT_RUN"} for k, v in stages.items()):
            raise EvaluationError("Stage-validation stages are invalid")
        missing = sorted(set(required_stages_by_ordinal[ordinal]) - set(stages))
        if missing:
            raise EvaluationError(f"Stage-validation receipt does not validate every required stage for ordinal {ordinal}: {missing}")
        seen.append(ordinal)
    if seen != list(range(count)):
        raise EvaluationError("Stage-validation results must be canonical ordered and unique")
    return rows


def _validate_raw_capture(raw: Any, manifest: dict[str, Any], freeze_hash: str, count: int, *, raw_path: Path,
                          config: dict[str, Any], required_stages_by_ordinal: list[list[str]]) -> tuple[dict[str, Any], list[dict[str, Any]], Path, Path]:
    if not isinstance(raw, dict):
        raise EvaluationError("External capture must be an object")
    required = {"schema", "method", "frozenManifestSha256", "execution", "responses", "stageValidationReceipt"}
    if set(raw) != required or raw.get("schema") != RAW_CAPTURE_SCHEMA:
        raise EvaluationError("External capture has unsupported schema")
    if raw.get("method") != manifest["method"] or raw.get("frozenManifestSha256") != freeze_hash:
        raise EvaluationError("External capture is bound to a different freeze")
    execution = raw.get("execution")
    execution_fields = {"kind", "authorizationReference", "provider", "modelId", "modelConfigSha256", "providerCallCount", "externalRunId", "auditReceipt"}
    if not isinstance(execution, dict) or set(execution) != execution_fields:
        raise EvaluationError("External capture execution provenance is invalid")
    if execution["kind"] != "ACTUAL_CAPTURE":
        raise EvaluationError("Fixture, mock, test, or unexecuted capture cannot be imported as performance")
    for field in ("authorizationReference", "provider", "modelId", "externalRunId"):
        _text(execution.get(field), f"execution.{field}")
    if isinstance(execution["providerCallCount"], bool) or not isinstance(execution["providerCallCount"], int) or execution["providerCallCount"] < 1:
        raise EvaluationError("Actual capture requires providerCallCount >= 1")
    if execution["modelId"] != config["modelId"]:
        raise EvaluationError("Capture modelId differs from frozen model configuration")
    config_sha = manifest["artifacts"]["modelConfig"]["sha256"]
    if _sha(execution.get("modelConfigSha256"), "execution.modelConfigSha256") != config_sha:
        raise EvaluationError("Capture model configuration hash differs from freeze")
    responses = raw.get("responses")
    if not isinstance(responses, list) or len(responses) != count:
        raise EvaluationError("Actual capture must contain one ordered response per frozen input")
    for response in responses:
        if not isinstance(response, dict) or set(response) != {"status", "answer"}:
            raise EvaluationError("Capture response has invalid schema")
        if response["status"] not in STATUSES:
            raise EvaluationError("Capture response has unknown status")
        if response["status"] == "ok":
            _validate_answer(response["answer"])
        elif response["answer"] is not None:
            raise EvaluationError("Failed or timed-out response must not fabricate an answer")
    provider_receipt = _receipt_file(execution.get("auditReceipt"), raw_path=raw_path, field="provider audit receipt")
    _validate_provider_receipt(provider_receipt, execution)
    stage_receipt = _receipt_file(raw.get("stageValidationReceipt"), raw_path=raw_path, field="stage validation receipt")
    stage_rows = _validate_stage_receipt(
        stage_receipt, raw=raw, freeze_hash=freeze_hash, count=count,
        external_run_id=execution["externalRunId"], required_stages_by_ordinal=required_stages_by_ordinal,
    )
    return raw, stage_rows, provider_receipt, stage_receipt


def import_external_actual_capture(*, freeze_path: Path | str, raw_capture_path: Path | str, output_path: Path | str) -> list[dict[str, Any]]:
    """Bind an externally supplied ordered capture without asserting network reality.

    The returned rows contain portable, relative records for the physical capture
    and receipts.  They are only *attested/unverified* evidence unless an
    external trust authority independently establishes more.
    """
    manifest = verify_freeze(freeze_path)
    freeze_hash = sha256_file(freeze_path)
    paths = _freeze_paths(freeze_path, manifest)
    inputs = load_inputs(paths["inputs"])
    labels = load_labels(paths["labels"], inputs)
    raw_path = Path(raw_capture_path)
    config = _json_config(paths["modelConfig"])
    required_stages = [label["expected"]["requiredStages"] for label in labels]
    raw, stage_rows, provider_receipt, stage_receipt = _validate_raw_capture(
        _json_object(raw_path), manifest, freeze_hash, len(inputs), raw_path=raw_path,
        config=config, required_stages_by_ordinal=required_stages,
    )
    output_base = Path(output_path).resolve().parent
    capture_attestation = _capture_attestation(raw["execution"])
    raw_record = _file_record(raw_path, base_dir=output_base)
    provider_record = _file_record(provider_receipt, base_dir=output_base)
    stage_record = _file_record(stage_receipt, base_dir=output_base)
    rows: list[dict[str, Any]] = []
    for ordinal, (record, response) in enumerate(zip(inputs, raw["responses"])):
        rows.append({
            "schema": PREDICTION_SCHEMA,
            "caseId": case_id(record),
            "inputSha256": input_record_sha256(record),
            "status": response["status"],
            "answer": response["answer"],
            "provenance": {
                "frozenManifestSha256": freeze_hash,
                "rawCapture": raw_record,
                "method": raw["method"],
                "executionKind": raw["execution"]["kind"],
                "captureAttestation": capture_attestation,
                "authorizationReference": raw["execution"]["authorizationReference"],
                "provider": raw["execution"]["provider"],
                "modelId": raw["execution"]["modelId"],
                "modelConfigSha256": raw["execution"]["modelConfigSha256"],
                "providerCallCount": raw["execution"]["providerCallCount"],
                "externalRunId": raw["execution"]["externalRunId"],
                "providerAuditReceipt": provider_record,
                "stageValidationReceipt": stage_record,
                "independentValidatedStages": stage_rows[ordinal]["stages"],
            },
        })
    _write_new_jsonl(output_path, rows)
    return rows


def _same_json(left: Any, right: Any) -> bool:
    return canonical_json(left) == canonical_json(right)


def _load_bound_predictions(*, path: Path | str, manifest: dict[str, Any], freeze_hash: str,
                            inputs: list[dict[str, Any]], labels: list[dict[str, Any]],
                            config: dict[str, Any]) -> list[dict[str, Any]]:
    """Re-read capture and receipt files; provenance hashes alone are not proof."""
    rows = _read_jsonl(path)
    if len(rows) != len(inputs):
        raise EvaluationError("Predictions must cover every frozen input, including failures")
    if len(labels) != len(inputs):
        raise EvaluationError("Prediction validation requires every frozen label")
    expected_ids = [case_id(item) for item in inputs]
    expected_hashes = {case_id(item): input_record_sha256(item) for item in inputs}
    required_stages = [label["expected"]["requiredStages"] for label in labels]
    provenance_fields = {
        "frozenManifestSha256", "rawCapture", "method", "executionKind", "captureAttestation",
        "authorizationReference", "provider", "modelId", "modelConfigSha256", "providerCallCount",
        "externalRunId", "providerAuditReceipt", "stageValidationReceipt", "independentValidatedStages",
    }
    base = Path(path).resolve().parent
    seen: list[str] = []
    raw_cache: dict[Path, tuple[dict[str, Any], list[dict[str, Any]], Path, Path]] = {}
    for ordinal, row in enumerate(rows):
        required = {"schema", "caseId", "inputSha256", "status", "answer", "provenance"}
        if set(row) != required or row.get("schema") != PREDICTION_SCHEMA:
            raise EvaluationError("Bound prediction has invalid schema")
        ident = case_id(row)
        if ident not in expected_hashes or row.get("inputSha256") != expected_hashes[ident]:
            raise EvaluationError("Prediction input fingerprint mismatch")
        if row.get("status") not in STATUSES:
            raise EvaluationError("Prediction has unknown status")
        provenance = row.get("provenance")
        if not isinstance(provenance, dict) or set(provenance) != provenance_fields:
            raise EvaluationError("Prediction provenance is incomplete or has unsupported fields")
        if provenance.get("frozenManifestSha256") != freeze_hash:
            raise EvaluationError("Prediction is not bound to this freeze")
        if provenance.get("executionKind") != "ACTUAL_CAPTURE":
            raise EvaluationError("Unexecuted fixture cannot be scored as performance")
        if provenance.get("method") != manifest["method"]:
            raise EvaluationError("Prediction method differs from freeze")
        raw_path = _resolve_file_record(provenance.get("rawCapture"), base_dir=base, field="prediction raw capture")
        if raw_path not in raw_cache:
            raw_cache[raw_path] = _validate_raw_capture(
                _json_object(raw_path), manifest, freeze_hash, len(inputs), raw_path=raw_path,
                config=config, required_stages_by_ordinal=required_stages,
            )
        raw, stage_rows, provider_path, stage_path = raw_cache[raw_path]
        execution = raw["execution"]
        for field in ("authorizationReference", "provider", "modelId", "modelConfigSha256", "providerCallCount", "externalRunId"):
            if execution[field] != provenance.get(field):
                raise EvaluationError(f"Prediction provenance differs from physical capture: {field}")
        if _capture_attestation(execution) != provenance.get("captureAttestation"):
            raise EvaluationError("Prediction capture attestation differs from physical capture")
        actual_provider_path = _resolve_file_record(provenance.get("providerAuditReceipt"), base_dir=base, field="prediction provider audit receipt")
        actual_stage_path = _resolve_file_record(provenance.get("stageValidationReceipt"), base_dir=base, field="prediction stage validation receipt")
        if actual_provider_path != provider_path or actual_stage_path != stage_path:
            raise EvaluationError("Prediction receipt record does not name the receipt bound by its raw capture")
        response = raw["responses"][ordinal]
        if not _same_json({"status": row["status"], "answer": row["answer"]}, response):
            raise EvaluationError("Prediction response differs from physical raw capture")
        if provenance.get("independentValidatedStages") != stage_rows[ordinal]["stages"]:
            raise EvaluationError("Prediction stage provenance differs from physical stage-validation receipt")
        if row["status"] == "ok":
            _validate_answer(row["answer"])
        elif row["answer"] is not None:
            raise EvaluationError("Failed prediction cannot include a fabricated answer")
        seen.append(ident)
    if seen != expected_ids:
        raise EvaluationError("Predictions must be in canonical input order with no duplicate or missing IDs")
    return rows

def _receipt_records_from_predictions(predictions_path: Path | str, rows: list[dict[str, Any]], *, output_base: Path) -> dict[str, list[dict[str, str]]]:
    """Copy receipt identity into a seal with paths relative to that seal."""
    prediction_base = Path(predictions_path).resolve().parent
    provider_paths: dict[Path, None] = {}
    stage_paths: dict[Path, None] = {}
    for row in rows:
        provenance = row["provenance"]
        provider_paths[_resolve_file_record(provenance["providerAuditReceipt"], base_dir=prediction_base, field="prediction provider audit receipt")] = None
        stage_paths[_resolve_file_record(provenance["stageValidationReceipt"], base_dir=prediction_base, field="prediction stage validation receipt")] = None
    return {
        "providerAuditReceipts": [_file_record(item, base_dir=output_base) for item in sorted(provider_paths)],
        "stageValidationReceipts": [_file_record(item, base_dir=output_base) for item in sorted(stage_paths)],
    }


def seal_predictions(*, freeze_path: Path | str, predictions_path: Path | str, output_path: Path | str) -> dict[str, Any]:
    """Seal a validated import; all receipt locations remain portable relative paths."""
    manifest = verify_freeze(freeze_path)
    freeze_hash = sha256_file(freeze_path)
    frozen_paths = _freeze_paths(freeze_path, manifest)
    inputs = load_inputs(frozen_paths["inputs"])
    labels = load_labels(frozen_paths["labels"], inputs)
    config = _json_config(frozen_paths["modelConfig"])
    rows = _load_bound_predictions(path=predictions_path, manifest=manifest, freeze_hash=freeze_hash, inputs=inputs, labels=labels, config=config)
    records = _receipt_records_from_predictions(predictions_path, rows, output_base=Path(output_path).resolve().parent)
    attestations = sorted({row["provenance"]["captureAttestation"] for row in rows})
    seal = {
        "schema": SEAL_SCHEMA,
        "frozenManifestSha256": freeze_hash,
        "predictions": _file_record(predictions_path, base_dir=Path(output_path).resolve().parent),
        "inputCount": len(rows),
        "method": manifest["method"],
        "actualCaptureEvidence": {"captureAttestations": attestations, **records},
    }
    _write_new_json(output_path, seal)
    return seal


def _validate_seal_receipt_inventory(*, seal: dict[str, Any], seal_path: Path | str,
                                     predictions_path: Path | str, predictions: list[dict[str, Any]]) -> None:
    """Verify seal receipt records against readable files and bound predictions."""
    evidence = seal.get("actualCaptureEvidence")
    required = {"captureAttestations", "providerAuditReceipts", "stageValidationReceipts"}
    if not isinstance(evidence, dict) or set(evidence) != required:
        raise EvaluationError("Prediction seal receipt inventory is invalid")
    if not all(isinstance(value, list) for value in evidence.values()):
        raise EvaluationError("Prediction seal receipt inventory lists are invalid")
    base = Path(seal_path).resolve().parent
    for field in ("providerAuditReceipts", "stageValidationReceipts"):
        for record in evidence[field]:
            _resolve_file_record(record, base_dir=base, field=f"sealed {field}")
    expected = _receipt_records_from_predictions(predictions_path, predictions, output_base=base)
    expected_attestations = sorted({row["provenance"]["captureAttestation"] for row in predictions})
    if evidence["captureAttestations"] != expected_attestations:
        raise EvaluationError("Prediction seal capture attestation inventory differs from predictions")
    for field in ("providerAuditReceipts", "stageValidationReceipts"):
        if not _same_json(evidence[field], expected[field]):
            raise EvaluationError(f"Prediction seal {field} differs from physical prediction provenance")


def _ratio(numerator: int, denominator: int, *, reason_if_na: str) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
        "status": "OK" if denominator else "NA",
        "reason": None if denominator else reason_if_na,
    }


def _answer_index(answer: dict[str, Any], key: str, id_key: str) -> dict[str, dict[str, Any]]:
    return {row[id_key]: row for row in answer.get(key, [])}


def _score_rows(*, inputs: list[dict[str, Any]], labels: list[dict[str, Any]], predictions: list[dict[str, Any]],
                evidence_registry: dict[tuple[str, str], dict[str, Any]], freeze_hash: str,
                manifest: dict[str, Any], performance: bool) -> dict[str, Any]:
    label_by_id = {row["caseId"]: row for row in labels}
    details: list[dict[str, Any]] = []
    tp = fp = fn = tn = clean_failed = 0
    numeric_good = numeric_checked = evidence_good = evidence_checked = workflow_good = workflow_attempts = 0
    for record, prediction in zip(inputs, predictions):
        ident = case_id(record)
        label = label_by_id[ident]
        expected = label["expected"]
        status = prediction["status"]
        expected_reject = expected["criticShouldReject"]
        reasons: list[str] = []
        critic_classification: str
        answer = prediction["answer"]
        if status != "ok":
            if expected_reject:
                fn += 1
                critic_classification = "FN_EXECUTION_FAILURE"
                reasons.append(f"critic execution {status}: expected rejection was not delivered")
            else:
                clean_failed += 1
                critic_classification = "CLEAN_EXECUTION_FAILURE_EXCLUDED_FROM_FPR"
                reasons.append(f"critic execution {status}: no determinate clean verdict")
        else:
            detected = answer["criticVerdict"] == "REJECT"
            if detected and expected_reject:
                tp += 1; critic_classification = "TP"
            elif detected and not expected_reject:
                fp += 1; critic_classification = "FP"
            elif not detected and expected_reject:
                fn += 1; critic_classification = "FN"
            else:
                tn += 1; critic_classification = "TN"
        numeric_actual = _answer_index(answer or {}, "numericStatements", "statementId")
        numeric_expected = {item["statementId"]: item for item in expected["numericStatements"]}
        numeric_results: list[dict[str, Any]] = []
        # The union is intentional: invented model statements are checked and
        # fail rather than silently disappearing from the denominator.
        for statement_id in sorted(set(numeric_expected) | set(numeric_actual)):
            numeric_checked += 1
            item = numeric_expected.get(statement_id)
            actual = numeric_actual.get(statement_id)
            valid = False
            if item is None:
                why = "unexpected_model_statement"
            elif actual is None:
                why = "missing_or_failed_output"
            else:
                valid = (
                    _decimal(actual["value"], "actual value") == _decimal(item["value"], "expected value")
                    and actual["precision"] == item["precision"]
                    and actual["roundingTrapId"] == item["roundingTrapId"]
                )
                why = "validated" if valid else "value_precision_or_rounding_trap_mismatch"
            if valid:
                numeric_good += 1
            numeric_results.append({"statementId": statement_id, "valid": valid, "reason": why})
            if not valid:
                reasons.append(f"numeric {statement_id}: {why}")
        evidence_actual = _answer_index(answer or {}, "evidenceCitations", "citationId")
        evidence_expected = {item["citationId"]: item for item in expected["evidenceCitations"]}
        evidence_results: list[dict[str, Any]] = []
        for citation_id in sorted(set(evidence_expected) | set(evidence_actual)):
            evidence_checked += 1
            item = evidence_expected.get(citation_id)
            actual = evidence_actual.get(citation_id)
            supported = False
            if item is None:
                why = "unexpected_model_citation"
            elif actual is None:
                why = "missing_or_failed_output"
            elif actual["evidenceRef"] != item["evidenceRef"]:
                why = "wrong_evidence_reference"
            else:
                source_fact = evidence_registry.get((item["evidenceRef"], item["claimId"]))
                supported = bool(source_fact and source_fact["supportStatus"] == "SUPPORTS")
                why = "independent_source_supports_claim" if supported else "independent_source_does_not_support_claim"
            if supported:
                evidence_good += 1
            else:
                reasons.append(f"evidence {citation_id}: {why}")
            evidence_results.append({"citationId": citation_id, "supported": supported, "reason": why})
        # A model's own ``stageStatus`` is never evidence of role execution.
        # Without a physical independent stage-validation receipt, workflow is
        # explicitly N/A rather than a synthetic 100% from self-declaration.
        if performance:
            workflow_attempts += 1
            stages = prediction["provenance"]["independentValidatedStages"]
            workflow_passed: bool | None = status == "ok" and all(stages.get(stage) == "PASSED" for stage in expected["requiredStages"])
            workflow_basis = "INDEPENDENT_STAGE_VALIDATION_RECEIPT"
            if workflow_passed:
                workflow_good += 1
            else:
                reasons.append("required workflow stage missing or not PASSED in independent validation receipt")
        else:
            workflow_passed = None
            workflow_basis = "NA_NO_INDEPENDENT_STAGE_VALIDATION_RECEIPT"
            reasons.append("workflow N/A: model-declared stageStatus is not independent proof")
        details.append({
            "caseId": ident,
            "inputSha256": input_record_sha256(record),
            "expected": deepcopy(expected),
            "actual": {"status": status, "answer": deepcopy(answer)},
            "criticClassification": critic_classification,
            "numeric": numeric_results,
            "evidence": evidence_results,
            "workflowPassed": workflow_passed,
            "workflowValidationBasis": workflow_basis,
            "reasons": reasons or ["all checked obligations passed"],
            "provenance": deepcopy(prediction["provenance"]),
        })
    status = "SCORED_EXTERNAL_CAPTURE_UNVERIFIED_NOT_OFFICIAL" if performance else "TEST_HARNESS_NOT_PERFORMANCE"
    return {
        "schema": METRICS_SCHEMA,
        "performanceStatus": status,
        "officialEligible": False if performance else False,
        "officialEligibilityReason": (
            "External capture files are integrity-bound attestations only; this offline evaluator cannot prove a provider network execution or independently authenticate human corpus/label review."
            if performance else "Test harness output is not a model-performance score."
        ),
        "freezeSha256": freeze_hash,
        "method": manifest["method"],
        "sampleScope": {
            "inputCaseCount": len(inputs),
            "predictionCaseCount": len(predictions),
            "allFailuresRetained": True,
            "labelStatus": sorted({row["labelStatus"] for row in labels}),
            "sourceCorpusSha256": manifest["artifacts"]["sourceCorpus"]["sha256"],
            "evidenceRegistrySha256": manifest["artifacts"].get("evidenceRegistry", {}).get("sha256"),
        },
        "metrics": {
            "criticDetectionRate": _ratio(tp, tp + fn, reason_if_na="No expected-rejection cases in the scored sample."),
            "falsePositiveRate": _ratio(fp, fp + tn, reason_if_na="No determinate clean verdicts; clean execution failures are reported separately, not counted as true negatives."),
            "numericFidelity": _ratio(numeric_good, numeric_checked, reason_if_na="No checked numeric statements in the scored sample."),
            "evidenceSupport": _ratio(evidence_good, evidence_checked, reason_if_na="No checked citations in the scored sample."),
            "completeWorkflow": _ratio(workflow_good, workflow_attempts, reason_if_na="No independent stage-validation receipt is available; model-declared stages are not workflow proof."),
        },
        "confusion": {"TP": tp, "FP": fp, "FN": fn, "TN": tn, "cleanExecutionFailuresExcludedFromFPR": clean_failed},
        "cases": details,
    }


def score_sealed_actual_capture(*, freeze_path: Path | str, predictions_path: Path | str, seal_path: Path | str,
                                output_path: Path | str) -> dict[str, Any]:
    """Score a bound external attestation without elevating it to official evidence.

    The scorer re-reads every physical receipt, then emits deterministic per-case
    metrics labelled unverified/non-official.  It cannot prove that a provider
    call or human review happened.  Explicit test fixtures remain unscorable.
    """
    manifest = verify_freeze(freeze_path)
    freeze_hash = sha256_file(freeze_path)
    paths = _freeze_paths(freeze_path, manifest)
    inputs = load_inputs(paths["inputs"])
    labels = load_labels(paths["labels"], inputs)
    evidence_registry = load_evidence_registry(paths["evidenceRegistry"])
    _validate_evidence_registry_bindings(labels=labels, registry=evidence_registry)
    config = _json_config(paths["modelConfig"])
    predictions = _load_bound_predictions(path=predictions_path, manifest=manifest, freeze_hash=freeze_hash, inputs=inputs, labels=labels, config=config)
    seal = _json_object(seal_path)
    if seal.get("schema") != SEAL_SCHEMA or seal.get("frozenManifestSha256") != freeze_hash:
        raise EvaluationError("Prediction seal is not bound to this freeze")
    if seal.get("method") != manifest["method"] or seal.get("inputCount") != len(inputs):
        raise EvaluationError("Prediction seal count or method mismatch")
    seal_prediction = seal.get("predictions")
    sealed_path = _resolve_file_record(seal_prediction, base_dir=Path(seal_path).resolve().parent, field="sealed predictions")
    if sealed_path != Path(predictions_path).resolve():
        raise EvaluationError("Prediction seal references a different output file")
    _validate_seal_receipt_inventory(seal=seal, seal_path=seal_path, predictions_path=predictions_path, predictions=predictions)
    attestations = {row["provenance"]["captureAttestation"] for row in predictions}
    if "TEST_FIXTURE_ONLY_VALIDATION_NOT_PERFORMANCE" in attestations:
        raise EvaluationError("TEST_FIXTURE_ONLY receipt may validate contract handling but can never produce model-performance metrics")
    result = _score_rows(inputs=inputs, labels=labels, predictions=predictions, evidence_registry=evidence_registry, freeze_hash=freeze_hash, manifest=manifest, performance=True)
    result["officialScoreEligibility"] = manifest["officialScoreEligibility"]
    result["captureAttestations"] = sorted(attestations)
    _write_new_json(output_path, result)
    return result


def score_test_harness(*, inputs_path: Path | str, labels_path: Path | str,
                       evidence_registry_path: Path | str, predictions: list[dict[str, Any]]) -> dict[str, Any]:
    """Internal unit-test scorer. It is explicitly and irreversibly non-performance."""
    inputs = load_inputs(inputs_path)
    labels = load_labels(labels_path, inputs)
    evidence_registry = load_evidence_registry(evidence_registry_path)
    _validate_evidence_registry_bindings(labels=labels, registry=evidence_registry)
    if len(predictions) != len(inputs):
        raise EvaluationError("Test predictions must cover every input")
    synthetic_manifest = {
        "method": "causora_pipeline",
        "artifacts": {"sourceCorpus": {"sha256": "0" * 64}, "evidenceRegistry": {"sha256": sha256_file(evidence_registry_path)}},
    }
    for record, row in zip(inputs, predictions):
        if row.get("caseId") != case_id(record) or row.get("inputSha256") != input_record_sha256(record):
            raise EvaluationError("Test prediction input binding mismatch")
        if row.get("status") not in STATUSES:
            raise EvaluationError("Test prediction status invalid")
        if row.get("status") == "ok":
            _validate_answer(row.get("answer"))
        elif row.get("answer") is not None:
            raise EvaluationError("Failed test prediction must not carry an answer")
        row.setdefault("provenance", {"executionKind": "FIXTURE", "note": "unit test only"})
    return _score_rows(inputs=inputs, labels=labels, predictions=predictions, evidence_registry=evidence_registry, freeze_hash="0" * 64, manifest=synthetic_manifest, performance=False)


def pending_metrics(*, reason: str = "Pending new explicit authorization for an external actual capture; no model/provider call was made by this evaluator.") -> dict[str, Any]:
    """Truthful placeholder for a run that has no authorised actual capture."""
    na = lambda why: _ratio(0, 0, reason_if_na=why)
    return {
        "schema": METRICS_SCHEMA,
        "performanceStatus": "N_A_NO_AUTHORIZED_ACTUAL_CAPTURE",
        "reason": reason,
        "sampleScope": {"inputCaseCount": 0, "predictionCaseCount": 0, "allFailuresRetained": True},
        "metrics": {
            "criticDetectionRate": na("No authorised actual capture; denominator is zero."),
            "falsePositiveRate": na("No authorised actual capture; denominator is zero."),
            "numericFidelity": na("No authorised actual capture; denominator is zero."),
            "evidenceSupport": na("No authorised actual capture; denominator is zero."),
            "completeWorkflow": na("No authorised actual capture; denominator is zero."),
        },
        "confusion": {"TP": 0, "FP": 0, "FN": 0, "TN": 0, "cleanExecutionFailuresExcludedFromFPR": 0},
        "cases": [],
    }
