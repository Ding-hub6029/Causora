"""Source-bound evidence validation for the Day 4 input boundary.

This module deliberately validates the original PDF bytes and extracted page text.  A
``quoteMatched``/``manually_verified`` flag is metadata only and can never make an
otherwise invalid evidence record pass.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path
import math
import re
from typing import Any


_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_EVIDENCE_ID_RE = re.compile(r"^EV-\d{3}$")
_WS_RE = re.compile(r"\s+")

# These are the only contract evidence records exposed to Day 4.  EV-020 is
# retained as a conditional-clause record, rather than an unconditional legal
# conclusion.
_EXPECTED: dict[str, dict[str, Any]] = {
    "EV-014": {
        "field": "renewal_notice_days", "value": 60, "unit": "days",
        "quote": "If written notice is not received at least 60 days before renewal, the agreement automatically renews.",
    },
    "EV-019": {
        "field": "renewal_term_months", "value": 24, "unit": "months",
        "quote": "The agreement automatically renews for 24 months at a 14% higher unit price.",
    },
    "EV-020": {
        "field": "auto_renew", "value": True, "unit": "boolean",
        "quote": "The agreement automatically renews for 24 months at a 14% higher unit price.",
    },
    "EV-021": {
        "field": "renewal_price_increase_pct", "value": 0.14, "unit": "percent",
        "quote": "The agreement automatically renews for 24 months at a 14% higher unit price.",
    },
    "EV-024": {
        "field": "min_purchase_share_A", "value": 0.6, "unit": "share",
        "quote": "The renewed term has a minimum purchase commitment equal to 60% of forecast demand.",
    },
    "EV-027": {
        "field": "termination_fee", "value": 25000, "unit": "USD",
        "quote": "Early exit during the renewed term incurs a fixed termination fee of $25,000.",
    },
}
_PUBLIC_IDS = frozenset(("EV-014", "EV-019", "EV-021", "EV-024", "EV-027"))
_SOURCE_BASENAME = "supplier_a_agreement.pdf"


class EvidenceValidationError(ValueError):
    """Raised when an evidence item is not demonstrably bound to its source."""


def canonical_sha256(value: Any) -> str:
    """Return the compact canonical JSON SHA-256 used by trace identities."""
    import json
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _fail(message: str) -> None:
    raise EvidenceValidationError(message)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{label}: expected an object")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label}: expected non-empty text")
    return value


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        _fail(f"{label}: expected a finite number")
    return float(value)


def _normalise(value: str) -> str:
    # PDF extraction frequently introduces a different line ending or a layout
    # whitespace run.  Characters and punctuation remain exact after this
    # normalisation; this is not fuzzy matching.
    return _WS_RE.sub(" ", value.replace("\u00a0", " ")).strip()


def _first(record: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record:
            return record[key]
    return None


def _source_candidates(source_root: Path, source_name: str) -> list[Path]:
    raw = Path(source_name)
    if raw.is_absolute() or ".." in raw.parts:
        _fail("evidence.sourceFile: source paths must be relative and cannot escape source_root")
    root = source_root.resolve()
    candidates = [root / raw]
    # Current sources use all of these legitimate layouts.  The evidence record
    # may use only a basename while trace provenance uses public/demo/... .
    if len(raw.parts) == 1:
        candidates.extend((
            root / "public" / "demo" / raw.name,
            root / "fixtures" / "demo" / raw.name,
            root / "frontend" / "public" / "demo" / raw.name,
            root / "backend" / "backend" / "public" / "demo" / raw.name,
            root / "agents" / "wanghao-day3" / "fixtures" / "demo" / raw.name,
        ))
    else:
        candidates.extend((root / "frontend" / raw, root / "backend" / "backend" / raw))
    result: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in result and (resolved == root or root in resolved.parents) and resolved.is_file():
            result.append(resolved)
    return result


def _pdf_page_text(path: Path, page_one_based: int) -> str:
    try:
        import fitz  # PyMuPDF is a project dependency and reads the source PDF directly.
    except ImportError:
        # Some isolated test interpreters do not inherit the project's optional
        # PyMuPDF wheel.  Poppler remains an original-PDF reader, not a cached
        # extraction or a boolean trust fallback.
        import subprocess
        try:
            completed = subprocess.run(
                ["pdftotext", "-f", str(page_one_based), "-l", str(page_one_based), str(path), "-"],
                check=True, capture_output=True, text=True, timeout=20,
            )
            if not completed.stdout.strip():
                _fail(f"evidence.page: page {page_one_based} is outside original PDF or has no extractable text")
            return completed.stdout
        except EvidenceValidationError:
            raise
        except Exception as exc:  # pragma: no cover - host command failure is explicit
            raise EvidenceValidationError("a local original-PDF text extractor is required for evidence validation") from exc
    try:
        document = fitz.open(path)
        try:
            if page_one_based < 1 or page_one_based > document.page_count:
                _fail(f"evidence.page: page {page_one_based} is outside original PDF")
            return document.load_page(page_one_based - 1).get_text("text")
        finally:
            document.close()
    except EvidenceValidationError:
        raise
    except Exception as exc:
        raise EvidenceValidationError(f"evidence.sourceFile: cannot read original PDF {path.name}") from exc


def _coerce_value(record: Mapping[str, Any], expected: Mapping[str, Any], label: str) -> Any:
    """Normalise wire strings only to compare their declared typed extraction."""
    raw = _first(record, "extractedValue", "extracted_value")
    unit = _first(record, "unit")
    if raw is None:
        _fail(f"{label}.extractedValue: missing")
    expected_value = expected["value"]
    expected_unit = expected["unit"]
    if unit is not None and unit != expected_unit:
        _fail(f"{label}.unit: expected {expected_unit!r}")
    if isinstance(expected_value, bool):
        if raw is not True:
            _fail(f"{label}.extractedValue: expected boolean true")
        return True
    if isinstance(raw, str):
        compact = raw.strip().replace(",", "")
        if expected_unit == "percent":
            if not compact.endswith("%"):
                _fail(f"{label}.extractedValue: percent extraction must retain '%' unit")
            try:
                value = float(compact[:-1]) / 100
            except ValueError:
                _fail(f"{label}.extractedValue: invalid percent")
        elif expected_unit == "share":
            if not compact.endswith("%"):
                _fail(f"{label}.extractedValue: share extraction must retain '%' unit")
            try:
                value = float(compact[:-1]) / 100
            except ValueError:
                _fail(f"{label}.extractedValue: invalid share")
        elif expected_unit == "USD":
            if not compact.startswith("$"):
                _fail(f"{label}.extractedValue: USD extraction must retain '$' unit")
            try:
                value = float(compact[1:])
            except ValueError:
                _fail(f"{label}.extractedValue: invalid USD amount")
        else:
            match = re.fullmatch(r"([+-]?\d+(?:\.0+)?)\s+" + re.escape(expected_unit), compact)
            if not match:
                _fail(f"{label}.extractedValue: expected numeric value with {expected_unit!r} unit")
            value = float(match.group(1))
    else:
        value = _number(raw, f"{label}.extractedValue")
        # Native extraction records retain a numeric percentage as ``14`` with
        # unit ``percent``; typed contract values use the fraction ``0.14``.
        # ``enrich_evidence`` subsequently emits that typed fraction, which is
        # accepted on revalidation rather than divided by 100 a second time.
        if expected_unit == "percent":
            if not math.isclose(value, float(expected_value), rel_tol=0.0, abs_tol=1e-12):
                value /= 100
    if not math.isclose(float(value), float(expected_value), rel_tol=0.0, abs_tol=1e-12):
        _fail(f"{label}.extractedValue: does not equal the source-supported {expected_value!r}")
    return expected_value


def _validate_optional_date(record: Mapping[str, Any], page_text: str, label: str) -> None:
    """Reject malformed/invented date extractions when an evidence record provides one."""
    value = _first(record, "extractedDate", "extracted_date", "date")
    if value is None:
        return
    value = _text(value, f"{label}.date")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise EvidenceValidationError(f"{label}.date: expected ISO calendar date") from exc
    if value not in page_text:
        _fail(f"{label}.date: date is not present in the quoted source page")


def _validate_bbox(record: Mapping[str, Any], label: str) -> None:
    bbox = _first(record, "locatorBbox", "locator_bbox")
    if bbox is None:
        return
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        _fail(f"{label}.locatorBbox: expected four coordinates")
    coords = [_number(value, f"{label}.locatorBbox") for value in bbox]
    if coords[2] <= coords[0] or coords[3] <= coords[1]:
        _fail(f"{label}.locatorBbox: invalid rectangle")


@dataclass(frozen=True)
class ValidatedEvidence:
    """A detached, source-checked evidence view safe to project into role prompts."""

    id: str
    page: int
    quote: str
    extracted_field: str
    extracted_value: Any
    unit: str
    source_file: str
    source_sha256: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "page": self.page,
            "quote": self.quote,
            "extractedField": self.extracted_field,
            "extractedValue": self.extracted_value,
            "unit": self.unit,
        }


def validate_evidence_records(
    records: Iterable[Mapping[str, Any]],
    *,
    source_root: Path,
    trace_contract_provenance: Mapping[str, Mapping[str, Any]] | None = None,
    required_ids: Iterable[str] | None = None,
) -> tuple[ValidatedEvidence, ...]:
    """Validate exact evidence quotations against original PDF bytes.

    ``trace_contract_provenance`` is keyed by evidence ID.  When supplied, each
    record's PDF hash must equal the source hash that the formula trace declares;
    this prevents a quote from one source being paired with a trace from another.
    """
    if not isinstance(source_root, Path):
        source_root = Path(source_root)
    if not source_root.is_dir():
        _fail("source_root: expected an existing directory")
    items = list(records)
    seen: set[str] = set()
    validated: list[ValidatedEvidence] = []
    for index, raw in enumerate(items):
        record = _mapping(raw, f"evidence[{index}]")
        evidence_id = _text(record.get("id"), f"evidence[{index}].id")
        if not _EVIDENCE_ID_RE.fullmatch(evidence_id) or evidence_id not in _EXPECTED:
            _fail(f"evidence[{index}].id: unsupported evidence identifier")
        if evidence_id in seen:
            _fail(f"evidence[{index}].id: duplicate identifier")
        seen.add(evidence_id)
        expected = _EXPECTED[evidence_id]
        label = f"evidence[{evidence_id}]"
        source_name = _text(_first(record, "sourceFile", "source_file"), f"{label}.sourceFile")
        declared_hash = _text(_first(record, "sourceSha256", "source_sha256"), f"{label}.sourceSha256")
        if not _SHA256_RE.fullmatch(declared_hash):
            _fail(f"{label}.sourceSha256: expected lowercase SHA-256")
        candidates = _source_candidates(source_root, source_name)
        if not candidates:
            _fail(f"{label}.sourceFile: original source PDF is unavailable under source_root")
        matching = [path for path in candidates if sha256(path.read_bytes()).hexdigest() == declared_hash]
        # The project deliberately packages byte-identical frontend, backend and
        # agent copies.  They are one pinned source artifact for integrity
        # purposes; a nonmatching duplicate can never satisfy this condition.
        if not matching:
            _fail(f"{label}.sourceSha256: does not bind an original source file")
        path = matching[0]
        page = _first(record, "page")
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            _fail(f"{label}.page: expected a one-based page integer")
        page_text = _pdf_page_text(path, page)
        quote = _text(record.get("quote"), f"{label}.quote")
        source_quote = _first(record, "sourceQuote", "source_quote")
        if source_quote is not None and source_quote != quote:
            _fail(f"{label}.sourceQuote: must exactly equal quote")
        if quote != expected["quote"]:
            _fail(f"{label}.quote: does not match the permitted original clause")
        normalised_page, normalised_quote = _normalise(page_text), _normalise(quote)
        if normalised_quote not in normalised_page:
            _fail(f"{label}.quote: exact quote is not present on original PDF page")
        span = _first(record, "sourceSpan", "source_span")
        if span is not None:
            if not isinstance(span, (list, tuple)) or len(span) != 2 or any(isinstance(v, bool) or not isinstance(v, int) for v in span):
                _fail(f"{label}.sourceSpan: expected two integer offsets")
            offset = normalised_page.find(normalised_quote)
            if list(span) != [offset, offset + len(normalised_quote)]:
                _fail(f"{label}.sourceSpan: offsets do not recompute from source page text")
        _validate_bbox(record, label)
        field = _text(_first(record, "extractedField", "extracted_field"), f"{label}.extractedField")
        if field != expected["field"]:
            _fail(f"{label}.extractedField: source field mismatch")
        value = _coerce_value(record, expected, label)
        _validate_optional_date(record, normalised_page, label)
        # Flags are intentionally ignored as proof.  If present they must not
        # misrepresent an artificial manual signature.
        if record.get("manually_verified") is True or record.get("manuallyVerified") is True:
            _fail(f"{label}: fabricated manual-verification flag is not accepted")
        if trace_contract_provenance is not None and evidence_id in trace_contract_provenance:
            provenance = _mapping(trace_contract_provenance[evidence_id], f"trace provenance for {evidence_id}")
            if provenance.get("sourceSha256") != declared_hash:
                _fail(f"{label}: evidence PDF hash differs from trace contract provenance")
            trace_file = provenance.get("sourceFile")
            if not isinstance(trace_file, str) or Path(trace_file).name != path.name:
                _fail(f"{label}: evidence source differs from trace contract provenance")
            ids = provenance.get("evidenceIds")
            if not isinstance(ids, list) or evidence_id not in ids:
                _fail(f"{label}: trace provenance does not cite this evidence identifier")
        try:
            source_file = path.relative_to(source_root.resolve()).as_posix()
        except ValueError:  # pragma: no cover - _source_candidates already confines paths
            _fail(f"{label}.sourceFile: resolved outside source_root")
        validated.append(ValidatedEvidence(evidence_id, page, quote, field, value, expected["unit"], source_file, declared_hash))
    required = set(required_ids) if required_ids is not None else set()
    if not required.issubset(seen):
        _fail(f"evidence: missing required identifiers {sorted(required - seen)}")
    return tuple(validated)


def public_evidence(records: Iterable[ValidatedEvidence], *, include_conditional: bool = False) -> list[dict[str, Any]]:
    """Return the source-path-free evidence allowlist for a Risk role projection."""
    allowed = set(_PUBLIC_IDS)
    if include_conditional:
        allowed.add("EV-020")
    return [record.public_dict() for record in records if record.id in allowed]


def _enrichment_contract(contract: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the actual contract payload accepted by the public-record adapter."""
    value = _mapping(contract, "contract")
    if "contract" in value:
        value = _mapping(value.get("contract"), "contract.contract")
    evidence_ids = value.get("evidenceIds")
    if not isinstance(evidence_ids, (list, tuple)) or any(not isinstance(item, str) for item in evidence_ids):
        _fail("contract.evidenceIds: expected string evidence IDs")
    if set(evidence_ids) != _PUBLIC_IDS or len(evidence_ids) != len(_PUBLIC_IDS):
        _fail("contract.evidenceIds: expected the exact five public evidence IDs")
    return value


