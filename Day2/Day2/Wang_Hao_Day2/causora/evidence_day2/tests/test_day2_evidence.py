from __future__ import annotations

import copy
import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError

from causora_day1.adapter import FRONT_IDS
from causora_day1.evidence import verify_source
from causora_day1.schemas import EvidenceSummary
from evidence_day2.cli import main, verify_bundle
from evidence_day2.handoff_models import JinzhuContractHandoff, validate_promoted_graph
from evidence_day2.pipeline import (ACK, ASSUMPTION_KEYS, FROZEN, frozen_sources, hash_file,
                                     load_json, notice_state, prepare, promote, review_template)
from simulation_day1.wire_models import ContractConstraint, DatasetSuccess, EvidenceSuccess

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def staged():
    return prepare(ROOT)


@pytest.fixture()
def synthetic_review(staged):
    """An IN-MEMORY test double, not an actual participant's attestation."""
    summary, baseline, assumptions, hashes = staged
    review = review_template(summary, baseline, assumptions, hashes)
    review["reviewerName"] = "QA Fixture Reviewer (unit test only)"
    review["reviewedAtUtc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    review["acknowledgement"] = ACK
    for group in ("evidence", "assumptions"):
        for row in review[group]:
            row["decision"] = "approved"
            row["confirmedValue"] = row["expectedValue"]
    return review


def test_ding_frontend_and_jinzhu_manifest_are_immutable(staged):
    summary, baseline, assumptions, hashes = staged
    assert hashes == FROZEN
    assert baseline["meta"]["schemaVersion"] == "causora.contract.v1"
    assert baseline["meta"]["dataVersion"] == "demo-2026.10.04-v4"
    assert summary.dataset_id == "ds-001"
    assert assumptions == {"decisionDate": "2026-10-04", "renewalDate": "2026-11-18",
                           "noticeSent": False, "forecastBasis": "locked-at-renewal",
                           "lockedForecastUnits24m": 26000}
    assert hash_file(ROOT / "public/demo/supplier_a_agreement.pdf") == summary.records[0].source_sha256


def test_real_pdf_quote_page_bbox_and_internal_auto_renew(staged):
    summary, baseline, _, _ = staged
    assert [r.id for r in summary.records] == list(FRONT_IDS) + ["EV-020"]
    assert all(r.page == 4 and r.quote_matched and r.match_method == "exact"
               and r.match_score == 100 and r.locator_bbox for r in summary.records)
    assert all(not r.manually_verified for r in summary.records)
    assert summary.business_variables == [] and len(baseline["evidence"]) == 5
    verify_source(summary, ROOT / "public/demo/supplier_a_agreement.pdf")


def test_review_template_is_all_pending_and_bound_to_pdf_and_notice(staged):
    template = review_template(*staged)
    assert len(template["evidence"]) == 6 and len(template["assumptions"]) == 5
    assert all(item["decision"] == "pending" and item["confirmedValue"] is None
               for group in ("evidence", "assumptions") for item in template[group])
    assert [item["key"] for item in template["assumptions"]] == list(ASSUMPTION_KEYS)
    assert template["sourceHashes"] == FROZEN
    assert template["reviewerName"] == "" and template["reviewedAtUtc"] == ""
    with pytest.raises(ValueError):
        promote(ROOT, template)


def test_transient_review_produces_jinzhu_v1_dataset_and_evidence_schemas(synthetic_review):
    output = promote(ROOT, synthetic_review)
    dataset = output["datasetSuccess"]
    assert output["reviewReceipt"]["simulationState"] == "NOT COMPUTED"
    assert output["reviewReceipt"]["backendState"] == "NOT CONNECTED"
    assert len(output["reviewedEvidenceSummary"]["business_variables"]) == 6
    assert output["reviewedEvidenceSummary"]["status"] == "MOCK_QUOTE_MATCHED_SYNTHETIC"
    EvidenceSummary.model_validate(output["reviewedEvidenceSummary"])
    assert dataset["dataVersion"] == dataset["data"]["dataVersion"]
    assert dataset["dataVersion"].startswith("demo-2026.10.04-v4-wang-day2-reviewed-")
    DatasetSuccess.model_validate_json(json.dumps(dataset, ensure_ascii=False))
    schema = load_json(ROOT / "simulation_day1/schemas/dataset_success_v1.schema.json")
    jsonschema.validate(dataset, schema, format_checker=jsonschema.FormatChecker())
    assert set(output["evidenceSuccessById"]) == set(FRONT_IDS)
    evidence_schema = load_json(ROOT / "simulation_day1/schemas/evidence_success_v1.schema.json")
    for response in output["evidenceSuccessById"].values():
        EvidenceSuccess.model_validate_json(json.dumps(response, ensure_ascii=False))
        jsonschema.validate(response, evidence_schema, format_checker=jsonschema.FormatChecker())
        assert response["data"]["evidence"]["locatorBbox"] is not None


def test_reviewed_fields_feed_contract_and_five_exact_ui_variables(synthetic_review):
    output = promote(ROOT, synthetic_review)
    contract = output["datasetSuccess"]["data"]["contract"]
    ContractConstraint.model_validate_json(json.dumps(contract))
    assert contract["daysToRenewal"] == 45 and contract["renewalNoticeDays"] == 60
    assert contract["noticeDeadline"] == "2026-09-19" and contract["renewalLocked"]
    assert contract["renewalTermMonths"] == 24 and contract["renewalPriceIncreasePct"] == 0.14
    assert contract["minPurchaseShareA"] == 0.6 and contract["minPurchaseUnitsA"] == 15600
    assert contract["terminationFeeUsd"] == 25000 and contract["evidenceIds"] == list(FRONT_IDS)
    variables = output["datasetSuccess"]["data"]["variables"]
    assert [v["key"] for v in variables] == ["renewal_locked", "renewal_term_months", "effective_price_A",
                                          "min_purchase_share_A", "termination_fee"]
    assert [v["source"] for v in variables] == list(FRONT_IDS)
    typed = {v["name"]: v for v in output["jinzhuContractInput"]["businessVariables"]}
    assert typed["renewal_price_increase_pct"]["value"] == 0.14
    assert typed["min_purchase_share_A"]["value"] == 0.6
    assert typed["termination_fee"]["value"] == 25000
    assert "auto_renew" not in typed  # clause presence is not an unconditional simulation input
    internal = {v["name"]: v for v in output["reviewedEvidenceSummary"]["business_variables"]}
    assert internal["auto_renew"]["value"] is True  # conditional clause retained only in ledger


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(reviewerName=""),
    lambda r: r.update(acknowledgement=""),
    lambda r: r.update(reviewedAtUtc="tomorrow"),
    lambda r: r.update(reviewedAtUtc=(datetime.now(timezone.utc) + timedelta(days=3)).isoformat().replace("+00:00", "Z")),
    lambda r: r["evidence"][0].update(decision="pending"),
    lambda r: r["evidence"][0].update(decision="rejected"),
    lambda r: r["evidence"][2].update(confirmedValue="15%"),
    lambda r: r["assumptions"][2].update(confirmedValue=0),  # False must not be int 0
    lambda r: r["assumptions"][2].update(confirmedValue=True),
    lambda r: r["evidence"][4].update(quote="fixed termination fee of $25,000,000"),
    lambda r: r["evidence"][3].update(page=5),
    lambda r: r["evidence"][1].update(id="EV-014"),
    lambda r: r["assumptions"].pop(),
    lambda r: r.update(scopeSha256="0" * 64),
    lambda r: r.update(sourceHashes={}),
    lambda r: r.update(extra="unexpected"),
])
def test_human_review_fail_closed_for_pending_wrong_tampered_or_forged(synthetic_review, mutate):
    bad = copy.deepcopy(synthetic_review)
    mutate(bad)
    with pytest.raises((ValueError, TypeError)):
        promote(ROOT, bad)


