"""Conservative PDF quote matching. A text-layer match is NOT human or legal approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from rapidfuzz import fuzz

from .claim_checks import PATTERNS, UNITS, normalize, supported_claim
from .schemas import EvidenceField, EvidenceRecord, EvidenceSummary

# The original one-page fixture remains a SEPARATE regression asset, never a v4.1 source.
CLAIMS = [
    ("EV-001", EvidenceField.renewal_notice_days, 60, "days", "at least 60 days before renewal", PATTERNS["renewal_notice_days"].pattern),
    ("EV-002", EvidenceField.auto_renew, True, "boolean", "the agreement automatically renews for 24 months", PATTERNS["auto_renew"].pattern),
    ("EV-003", EvidenceField.renewal_term_months, 24, "months", "automatically renews for 24 months", PATTERNS["renewal_term_months"].pattern),
    ("EV-004", EvidenceField.renewal_price_increase_pct, 14, "percent", "at a 14% higher unit price", PATTERNS["renewal_price_increase_pct"].pattern),
    ("EV-005", EvidenceField.min_purchase_share_A, 0.6, "share", "minimum purchase commitment equal to 60% of forecast demand", PATTERNS["min_purchase_share_A"].pattern),
    ("EV-006", EvidenceField.termination_fee, 25000, "USD", "fixed termination fee of $25,000", PATTERNS["termination_fee"].pattern),
]

BASELINE_VALUES = {
    "EV-014": (EvidenceField.renewal_notice_days, 60),
    "EV-019": (EvidenceField.renewal_term_months, 24),
    "EV-021": (EvidenceField.renewal_price_increase_pct, 14),
    "EV-024": (EvidenceField.min_purchase_share_A, 0.6),
    "EV-027": (EvidenceField.termination_fee, 25000),
}


@dataclass(frozen=True)
class SourceMatch:
    method: str = "none"
    score: float = 0.0  # 0..100 internally
    bbox: list[float] | None = None
    source_quote: str | None = None
    source_span: list[int] | None = None  # normalized page text [start,end)


def semantic_match(field: EvidenceField, value: int | float | bool, text: str, pattern: str) -> bool:
    """Backwards-compatible signature; the independent typed check is authoritative."""
    del pattern
    return supported_claim(field.value, value, UNITS[field.value], text)


def _candidate_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return [" ".join(lines[i:i + width]) for i in range(len(lines)) for width in (1, 2) if i + width <= len(lines)]


def _rect_for(page: pymupdf.Page, source_text: str) -> list[float] | None:
    found = page.search_for(source_text)
    if not found:
        return None
    # A wrapped quote can yield multiple rectangles. Keep one conservative union.
    union = pymupdf.Rect(found[0])
    for rect in found[1:]:
        union |= rect
    if (not page.rect.contains(union) or not all(math.isfinite(v) for v in union)
            or union.is_empty or not union.x0 < union.x1 or not union.y0 < union.y1):
        return None
    return [float(union.x0), float(union.y0), float(union.x1), float(union.y1)]


def locate_detail(page: pymupdf.Page, quote: str, field: EvidenceField,
                  value: int | float | bool, pattern: str) -> SourceMatch:
    del pattern
    source_raw = page.get_text("text", sort=True)
    source = normalize(source_raw)
    claim = normalize(quote)
    unit = UNITS[field.value]
    # Both the offered quote and its source-side context must support the claim.
    if not supported_claim(field.value, value, unit, quote, context=source_raw):
        return SourceMatch()
    if claim in source:
        box = _rect_for(page, quote)
        if box is not None:
            actual = page.get_textbox(pymupdf.Rect(box)).strip()
            if actual and claim in normalize(actual):
                index = source.index(claim)
                return SourceMatch("exact", 100.0, box, actual, [index, index + len(claim)])
    # A whole-candidate ratio rejects a true substring followed by invented text.
    # Partial-ratio alone could award a fabricated "This fee is waived" 100 points.
    for candidate in _candidate_lines(source_raw):
        normalized = normalize(candidate)
        if not supported_claim(field.value, value, unit, candidate, context=source_raw):
            continue
        score = fuzz.ratio(claim, normalized)
        if score < 95 or min(len(claim), len(normalized)) / max(len(claim), len(normalized)) < 0.95:
            continue
        box = _rect_for(page, candidate)
        index = source.find(normalized)
        if box is None or index < 0:
            continue
        actual = page.get_textbox(pymupdf.Rect(box)).strip()
        if actual and fuzz.ratio(normalize(actual), normalized) >= 95:
            return SourceMatch("fuzzy", float(score), box, actual, [index, index + len(normalized)])
    return SourceMatch()


def locate(page: pymupdf.Page, quote: str, field: EvidenceField, value: int | float | bool,
           pattern: str) -> tuple[str, float, list[float] | None]:
    """Compatibility wrapper retained for the original Day 1 tests."""
    result = locate_detail(page, quote, field, value, pattern)
    return result.method, result.score, result.bbox


def verify_source(summary: EvidenceSummary, pdf: Path) -> None:
    """Bind each matched record to this PDF's digest, real page, text span and page bounds."""
    if pdf.name != summary.source_file:
        raise ValueError("PDF basename does not match the evidence summary")
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    with pymupdf.open(pdf) as doc:
        for record in summary.records:
            if record.source_sha256 != digest or record.page > len(doc):
                raise ValueError(f"{record.id}: source hash or page mismatch")
            if not record.quote_matched:
                continue
            page = doc[record.page - 1]
            rect = pymupdf.Rect(record.locator_bbox)
            if (not page.rect.contains(rect) or not all(math.isfinite(v) for v in rect)
                    or rect.is_empty):
                raise ValueError(f"{record.id}: bbox outside the cited page")
            page_text = normalize(page.get_text("text", sort=True))
            start, end = record.source_span
            if end > len(page_text) or not page_text[start:end] or normalize(record.source_quote) not in page_text:
                raise ValueError(f"{record.id}: source span/quote absent from PDF page")
            if record.match_method == "exact" and page_text[start:end] != normalize(record.quote):
                raise ValueError(f"{record.id}: exact match's source span changed")
            if record.match_method == "fuzzy" and fuzz.ratio(page_text[start:end], normalize(record.source_quote)) < 95:
                raise ValueError(f"{record.id}: fuzzy source span changed")
            actual = normalize(page.get_textbox(rect))
            if not actual or (normalize(record.quote) not in actual and record.match_method == "exact"):
                raise ValueError(f"{record.id}: bbox does not identify its quote")
            if not supported_claim(record.extracted_field.value, record.extracted_value, record.unit,
                                   record.quote, context=page.get_text("text", sort=True)):
                raise ValueError(f"{record.id}: contradicted or unsupported source clause")


