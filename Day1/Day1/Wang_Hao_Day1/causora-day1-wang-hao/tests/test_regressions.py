from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pymupdf
import pytest
from pydantic import ValidationError
from reportlab.pdfgen import canvas

from causora_day1.adapter import DATA_VERSION, FRONT_IDS, adapt
from causora_day1.claim_checks import PATTERNS, supported_claim
from causora_day1.evidence import extract, extract_baseline, locate, verify_source
from causora_day1.make_mock import build
from causora_day1.provider_smoke import _check, run, valid_structured_reply
from causora_day1.schemas import (BusinessVariable, DecisionOption, EvidenceField, EvidenceRecord,
                                 EvidenceSummary, MockE2EPayload)

ROOT = Path(__file__).resolve().parents[1]
PDF_OLD = ROOT / "demo_data/supplier_a_poison_pill.pdf"
BASE = ROOT / "demo_data/integration_v4.1"
PDF_NEW = BASE / "public/demo/supplier_a_agreement.pdf"
BASE_JSON = BASE / "causora_day1_mock_baseline.json"


@pytest.fixture(scope="module")
def integrated():
    summary = extract_baseline(PDF_NEW, BASE_JSON)
    base = json.loads(BASE_JSON.read_text(encoding="utf-8"))
    pending = build(summary)
    return summary, base, pending


def test_all_package_text_io_explicitly_uses_utf8():
    # Prevent Windows cp936/cp1252 defaults from silently breaking JSON fixtures.
    for folder in (ROOT / "src", ROOT / "tests"):
        for path in folder.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr in {"read_text", "write_text"}):
                    encoding = next((kw.value for kw in node.keywords if kw.arg == "encoding"), None)
                    assert isinstance(encoding, ast.Constant) and encoding.value == "utf-8", (
                        f"{path}: {node.func.attr} must declare encoding='utf-8'"
                    )


@pytest.mark.parametrize("field,value,unit,quote", [
    ("renewal_notice_days", 90, "days", "at least 60 days before renewal"),
    ("renewal_notice_days", 60, "USD", "at least 60 days before renewal"),
    ("renewal_term_months", 24.0, "months", "automatically renews for 24 months"),
    ("renewal_price_increase_pct", 14, "USD", "at a 14% higher unit price"),
    ("renewal_price_increase_pct", 14, "percent", "at a 15% higher unit price"),
    ("min_purchase_share_A", 0.6, "share", "minimum purchase commitment equal to 50% of forecast demand"),
    ("termination_fee", 25000, "USD", "fixed termination fee of $25,000,000"),
    ("termination_fee", 25000, "USD", "fixed termination fee of $25,000.50"),
])
def test_semantic_number_unit_type_rejections(field, value, unit, quote):
    assert not supported_claim(field, value, unit, quote)


def test_model_rejects_wrong_typed_value_even_with_valid_bbox():
    record = extract(PDF_OLD).records[0].model_dump()
    record["extracted_value"] = 90  # quote still says 60
    with pytest.raises(ValidationError):
        EvidenceRecord.model_validate(record)
    record["extracted_value"] = 60
    record["unit"] = "USD"
    with pytest.raises(ValidationError):
        EvidenceRecord.model_validate(record)


@pytest.mark.parametrize("field,value,unit,quote", [
    ("renewal_price_increase_pct", 14, "percent", "The price will not be at a 14% higher unit price."),
    ("renewal_price_increase_pct", 14, "percent", "at a 14% higher unit price. The uplift is waived."),
    ("min_purchase_share_A", 0.6, "share", "There is no minimum purchase commitment equal to 60% of forecast demand."),
    ("min_purchase_share_A", 0.6, "share", "minimum purchase commitment equal to 60% of forecast demand. The minimum purchase commitment does not apply."),
    ("renewal_term_months", 24, "months", "The agreement automatically renews for 24 months. The renewal clause does not apply to the current customer."),
    ("termination_fee", 25000, "USD", "fixed termination fee of $25,000. This fee is waived."),
    ("renewal_term_months", 24, "months", "The agreement automatically renews for 24 months unless the parties agree otherwise."),
    ("min_purchase_share_A", 0.6, "share", "The renewed term has a minimum purchase commitment equal to 60% of forecast demand, except where waived in writing."),
])
def test_negative_and_exception_context_rejected(field, value, unit, quote):
    assert not supported_claim(field, value, unit, quote)


def test_fuzzy_cannot_accept_fabricated_waiver_suffix():
    with pymupdf.open(PDF_OLD) as doc:
        quote = "fixed termination fee of $25,000. This fee is waived."
        method, score, bbox = locate(doc[0], quote, EvidenceField.termination_fee, 25000,
                                     PATTERNS["termination_fee"].pattern)
    assert (method, score, bbox) == ("none", 0.0, None)