@pytest.mark.parametrize("relative,alter", [
    ("public/demo/supplier_a_agreement.pdf", b"PDF swapped under same basename"),
    ("demo_data/causora_day1_mock.json", b"JSON changed without dataVersion"),
    ("public/demo/supplier_correspondence_log.csv", b"notice register changed"),
    ("lib/contracts.ts", b"contract changed without owner review"),
])
def test_modified_frozen_sources_are_rejected_before_quote_promotion(tmp_path, relative, alter):
    for name in FROZEN:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, p)
    (tmp_path / relative).write_bytes(alter)
    with pytest.raises(ValueError, match="Frozen team input changed"):
        frozen_sources(tmp_path)


def test_notice_false_depends_on_explicit_synthetic_register_not_pdf_only(tmp_path):
    target = tmp_path / "public/demo/supplier_correspondence_log.csv"
    target.parent.mkdir(parents=True)
    shutil.copy2(ROOT / "public/demo/supplier_correspondence_log.csv", target)
    from evidence_day2.pipeline import notice_state
    from datetime import date
    assert notice_state(tmp_path, date(2026, 9, 19)) is False
    text = target.read_text(encoding="utf-8")
    target.write_text(text.replace("quarterly_planning_check,false", "valid_written_notice,true"), encoding="utf-8")
    assert notice_state(tmp_path, date(2026, 9, 19)) is True
    with pytest.raises(ValueError):
        target.write_text(text.replace("quarterly_planning_check,false", "quarterly_planning_check,maybe"), encoding="utf-8")
        notice_state(tmp_path, date(2026, 9, 19))


def test_cli_preprocess_refuses_overwrite_and_pending_review_cannot_publish(tmp_path):
    staged = tmp_path / "staged"
    main(["preprocess", "--project-root", str(ROOT), "--out", str(staged)])
    assert (staged / "evidence_pending.json").is_file()
    assert (staged / "review_request.json").is_file()
    assert not (staged / "dataset_success.json").exists()
    with pytest.raises(FileExistsError):
        main(["preprocess", "--project-root", str(ROOT), "--out", str(staged)])
    with pytest.raises(ValueError):
        main(["promote", "--project-root", str(ROOT), "--out", str(tmp_path / "approved"),
              "--review", str(staged / "review_request.json")])
    assert not (tmp_path / "approved").exists()