def enrich_evidence(
    records: Iterable[Mapping[str, Any]],
    *,
    source_root: Path | str,
    contract: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Adapt public ``EvidenceRecord`` objects into private, source-bound records.

    The frontend DTO deliberately has no source hash or trusted typed value.  This
    helper obtains both from the physical PDF and the fixed source clause rather
    than accepting client flags such as ``quoteMatched`` or ``matchScore`` as
    evidence.  It is intentionally useful to both backend routing and test
    fixtures: callers pass the public records unchanged, then pass this result to
    :func:`validate_evidence_records` together with trace provenance when present.

    ``EV-020`` remains a conditional internal clause.  It is accepted only when
    the supplied contract has a boolean ``renewalLocked`` field; it is never added
    to the public five-ID contract list by this adapter.
    """
    root = Path(source_root).resolve()
    if not root.is_dir():
        _fail("source_root: expected an existing directory")
    contract_payload = _enrichment_contract(contract)
    allowed = set(_PUBLIC_IDS)
    if isinstance(contract_payload.get("renewalLocked"), bool):
        allowed.add("EV-020")

    candidates: list[dict[str, Any]] = []
    for index, raw in enumerate(list(records)):
        record = _mapping(raw, f"public evidence[{index}]")
        evidence_id = _text(record.get("id"), f"public evidence[{index}].id")
        if not _EVIDENCE_ID_RE.fullmatch(evidence_id) or evidence_id not in allowed:
            _fail(f"public evidence[{index}].id: not permitted by supplied contract")
        if record.get("manually_verified") is True or record.get("manuallyVerified") is True:
            _fail(f"public evidence[{index}]: fabricated manual-verification flag is not accepted")
        expected = _EXPECTED[evidence_id]
        source_name = _first(record, "sourceFile", "source_file")
        if source_name is None:
            source_name = _SOURCE_BASENAME
        source_name = _text(source_name, f"public evidence[{index}].sourceFile")
        if Path(source_name).name != _SOURCE_BASENAME:
            _fail(f"public evidence[{index}].sourceFile: unexpected contract source")
        source_paths = _source_candidates(root, source_name)
        if not source_paths:
            _fail(f"public evidence[{index}].sourceFile: original source PDF is unavailable under source_root")
        # A source name can resolve to byte-identical packaged copies.  The
        # resolved path, and more importantly its physical SHA-256, are chosen
        # here; a supplied sourceSha256 is never copied into the private record.
        source_path = source_paths[0]
        actual_hash = sha256(source_path.read_bytes()).hexdigest()
        supplied_hash = _first(record, "sourceSha256", "source_sha256")
        if supplied_hash is not None:
            supplied_hash = _text(supplied_hash, f"public evidence[{index}].sourceSha256")
            if not _SHA256_RE.fullmatch(supplied_hash) or supplied_hash != actual_hash:
                _fail(f"public evidence[{index}].sourceSha256: differs from physical source PDF")
        try:
            source_file = source_path.relative_to(root).as_posix()
        except ValueError:  # pragma: no cover - candidates are confined above
            _fail(f"public evidence[{index}].sourceFile: resolved outside source_root")
        candidates.append({
            "id": evidence_id,
            "sourceFile": source_file,
            "sourceSha256": actual_hash,
            "page": record.get("page"),
            "quote": record.get("quote"),
            "extractedField": record.get("extractedField", record.get("extracted_field")),
            "extractedValue": record.get("extractedValue", record.get("extracted_value")),
            # This is the source schema's unit, not an untrusted public field.
            "unit": expected["unit"],
        })

    # Re-read the original PDF and check the exact quote before marking anything
    # matched.  This also normalises source values (for example ``"14%"`` to
    # ``0.14``) through the canonical typed extraction checker.
    checked = validate_evidence_records(candidates, source_root=root)
    return tuple({
        "id": item.id,
        "sourceFile": item.source_file,
        "sourceSha256": item.source_sha256,
        "page": item.page,
        "quote": item.quote,
        "extractedField": item.extracted_field,
        "extractedValue": item.extracted_value,
        "unit": item.unit,
        # This is the sole trusted quote-matched state: it exists only after the
        # exact PDF/page/typed-value checks above have completed.
        "quoteMatched": True,
    } for item in checked)


__all__ = [
    "EvidenceValidationError",
    "ValidatedEvidence",
    "canonical_sha256",
    "enrich_evidence",
    "public_evidence",
    "validate_evidence_records",
]