def test_source_side_waiver_prevents_positive_match(tmp_path):
    pdf = tmp_path / "waiver.pdf"
    c = canvas.Canvas(str(pdf))
    c.drawString(50, 750, "Early exit incurs a fixed termination fee of $25,000.")
    c.drawString(50, 730, "This fee is waived.")
    c.save()
    summary = extract(pdf)
    assert not next(r for r in summary.records if r.extracted_field == EvidenceField.termination_fee).quote_matched


@pytest.mark.parametrize("clause,field", [
    ("The agreement automatically renews for 24 months unless the parties agree otherwise.", EvidenceField.renewal_term_months),
    ("The renewed term has a minimum purchase commitment equal to 60% of forecast demand, except where waived in writing.", EvidenceField.min_purchase_share_A),
])
def test_unresolved_source_qualifier_requires_review(tmp_path, clause, field):
    pdf = tmp_path / "conditional.pdf"
    c = canvas.Canvas(str(pdf))
    c.drawString(50, 750, clause)
    c.save()
    summary = extract(pdf)
    assert not next(r for r in summary.records if r.extracted_field == field).quote_matched


@pytest.mark.parametrize("bad", [[3, 3, 1, 4], [1, 5, 4, 5], [0, 0, float('nan'), 4],
                                  [0, 0, float('inf'), 4], [True, 1, 3, 4]])
def test_locator_rejects_bad_rectangles(bad):
    record = extract(PDF_OLD).records[0].model_dump()
    record["locator_bbox"] = bad
    with pytest.raises(ValidationError):
        EvidenceRecord.model_validate(record)


def test_page_number_and_bbox_checked_against_real_pdf():
    summary = extract(PDF_OLD).model_copy(deep=True)
    summary.records[0].page = 2
    with pytest.raises(ValueError, match="page mismatch"):
        verify_source(summary, PDF_OLD)
    summary = extract(PDF_OLD).model_copy(deep=True)
    summary.records[0].locator_bbox = [500.0, 100.0, 900.0, 120.0]
    with pytest.raises(ValueError, match="bbox outside"):
        verify_source(summary, PDF_OLD)


def test_live_verified_requires_real_per_record_approval():
    summary = extract(PDF_OLD).model_dump()
    summary["status"] = "LIVE_VERIFIED"
    with pytest.raises(ValidationError):
        EvidenceSummary.model_validate(summary)
    summary["records"][0]["manually_verified"] = True
    with pytest.raises(ValidationError):
        EvidenceSummary.model_validate(summary)
    # No fixture file is changed to manually_verified=true.


def test_business_variable_requires_valid_source_value_and_approval():
    summary = extract(PDF_OLD).model_dump()
    summary["records"][0]["manually_verified"] = True
    summary["business_variables"] = [BusinessVariable(name=EvidenceField.renewal_notice_days,
        value=60, unit="days", evidence_id="EV-001", quote_matched=True,
        manually_verified=True).model_dump()]
    EvidenceSummary.model_validate(summary)
    summary["records"][0]["extracted_value"] = 90
    with pytest.raises(ValidationError):
        EvidenceSummary.model_validate(summary)


def test_cross_object_ids_coverage_and_fixed_options(integrated):
    summary, _, pending = integrated
    raw = pending.model_dump()
    raw["critic_issues"].append(copy.deepcopy(raw["critic_issues"][0]))
    with pytest.raises(ValidationError):
        MockE2EPayload.model_validate(raw)
    raw = pending.model_dump(); raw["brief"]["critic_issue_ids"] = ["CR-999"]
    with pytest.raises(ValidationError):
        MockE2EPayload.model_validate(raw)
    raw = pending.model_dump(); raw["matrix"].pop()
    with pytest.raises(ValidationError):
        MockE2EPayload.model_validate(raw)
    raw = pending.model_dump(); raw["options"][0]["terminate_A"] = True
    with pytest.raises(ValidationError):
        MockE2EPayload.model_validate(raw)
    assert set(s.id for s in pending.scenarios) == {"baseline", "demand-drop", "lead-stress"}
    assert len(pending.matrix) == 9 and summary.business_variables == []


def test_baseline_pdf_hash_quotes_and_nonmixed_locators(integrated):
    summary, baseline, _ = integrated
    assert PDF_NEW.read_bytes() != PDF_OLD.read_bytes()
    assert len(summary.records) == 6 and all(r.page == 4 and r.quote_matched for r in summary.records)
    assert all(r.source_sha256 == hashlib.sha256(PDF_NEW.read_bytes()).hexdigest() for r in summary.records)
    assert summary.records[-1].id == "EV-020"  # preserved auto-renew evidence
    assert [r["id"] for r in baseline["evidence"]] == list(FRONT_IDS)
    assert all(not r.manually_verified and r.source_quote and r.source_span for r in summary.records)