def test_cli_test_only_review_writes_separate_reviewed_snapshot(synthetic_review, tmp_path):
    review = tmp_path / "review_for_test_only.json"
    review.write_text(json.dumps(synthetic_review, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "approved_for_test_only"
    before = {rel: hash_file(ROOT / rel) for rel in FROZEN}
    main(["promote", "--project-root", str(ROOT), "--out", str(out), "--review", str(review)])
    assert DatasetSuccess.model_validate_json((out / "dataset_success.json").read_text(encoding="utf-8"))
    assert (out / "jinzhu_contract_input.json").is_file()
    assert len(list((out / "evidence_responses").glob("*.json"))) == 5
    assert before == {rel: hash_file(ROOT / rel) for rel in FROZEN}


def test_versioned_internal_handoff_is_strict_and_jinzhu_bound(synthetic_review):
    raw = promote(ROOT, synthetic_review)["jinzhuContractInput"]
    JinzhuContractHandoff.model_validate_json(json.dumps(raw, ensure_ascii=False))
    schema = load_json(ROOT / "evidence_day2/schemas/jinzhu_contract_input.schema.json")
    jsonschema.validate(raw, schema, format_checker=jsonschema.FormatChecker())
    assert raw["handoffVersion"] == "wang.evidence_day2.v1"
    assert raw["status"] == "SELF_ATTESTED_SYNTHETIC_ONLY_NOT_SIMULATED"
    assert len(raw["businessVariables"]) == 5
    for mutation in (
        lambda x: x["businessVariables"].append(x["businessVariables"][0]),
        lambda x: x["businessVariables"][1].update(evidence_id="EV-014"),
        lambda x: x["businessVariables"][2].update(value=0.15),
        lambda x: x["contract"].update(renewalNoticeDays=61),
        lambda x: x.update(handoffVersion="unreviewed-v2"),
        lambda x: x.update(dataVersion="stale-static-mock"),
        lambda x: x["sourceHashes"].update({"public/demo/supplier_a_agreement.pdf": "Z" * 64}),
        lambda x: x.update(unknown=True),
    ):
        bad = copy.deepcopy(raw)
        mutation(bad)
        with pytest.raises((ValueError, ValidationError)):
            JinzhuContractHandoff.model_validate_json(json.dumps(bad, ensure_ascii=False))


@pytest.mark.parametrize("mutation", [
    lambda x: x["data"]["evidence"].pop(),
    lambda x: x["data"]["evidence"][1].update(id="EV-014"),
    lambda x: x["data"]["evidence"][0].update(quote="Invented quote with 60 days"),
    lambda x: x["data"]["variables"][3].update(source="EV-999"),
    lambda x: x["data"]["variables"][2].update(value="Base × 1.15"),
    lambda x: x["data"]["contract"].update(evidenceIds=["EV-014"] * 5),
    lambda x: x["data"].update(dataVersion="stale-static-mock"),
])
def test_dataset_graph_rejects_orphan_duplicate_and_tampered_links(synthetic_review, mutation):
    outputs = promote(ROOT, synthetic_review)
    bad = copy.deepcopy(outputs["datasetSuccess"])
    mutation(bad)
    ledger = EvidenceSummary.model_validate(outputs["reviewedEvidenceSummary"])
    with pytest.raises((ValueError, ValidationError)):
        validate_promoted_graph(bad, ledger)


def test_implementation_and_wire_code_changed_after_review_are_rejected(synthetic_review, monkeypatch):
    from evidence_day2 import pipeline
    originally = pipeline.implementation_hashes
    monkeypatch.setattr(pipeline, "implementation_hashes", lambda: {**originally(), "evidence_day2/pipeline.py": "0" * 64})
    with pytest.raises(ValueError, match="scopeSha256|implementationHashes"):
        promote(ROOT, synthetic_review)


def test_bundle_retains_review_scope_receipt_and_verifies_every_file(synthetic_review, tmp_path):
    review = tmp_path / "only_in_test.json"
    review.write_text(json.dumps(synthetic_review, ensure_ascii=False), encoding="utf-8")
    bundle = tmp_path / "reviewed-test-output"
    main(["promote", "--project-root", str(ROOT), "--out", str(bundle), "--review", str(review)])
    assert (bundle / "approved_review.json").is_file()
    assert (bundle / "review_scope.json").is_file()
    assert (bundle / "bundle_manifest.json").is_file()
    verify_bundle(ROOT, bundle)
    copied = load_json(bundle / "approved_review.json")
    assert copied == synthetic_review
    manifest = load_json(bundle / "bundle_manifest.json")
    assert "approved_review.json" in manifest["filesSha256"]
    assert "dataset_success.json" in manifest["filesSha256"]
    assert "jinzhu_contract_input.json" in manifest["filesSha256"]
    (bundle / "review_receipt.json").write_text('{"tampered": true}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="hash changed"):
        verify_bundle(ROOT, bundle)
