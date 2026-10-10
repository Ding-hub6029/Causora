from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from evaluation.day5.core import (
    ANSWER_SCHEMA,
    EVIDENCE_REGISTRY_SCHEMA,
    EvaluationError,
    canonical_json,
    create_freeze,
    import_external_actual_capture,
    input_record_sha256,
    load_evidence_registry,
    load_inputs,
    pending_metrics,
    score_sealed_actual_capture,
    score_test_harness,
    seal_predictions,
    sha256_file,
    verify_freeze,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "evaluation" / "day5" / "fixtures"


def _json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _copy_fixture_set(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}
    for name in (
        "dev_inputs.jsonl", "dev_labels.jsonl", "evidence_registry.json",
        "fair_prompt.md", "model_config.json", "source_corpus_identity.json",
    ):
        target = root / name
        shutil.copy2(FIXTURES / name, target)
        files[name] = target
    scorer = root / "core_snapshot.py"
    shutil.copy2(ROOT / "evaluation" / "day5" / "core.py", scorer)
    files["scorer"] = scorer
    return files


def _freeze(root: Path) -> tuple[dict, dict[str, Path]]:
    files = _copy_fixture_set(root)
    freeze = root / "freeze.json"
    manifest = create_freeze(
        inputs_path=files["dev_inputs.jsonl"], labels_path=files["dev_labels.jsonl"],
        prompt_path=files["fair_prompt.md"], model_config_path=files["model_config.json"],
        scoring_source_path=files["scorer"], source_corpus_path=files["source_corpus_identity.json"],
        evidence_registry_path=files["evidence_registry.json"], output_path=freeze,
        author="unit-test-author",
    )
    files["freeze"] = freeze
    return manifest, files


def _answer(*, verdict: str, value: str, citation: str, evidence: str = "ev-a", extra_numeric: bool = False,
            extra_citation: bool = False, stages: dict[str, str] | None = None) -> dict:
    numeric = [{
        "statementId": "n-total", "value": value,
        "precision": {"scale": 2, "rounding": "ROUND_HALF_EVEN"},
        "roundingTrapId": "half-even-unit",
    }]
    citations = [{"citationId": citation, "evidenceRef": evidence}]
    if extra_numeric:
        numeric.append({
            "statementId": "unknown-extra-number", "value": "999.00",
            "precision": {"scale": 2, "rounding": "ROUND_HALF_EVEN"},
            "roundingTrapId": "invented-trap",
        })
    if extra_citation:
        citations.append({"citationId": "unknown-extra-claim", "evidenceRef": evidence})
    return {
        "schema": ANSWER_SCHEMA, "criticVerdict": verdict, "criticReasons": ["fixture response"],
        "numericStatements": numeric, "evidenceCitations": citations,
        "stageStatus": stages or {stage: "PASSED" for stage in ("CFO", "COO", "Risk", "Critic", "Brief")},
    }


def _test_prediction(record: dict, *, status: str, answer: dict | None) -> dict:
    return {
        "caseId": record["caseId"], "inputSha256": input_record_sha256(record),
        "status": status, "answer": answer,
        "provenance": {"executionKind": "TEST_FIXTURE_ONLY", "note": "unit test only"},
    }


def _write_test_capture(root: Path, manifest: dict, files: dict[str, Path], *, model_id: str = "NO_PROVIDER_TEST_ONLY",
                        responses: list[dict] | None = None, stage_overrides: list[dict[str, str]] | None = None) -> Path:
    """Create explicitly test-only receipts for validation paths, never performance."""
    freeze_hash = sha256_file(files["freeze"])
    if responses is None:
        responses = [
            {"status": "ok", "answer": _answer(verdict="REJECT", value="10.00", citation="c-a")},
            {"status": "ok", "answer": _answer(verdict="ACCEPT", value="20.00", citation="c-b", evidence="ev-b")},
        ]
    capture_dir = root / "capture"
    provider = {
        "schema": "causora.day5.provider-audit-receipt.v1",
        "externalRunId": "TEST_FIXTURE_ONLY_RUN_001",
        "authorizationReference": "TEST_FIXTURE_ONLY",
        "provider": "TEST_FIXTURE_ONLY",
        "modelId": model_id,
        "providerCallCount": 1,
    }
    provider_path = _json(capture_dir / "provider_audit.json", provider)
    default_stages = {stage: "PASSED" for stage in ("CFO", "COO", "Risk", "Critic", "Brief")}
    stage_rows = [
        {"ordinal": ordinal, "stages": (stage_overrides or [default_stages, default_stages])[ordinal]}
        for ordinal in range(len(responses))
    ]
    stage = {
        "schema": "causora.day5.independent-stage-validation.v1",
        "frozenManifestSha256": freeze_hash,
        "externalRunId": "TEST_FIXTURE_ONLY_RUN_001",
        "orderedResponsesSha256": hashlib.sha256(canonical_json(responses).encode("utf-8")).hexdigest(),
        "validatorId": "TEST_FIXTURE_ONLY_VALIDATOR",
        "validationStatus": "INDEPENDENTLY_VALIDATED",
        "roleStageResults": stage_rows,
    }
    stage_path = _json(capture_dir / "stage_validation.json", stage)
    raw = {
        "schema": "causora.day5.external-actual-capture.v1",
        "method": manifest["method"], "frozenManifestSha256": freeze_hash,
        "execution": {
            "kind": "ACTUAL_CAPTURE", "authorizationReference": "TEST_FIXTURE_ONLY",
            "provider": "TEST_FIXTURE_ONLY", "modelId": model_id,
            "modelConfigSha256": manifest["artifacts"]["modelConfig"]["sha256"],
            "providerCallCount": 1, "externalRunId": "TEST_FIXTURE_ONLY_RUN_001",
            "auditReceipt": {"path": "provider_audit.json", "sha256": sha256_file(provider_path)},
        },
        "responses": responses,
        "stageValidationReceipt": {"path": "stage_validation.json", "sha256": sha256_file(stage_path)},
    }
    return _json(capture_dir / "external_capture.json", raw)


def _harness(files: dict[str, Path], predictions: list[dict]) -> dict:
    return score_test_harness(
        inputs_path=files["dev_inputs.jsonl"], labels_path=files["dev_labels.jsonl"],
        evidence_registry_path=files["evidence_registry.json"], predictions=predictions,
    )


def test_freeze_requires_registry_and_fixture_remains_ineligible(tmp_path: Path) -> None:
    manifest, files = _freeze(tmp_path)
    assert "evidenceRegistry" in manifest["artifacts"]
    assert manifest["officialScoreEligibility"] == "INELIGIBLE_CORPUS_NOT_FRESH_INDEPENDENT_OR_DEBUG_FREE"
    assert manifest["corpusFormalEligibility"] is False
    assert verify_freeze(files["freeze"])["officialScoreEligibility"] == manifest["officialScoreEligibility"]


def test_dispatch_has_inputs_only_and_freeze_input_tamper_fails(tmp_path: Path) -> None:
    manifest, files = _freeze(tmp_path)
    from evaluation.day5.core import build_dispatch_bundle

    bundle = build_dispatch_bundle(freeze_path=files["freeze"], output_path=tmp_path / "dispatch.json")
    assert bundle["method"] == manifest["method"]
    assert bundle["payloads"] and all("caseId" not in payload and "labels" not in payload for payload in bundle["payloads"])
    with files["dev_inputs.jsonl"].open("a", encoding="utf-8") as stream:
        stream.write("\n")
    with pytest.raises(EvaluationError, match="Frozen artifact hash mismatch: inputs"):
        verify_freeze(files["freeze"])


def test_freeze_source_hash_change_fails_closed(tmp_path: Path) -> None:
    _, files = _freeze(tmp_path)
    source = json.loads(files["source_corpus_identity.json"].read_text(encoding="utf-8"))
    source["description"] = "tampered after freeze"
    _json(files["source_corpus_identity.json"], source)
    with pytest.raises(EvaluationError, match="Frozen artifact hash mismatch: sourceCorpus"):
        verify_freeze(files["freeze"])


def test_input_label_leak_and_wrong_json_are_rejected(tmp_path: Path) -> None:
    files = _copy_fixture_set(tmp_path)
    files["dev_inputs.jsonl"].write_text(
        json.dumps({"caseId": "leak", "input": {"nested": {"labels": ["secret"]}}}) + "\n", encoding="utf-8"
    )
    with pytest.raises(EvaluationError, match="Input label leakage"):
        load_inputs(files["dev_inputs.jsonl"])
    malformed = tmp_path / "not-json.json"
    malformed.write_text("{ definitely not JSON", encoding="utf-8")
    with pytest.raises(EvaluationError, match="Invalid JSON"):
        load_evidence_registry(malformed)


def test_registry_requires_labelled_quote_claim_binding(tmp_path: Path) -> None:
    files = _copy_fixture_set(tmp_path)
    registry = {"schema": EVIDENCE_REGISTRY_SCHEMA, "entries": []}
    _json(files["evidence_registry.json"], registry)
    with pytest.raises(EvaluationError, match="lacks labelled source quote"):
        create_freeze(
            inputs_path=files["dev_inputs.jsonl"], labels_path=files["dev_labels.jsonl"],
            prompt_path=files["fair_prompt.md"], model_config_path=files["model_config.json"],
            scoring_source_path=files["scorer"], source_corpus_path=files["source_corpus_identity.json"],
            evidence_registry_path=files["evidence_registry.json"], output_path=tmp_path / "freeze.json", author="unit-test",
        )


def test_model_supported_boolean_is_not_accepted_as_evidence(tmp_path: Path) -> None:
    files = _copy_fixture_set(tmp_path)
    inputs = load_inputs(files["dev_inputs.jsonl"])
    bad = _answer(verdict="REJECT", value="10.00", citation="c-a")
    bad["evidenceCitations"][0]["supported"] = True
    with pytest.raises(EvaluationError, match="evidenceCitations entry has invalid schema"):
        _harness(files, [_test_prediction(inputs[0], status="ok", answer=bad), _test_prediction(inputs[1], status="timeout", answer=None)])


def test_numeric_and_evidence_actual_extras_expand_denominators_and_fail(tmp_path: Path) -> None:
    files = _copy_fixture_set(tmp_path)
    inputs = load_inputs(files["dev_inputs.jsonl"])
    result = _harness(files, [
        _test_prediction(inputs[0], status="ok", answer=_answer(verdict="REJECT", value="10.00", citation="c-a", extra_numeric=True, extra_citation=True)),
        _test_prediction(inputs[1], status="ok", answer=_answer(verdict="ACCEPT", value="20.00", citation="c-b", evidence="ev-b")),
    ])
    assert result["metrics"]["numericFidelity"]["denominator"] == 3
    assert result["metrics"]["numericFidelity"]["numerator"] == 2
    assert result["metrics"]["evidenceSupport"]["denominator"] == 3
    assert result["metrics"]["evidenceSupport"]["numerator"] == 2
    assert any(item["reason"] == "unexpected_model_citation" for item in result["cases"][0]["evidence"])


def test_timeout_logs_are_retained_and_clean_failures_are_separate(tmp_path: Path) -> None:
    files = _copy_fixture_set(tmp_path)
    inputs = load_inputs(files["dev_inputs.jsonl"])
    result = _harness(files, [
        _test_prediction(inputs[0], status="timeout", answer=None),
        _test_prediction(inputs[1], status="timeout", answer=None),
    ])
    assert result["performanceStatus"] == "TEST_HARNESS_NOT_PERFORMANCE"
    assert result["confusion"] == {"TP": 0, "FP": 0, "FN": 1, "TN": 0, "cleanExecutionFailuresExcludedFromFPR": 1}
    assert result["metrics"]["criticDetectionRate"]["denominator"] == 1
    assert result["metrics"]["falsePositiveRate"]["status"] == "NA"
    assert result["metrics"]["numericFidelity"]["denominator"] == 2
    assert [item["actual"]["status"] for item in result["cases"]] == ["timeout", "timeout"]


def test_model_declared_stages_never_make_workflow_success_without_receipt(tmp_path: Path) -> None:
    files = _copy_fixture_set(tmp_path)
    inputs = load_inputs(files["dev_inputs.jsonl"])
    result = _harness(files, [
        _test_prediction(inputs[0], status="ok", answer=_answer(verdict="REJECT", value="10.00", citation="c-a")),
        _test_prediction(inputs[1], status="ok", answer=_answer(verdict="ACCEPT", value="20.00", citation="c-b", evidence="ev-b")),
    ])
    workflow = result["metrics"]["completeWorkflow"]
    assert workflow["status"] == "NA" and workflow["denominator"] == 0
    assert all(case["workflowPassed"] is None for case in result["cases"])
    assert all(case["workflowValidationBasis"] == "NA_NO_INDEPENDENT_STAGE_VALIDATION_RECEIPT" for case in result["cases"])


def test_duplicate_prediction_cannot_replace_canonical_second_case(tmp_path: Path) -> None:
    files = _copy_fixture_set(tmp_path)
    inputs = load_inputs(files["dev_inputs.jsonl"])
    first = _test_prediction(inputs[0], status="ok", answer=_answer(verdict="REJECT", value="10.00", citation="c-a"))
    with pytest.raises(EvaluationError, match="input binding mismatch"):
        _harness(files, [first, first])


def test_external_model_mismatch_is_rejected_before_import(tmp_path: Path) -> None:
    manifest, files = _freeze(tmp_path)
    capture = _write_test_capture(tmp_path, manifest, files, model_id="some-other-model")
    with pytest.raises(EvaluationError, match="modelId differs"):
        import_external_actual_capture(freeze_path=files["freeze"], raw_capture_path=capture, output_path=tmp_path / "predictions.jsonl")


def test_stage_receipt_must_validate_each_required_stage(tmp_path: Path) -> None:
    manifest, files = _freeze(tmp_path)
    incomplete = {"CFO": "PASSED", "COO": "PASSED", "Risk": "PASSED", "Critic": "PASSED"}
    capture = _write_test_capture(tmp_path, manifest, files, stage_overrides=[incomplete, incomplete])
    with pytest.raises(EvaluationError, match="does not validate every required stage"):
        import_external_actual_capture(freeze_path=files["freeze"], raw_capture_path=capture, output_path=tmp_path / "predictions.jsonl")


def test_test_only_receipts_are_portable_and_never_score_performance(tmp_path: Path) -> None:
    work = tmp_path / "work"
    manifest, files = _freeze(work)
    capture = _write_test_capture(work, manifest, files)
    predictions = work / "bound" / "predictions.jsonl"
    rows = import_external_actual_capture(freeze_path=files["freeze"], raw_capture_path=capture, output_path=predictions)
    assert rows[0]["provenance"]["captureAttestation"] == "TEST_FIXTURE_ONLY_VALIDATION_NOT_PERFORMANCE"
    for field in ("rawCapture", "providerAuditReceipt", "stageValidationReceipt"):
        assert not Path(rows[0]["provenance"][field]["path"]).is_absolute()
    portable = tmp_path / "portable-copy"
    shutil.copytree(work, portable)
    copied_freeze = portable / "freeze.json"
    copied_predictions = portable / "bound" / "predictions.jsonl"
    seal = portable / "bound" / "seal.json"
    sealed = seal_predictions(freeze_path=copied_freeze, predictions_path=copied_predictions, output_path=seal)
    assert all(not Path(record["path"]).is_absolute() for record in sealed["actualCaptureEvidence"]["providerAuditReceipts"])
    with pytest.raises(EvaluationError, match="TEST_FIXTURE_ONLY receipt"):
        score_sealed_actual_capture(freeze_path=copied_freeze, predictions_path=copied_predictions, seal_path=seal, output_path=portable / "metrics.json")
    assert not (portable / "metrics.json").exists()


def test_postseal_scorer_rereads_physical_receipt(tmp_path: Path) -> None:
    manifest, files = _freeze(tmp_path)
    capture = _write_test_capture(tmp_path, manifest, files)
    predictions = tmp_path / "bound_predictions.jsonl"
    import_external_actual_capture(freeze_path=files["freeze"], raw_capture_path=capture, output_path=predictions)
    seal = tmp_path / "seal.json"
    seal_predictions(freeze_path=files["freeze"], predictions_path=predictions, output_path=seal)
    provider_path = tmp_path / "capture" / "provider_audit.json"
    receipt = json.loads(provider_path.read_text(encoding="utf-8"))
    receipt["provider"] = "tampered"
    _json(provider_path, receipt)
    with pytest.raises(EvaluationError, match="Frozen artifact hash mismatch: provider audit receipt"):
        score_sealed_actual_capture(freeze_path=files["freeze"], predictions_path=predictions, seal_path=seal, output_path=tmp_path / "metrics.json")


def test_import_preserves_ordered_failure_logs_without_fabricating_answers(tmp_path: Path) -> None:
    manifest, files = _freeze(tmp_path)
    capture = _write_test_capture(tmp_path, manifest, files, responses=[
        {"status": "timeout", "answer": None},
        {"status": "error", "answer": None},
    ])
    rows = import_external_actual_capture(
        freeze_path=files["freeze"], raw_capture_path=capture, output_path=tmp_path / "failure_predictions.jsonl",
    )
    assert [row["status"] for row in rows] == ["timeout", "error"]
    assert [row["answer"] for row in rows] == [None, None]
    assert [row["caseId"] for row in rows] == ["dev-visible-001", "dev-visible-002"]


def test_self_declared_formal_source_and_label_status_do_not_create_official_candidate(tmp_path: Path) -> None:
    files = _copy_fixture_set(tmp_path)
    source = json.loads(files["source_corpus_identity.json"].read_text(encoding="utf-8"))
    source["formalEligibility"] = {
        "freshIndependent": True, "labelsHeldSeparately": True,
        "notUsedForDebug": True, "evaluatorHasNotSeenLabels": True,
    }
    _json(files["source_corpus_identity.json"], source)
    labels = [json.loads(line) for line in files["dev_labels.jsonl"].read_text(encoding="utf-8").splitlines()]
    for label in labels:
        label["labelStatus"] = "INDEPENDENTLY_REVIEWED"
    files["dev_labels.jsonl"].write_text("".join(canonical_json(label) + "\n" for label in labels), encoding="utf-8")
    manifest = create_freeze(
        inputs_path=files["dev_inputs.jsonl"], labels_path=files["dev_labels.jsonl"],
        prompt_path=files["fair_prompt.md"], model_config_path=files["model_config.json"],
        scoring_source_path=files["scorer"], source_corpus_path=files["source_corpus_identity.json"],
        evidence_registry_path=files["evidence_registry.json"], output_path=tmp_path / "freeze.json", author="caller-cannot-sign-approval",
    )
    assert manifest["corpusSelfDeclaredEligibility"] is True
    assert manifest["labelsClaimIndependentlyReviewed"] is True
    assert manifest["corpusFormalEligibility"] is False
    assert manifest["officialScoreEligibility"] == "INELIGIBLE_SELF_DECLARED_REVIEW_NOT_INDEPENDENTLY_VERIFIABLE"


def test_pending_metrics_is_explicit_na_with_zero_denominators() -> None:
    result = pending_metrics()
    assert result["performanceStatus"] == "N_A_NO_AUTHORIZED_ACTUAL_CAPTURE"
    assert all(metric["numerator"] == 0 and metric["denominator"] == 0 and metric["status"] == "NA" for metric in result["metrics"].values())


def test_day4_interface_has_no_agent_day3_scoring_dependency() -> None:
    path = ROOT / "agents" / "wanghao-day3" / "agent_day4" / "eval_interface.py"
    spec = importlib.util.spec_from_file_location("day4_eval_interface_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    record = {"caseId": "opaque", "input": {"fact": "answer-free"}}
    assert module.model_payload(record) == {"fact": "answer-free"}
    with pytest.raises(ValueError, match="answer/label"):
        module.model_payload({"caseId": "opaque", "input": {"labels": ["leak"]}})