def test_adapter_mapping_and_mock_not_falsely_upgraded(integrated):
    summary, baseline, pending = integrated
    front, ledger = adapt(summary, baseline, PDF_NEW, pending)
    assert front["meta"]["schemaVersion"] == "causora.contract.v1"
    assert front["meta"]["dataVersion"] == front["simulation"]["dataVersion"] == DATA_VERSION
    assert "LOCAL MOCK" in front["meta"]["notice"] and "LOCAL MOCK" in front["meta"]["status"]
    assert [r["id"] for r in front["evidence"]] == list(FRONT_IDS)
    assert all(r["page"] == 4 and r["matchScore"] == 1.0 and r["sourceFile"] == PDF_NEW.name for r in front["evidence"])
    assert all(r["locatorBbox"] is None for r in front["evidence"])
    assert all(r["locator_bbox"] for r in ledger["evidenceRecords"])
    assert front["evidence"][2]["extractedValue"] == "14%"
    assert front["contract"]["renewalPriceIncreasePct"] == 0.14
    assert front["contract"]["minPurchaseShareA"] == 0.6
    assert front["scenarios"][1]["demandShock"] == -15
    assert front["simulation"]["matrix"] == baseline["simulation"]["matrix"]
    assert front["brief"]["recommendedOptionId"] == baseline["brief"]["recommendedOptionId"] == "D1"
    assert pending.brief.recommended_option_id is None and ledger["wangPendingRecommendation"] is None
    assert ledger["humanSignoff"] == "PENDING" and ledger["businessVariablesPromoted"] == []
    assert ledger["sourceSha256"] == summary.records[0].source_sha256


def test_adapter_rejects_source_mix_or_fake_approval(integrated):
    summary, baseline, pending = integrated
    with pytest.raises(ValueError, match="one-page"):
        adapt(extract(PDF_OLD), baseline, PDF_OLD, build(extract(PDF_OLD)))
    altered = summary.model_copy(deep=True)
    altered.records[0].manually_verified = True
    with pytest.raises(ValueError, match="unreview"):
        adapt(altered, baseline, PDF_NEW, build(altered))
    altered = summary.model_copy(deep=True)
    altered.records[0].source_sha256 = "0" * 64
    with pytest.raises(ValueError, match="hash"):
        adapt(altered, baseline, PDF_NEW, build(altered))


def test_structural_frontend_schemas_and_json(integrated):
    folder = BASE
    mock = json.loads((folder / "frontend_compatible_local_mock.json").read_text(encoding="utf-8"))
    ev = json.loads((folder / "frontend_evidence.schema.json").read_text(encoding="utf-8"))
    schema = json.loads((folder / "frontend_compatible_local_mock.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(ev)
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(mock, schema)
    jsonschema.validate(mock["evidence"][0], ev)
    bad = copy.deepcopy(mock); bad["evidence"][0]["matchScore"] = 100
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def response(text: str, finish: str = "stop"):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text), finish_reason=finish)])


def fake_client(replies: list[object]):
    iterator = iter(replies)
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: next(iterator))))


def test_provider_json_requires_real_boolean_not_numeric():
    assert valid_structured_reply('{"ready":true}')
    for bad in ('{"ready":1}', '{"ready":1.0}', '{"ready":"true"}',
                '{"ready":false}', '{"ready":true,"extra":1}', 'not json'):
        assert not valid_structured_reply(bad)
    assert _check(fake_client([response('{"ready":1}')]), "offline", True)["ok"] is False
    assert _check(fake_client([response('{"ready":1.0}')]), "offline", True)["ok"] is False
    assert _check(fake_client([response('{"ready":true}')]), "offline", True)["ok"] is True


def test_provider_offline_success_failure_exception_and_missing_configuration():
    env = {"OPENAI_API_KEY": "offline-placeholder", "OPENAI_API_BASE": "https://offline.invalid/v1"}
    factory = lambda **_: fake_client([response("READY"), response('{"ready":true}')])
    assert all(c["ok"] for c in run(["offline"], environ=env, client_factory=factory)["results"][0]["checks"])
    bad_factory = lambda **_: fake_client([response("WRONG"), response('{"ready":false}', finish="length")])
    assert all(not c["ok"] for c in run(["offline"], environ=env, client_factory=bad_factory)["results"][0]["checks"])
    class Exploding:
        def create(self, **kwargs):
            raise TimeoutError("do not log any raw URL or secret")
    client = SimpleNamespace(chat=SimpleNamespace(completions=Exploding()))
    assert _check(client, "offline", False)["error_type"] == "TimeoutError"
    missing = run(["offline"], environ={})
    assert missing["results"][0]["checks"][0]["error_type"] == "MissingEnvironment"