def extract(pdf: Path, *, claims: list[tuple] = CLAIMS, dataset_id: str = "supplier-a-synthetic-v1",
            assumptions: dict | None = None) -> EvidenceSummary:
    if pdf.suffix.lower() != ".pdf" or pdf.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("A PDF no larger than 5 MB is required")
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    records: list[EvidenceRecord] = []
    with pymupdf.open(pdf) as doc:
        if not doc or not any(page.get_text("text").strip() for page in doc):
            raise ValueError("Scanned/image-only PDF is out of MVP scope")
        for evidence_id, field, value, unit, quote, pattern in claims:
            for page_no, page in enumerate(doc, start=1):
                result = locate_detail(page, quote, field, value, pattern)
                if result.bbox is not None:
                    records.append(EvidenceRecord(id=evidence_id, source_file=pdf.name, source_sha256=digest,
                        page=page_no, quote=quote, source_quote=result.source_quote, source_span=result.source_span,
                        locator_bbox=result.bbox, extracted_field=field, extracted_value=value, unit=unit,
                        match_method=result.method, match_score=result.score, quote_matched=True,
                        manually_verified=False))
                    break
            else:
                records.append(EvidenceRecord(id=evidence_id, source_file=pdf.name, source_sha256=digest,
                    page=1, quote=quote, source_quote=None, source_span=None, locator_bbox=None,
                    extracted_field=field, extracted_value=value, unit=unit,
                    match_method="none", match_score=0.0, quote_matched=False, manually_verified=False))
    summary = EvidenceSummary(dataset_id=dataset_id, source_file=pdf.name, records=records,
        business_variables=[], scenario_assumptions=assumptions or {"days_to_renewal": 45},
        status="MOCK_QUOTE_MATCHED_SYNTHETIC")
    verify_source(summary, pdf)
    return summary


def extract_baseline(pdf: Path, baseline_mock: Path) -> EvidenceSummary:
    """Only v4.1's OWN PDF and quote IDs are accepted; EV-020 preserves auto-renew internally."""
    data = json.loads(baseline_mock.read_text(encoding="utf-8"))
    if (data["meta"]["schemaVersion"] != "causora.contract.v1"
            or data["intake"][3]["path"] != "/demo/supplier_a_agreement.pdf"
            or pdf.name != "supplier_a_agreement.pdf"):
        raise ValueError("Expected the v4.1 synthetic agreement and contract version")
    claims = []
    for item in data["evidence"]:
        field, value = BASELINE_VALUES[item["id"]]
        quote = item["quote"]
        claims.append((item["id"], field, value, UNITS[field.value], quote, PATTERNS[field.value].pattern))
    # The frontend exposes five fixed IDs; auto-renew is not discarded from our full ledger.
    renewal_quote = next(item["quote"] for item in data["evidence"] if item["id"] == "EV-019")
    claims.append(("EV-020", EvidenceField.auto_renew, True, "boolean", renewal_quote, PATTERNS["auto_renew"].pattern))
    contract = data["contract"]
    assumptions = {"days_to_renewal": contract["daysToRenewal"], "decision_date": contract["decisionDate"],
                   "renewal_date": contract["renewalDate"], "notice_sent": contract["noticeSent"],
                   "locked_forecast_units_24m": contract["lockedForecastUnits24m"],
                   "forecast_basis": contract["forecastBasis"],
                   "notice_record_source": contract["noticeRecordSource"]}
    return extract(pdf, claims=claims, dataset_id="ds-001", assumptions=assumptions)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Match synthetic PDF clauses; human approval stays false")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--baseline-mock", type=Path, help="v4.1 demo JSON, for its separate six-page agreement")
    args = parser.parse_args()
    summary = extract_baseline(args.pdf, args.baseline_mock) if args.baseline_mock else extract(args.pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Matched {sum(r.quote_matched for r in summary.records)}/{len(summary.records)} claims; manual signoff remains pending")
