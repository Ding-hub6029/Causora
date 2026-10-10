"""Strict numeric guardrail for Boardroom free text.

``scan_text`` intentionally has no provider, model, or mutation dependency.  A
number in a field is valid only when its *exact character range* is bound to a
field-local, declared registry reference.  The only exception is an explicitly
allowed exact identifier (for example the selected option id).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import math
import re
from typing import Any


# These are display tokens, not general-purpose references.  In particular,
# accepting arbitrary {{registry_key}} strings would allow a model to expose a
# metric from another scenario or option.
_PUBLIC_TOKENS: dict[str, str] = {
    "delta_tco": "money",
    "stockout_probability": "percent",
    "cash_outflow_p90": "money",
}

_SIGN = r"[+\-\N{MINUS SIGN}]"
_CORE = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_INT_CORE = r"(?:\d{1,3}(?:,\d{3})+|\d+)"

_TOKEN_RE = re.compile(r"\{\{[^{}]*\}\}")
_TOKEN_NAME_RE = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}\Z")
_DATE_RE = re.compile(r"(?<![A-Za-z0-9_])\d{4}-\d{2}-\d{2}(?![A-Za-z0-9_])")
_OPTION_OR_EVIDENCE_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:D\d+|EV-\d+|P\d+)(?![A-Za-z0-9_])"
)
# A scientific spelling must be recognized as one invalid span rather than
# allowing its mantissa to be matched as an apparently legitimate integer.
_SCIENTIFIC_RE = re.compile(
    rf"(?<![A-Za-z0-9_.]){_SIGN}?{_CORE}[eE]{_SIGN}?\d+(?![A-Za-z0-9_]|\.\d)"
)
# A formula/version identifier is not an authorised numeric exemption.  The
# Boardroom formula field may verify the exact ``tco-v1`` identifier separately;
# ordinary prose sent to this scanner must still be rejected.
_TECHNICAL_VERSION_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:[A-Za-z][A-Za-z0-9_]*-)?v\d+(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
# Do not let an unknown ID-like value such as ``S1`` hide its numeric portion
# merely because the digit directly follows a letter.  It remains acceptable
# only when the exact full identifier is supplied in allowed_ids.
_GENERIC_NUMERIC_ID_RE = re.compile(
    r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z_]*(?:-[A-Za-z_]+)*-?\d+(?:[-_][A-Za-z0-9_]+)*(?![A-Za-z0-9_])"
)
# Prefix and suffix USD forms, including -$12, $-12, −$12 and (US$12).
_CURRENCY_BODY = rf"(?:{_SIGN}?\s*(?:US\$|\$|USD)\s*{_SIGN}?\s*{_CORE}(?:\s*[kKmMbB])?|{_SIGN}?\s*{_CORE}(?:\s*[kKmMbB])?\s*(?:US\$|USD))"
_CURRENCY_RE = re.compile(
    rf"(?<![A-Za-z0-9_.+\-\N{{MINUS SIGN}}])(?:\(\s*{_CURRENCY_BODY}\s*\)|{_CURRENCY_BODY})(?![A-Za-z0-9_]|\.\d)"
)
_PERCENT_RE = re.compile(
    rf"(?<![A-Za-z0-9_.]){_SIGN}?\s*{_CORE}\s*(?:%|percent(?:age)?s?)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
# A percentage-point delta is not an interchangeable display of a probability
# fraction.  The current registry has no ``percentage_points`` kind, so retain
# it as a separate span and let the normal typed verifier reject it rather than
# silently treating ``8.7 percentage points`` as ``8.7%``.
_PERCENTAGE_POINT_RE = re.compile(
    rf"(?<![A-Za-z0-9_.]){_SIGN}?\s*{_CORE}\s*(?:percentage\s+points?|percent\s+points?|%\s*(?:points?|pts?)|pp|ppt)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
# A compact suffix without a dollar marker is still a normal compact monetary
# display ("419k"), but only a claimed money field may use it.
_COMPACT_RE = re.compile(
    rf"(?<![A-Za-z0-9_.]){_SIGN}?\s*{_CORE}\s*[kKmMbB](?![A-Za-z0-9_])"
)
_BARE_DECIMAL_RE = re.compile(
    rf"(?<![A-Za-z0-9_.]){_SIGN}?{_CORE}(?![A-Za-z0-9_]|\.\d)"
)
_INTEGER_RE = re.compile(
    rf"(?<![A-Za-z0-9_.]){_SIGN}?{_INT_CORE}(?![A-Za-z0-9_,]|\.\d)"
)
# Full-width digits/punctuation and the most common Chinese numeric characters
# are deliberately detected and rejected.  Normalising them would make an
# unsupported representation look verified.
_FULLWIDTH_NUMERIC_RE = re.compile(r"[０-９][０-９．，％]*|[％．，][０-９][０-９．，％]*")
_CJK_NUMERIC_RE = re.compile(r"[〇\u96f6\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u5343\u4e07\u842c\u5104\u4ebf\u5146\u5169\u4e24]+")
_WORD_NUMBER_RE = re.compile(
    r"\b(?:"
    r"zero|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
    r"hundred|thousand|million|billion|trillion|dozen|"
    r"first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth"
    r")\b",
    re.IGNORECASE,
)
_RAW_PUBLIC_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:delta_tco|stockout_probability|cash_outflow_p90)(?![A-Za-z0-9_])"
)
_UNKNOWN_CURRENCY_RE = re.compile(r"[€£¥₹]\s*[+\-−]?\s*\d")


@dataclass(frozen=True)
class _Span:
    """One logical numeric/identifier span in the supplied text."""

    start: int
    end: int
    text: str
    surface: str


def scan_text(
    text: str,
    *,
    registry: Mapping[str, Mapping[str, Any]],
    declared_refs: Iterable[str],
    claims: list[Mapping[str, Any]] = [],
    allowed_ids: Iterable[str] = [],
) -> list[str]:
    """Return deterministic violations for numeric content in ``text``.

    ``claims`` are positional bindings only: ``{"start", "end", "ref"}``.
    Their values are never trusted.  Every conventional digit-bearing span
    requires a non-overlapping claim with exactly the same range, except an
    exact member of ``allowed_ids`` (option/evidence identifiers shown as
    labels).  Token substitution has its own narrow, three-token allowlist.

    The function is fail-closed for malformed claims, braces, registry records,
    unsupported number representations, and invalid dates.  It does not mutate
    any supplied object.
    """

    violations: list[str] = []
    if not isinstance(text, str):
        return ["text must be a string"]
    if not isinstance(registry, Mapping):
        return ["registry must be a mapping"]

    declared, declaration_errors = _string_set(declared_refs, "declared_refs")
    allowed, allowed_errors = _string_set(allowed_ids, "allowed_ids")
    violations.extend(declaration_errors)
    violations.extend(allowed_errors)

    token_ranges = _check_tokens(text, registry, declared, violations)
    _check_unmatched_braces(text, token_ranges, violations)

    spans = _find_spans(text, token_ranges, allowed)
    claims_by_range = _validate_claims(
        text=text,
        claims=claims,
        spans=spans,
        registry=registry,
        declared=declared,
        violations=violations,
    )

    for span in spans:
        claim = claims_by_range.get((span.start, span.end))
        if span.surface == "raw_ref":
            violations.append(
                f"raw numeric reference {span.text!r} at {_where(span)} must use a declared {{token}}"
            )
            continue
        if span.surface in {
            "scientific",
            "technical_version",
            "bare_decimal",
            "fullwidth",
            "cjk",
            "word",
            "currency_other",
        }:
            violations.append(f"unsupported numeric form {span.text!r} at {_where(span)}")
            continue
        if span.surface == "id" and claim is None:
            if span.text in allowed:
                continue
            violations.append(f"identifier {span.text!r} at {_where(span)} is not in allowed_ids")
            continue
        if claim is None:
            violations.append(f"unbound numeric span {span.text!r} at {_where(span)}")
            continue

        # Claim structural/ref errors have already been emitted.  Do not use a
        # malformed binding as permission for the visible span.
        ref = claim["ref"]
        entry, entry_error = _registry_entry(registry, ref)
        if entry_error:
            violations.append(f"ref {ref!r} at {_where(span)}: {entry_error}")
            continue
        if ref not in declared:
            # _validate_claims reported this once; retaining this branch makes
            # direct use safe if callers later change claim validation.
            continue
        if entry['kind'] in {'units', 'integer'}:
            suffix = re.match(r'\s+(units?|weeks?|days?|months?)\b', text[span.end:], re.I)
            if suffix:
                shown_unit = suffix.group(1).lower().rstrip('s')
                expected_unit = entry['unit'].lower().rstrip('s')
                if expected_unit in {'unit', 'week', 'day', 'month'} and shown_unit != expected_unit:
                    violations.append(f"unit {shown_unit!r} does not match {expected_unit!r} for ref {ref!r} at {_where(span)}")
                    continue
        message = _verify_span(span, ref, entry)
        if message:
            violations.append(f"{message} at {_where(span)}")

    return violations


def _string_set(value: Iterable[str], label: str) -> tuple[set[str], list[str]]:
    """Return a validated set without treating a scalar string as an iterable."""

    if value is None:
        return set(), [f"{label} must be an iterable of strings"]
    if isinstance(value, (str, bytes)):
        return set(), [f"{label} must be an iterable of strings, not a string"]
    try:
        values = list(value)
    except TypeError:
        return set(), [f"{label} must be an iterable of strings"]
    bad = [item for item in values if not isinstance(item, str) or not item]
    if bad:
        return {item for item in values if isinstance(item, str) and item}, [
            f"{label} contains a non-string or empty reference"
        ]
    return set(values), []


def _check_tokens(
    text: str,
    registry: Mapping[str, Mapping[str, Any]],
    declared: set[str],
    violations: list[str],
) -> list[tuple[int, int]]:
    """Validate every complete brace construct and return shielded ranges."""

    ranges: list[tuple[int, int]] = []
    for match in _TOKEN_RE.finditer(text):
        ranges.append((match.start(), match.end()))
        name_match = _TOKEN_NAME_RE.fullmatch(match.group(0))
        if not name_match:
            violations.append(f"unknown or malformed token {match.group(0)!r} at {match.start()}:{match.end()}")
            continue
        name = name_match.group(1)
        expected_kind = _PUBLIC_TOKENS.get(name)
        if expected_kind is None:
            violations.append(f"unknown token {match.group(0)!r} at {match.start()}:{match.end()}")
            continue
        if name not in declared:
            violations.append(f"token {match.group(0)!r} is not declared")
            continue
        entry, error = _registry_entry(registry, name)
        if error:
            violations.append(f"token {match.group(0)!r}: {error}")
            continue
        if entry["kind"] != expected_kind:
            violations.append(
                f"token {match.group(0)!r} requires {expected_kind!r}, got {entry['kind']!r}"
            )
    return ranges


def _check_unmatched_braces(
    text: str, token_ranges: list[tuple[int, int]], violations: list[str]
) -> None:
    """Reject every brace outside a complete token; malformed braces never hide text."""

    for index, char in enumerate(text):
        if char not in "{}":
            continue
        if not any(start <= index < end for start, end in token_ranges):
            violations.append(f"malformed brace syntax at {index}")


def _find_spans(text: str, token_ranges: list[tuple[int, int]], allowed: set[str]) -> list[_Span]:
    """Find non-overlapping logical spans in precedence order.

    Precedence ensures a date/identifier/currency is not decomposed into
    several bare integers.  Complete or malformed brace constructs are
    shielded because the brace validator has already rejected malformed ones.
    """

    shielded = list(token_ranges)
    candidates: list[tuple[int, int, str, str]] = []

    def add_matches(pattern: re.Pattern[str], surface: str) -> None:
        for match in pattern.finditer(text):
            candidates.append((match.start(), match.end(), match.group(0), surface))

    # Context-authorised IDs are found as one exact span even when their shape
    # is not D# / EV-### (for example a scenario label containing digits).
    for value in sorted(allowed, key=len, reverse=True):
        if _DATE_RE.fullmatch(value) or _TECHNICAL_VERSION_RE.fullmatch(value):
            continue
        escaped = re.escape(value)
        pattern = re.compile(rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])")
        add_matches(pattern, "id")

    add_matches(_DATE_RE, "date")
    add_matches(_OPTION_OR_EVIDENCE_RE, "id")
    add_matches(_SCIENTIFIC_RE, "scientific")
    add_matches(_TECHNICAL_VERSION_RE, "technical_version")
    add_matches(_GENERIC_NUMERIC_ID_RE, "id")
    add_matches(_CURRENCY_RE, "money")
    add_matches(_PERCENTAGE_POINT_RE, "percentage_points")
    add_matches(_PERCENT_RE, "percent")
    add_matches(_COMPACT_RE, "compact")
    # Decimal must precede ordinary integers.  The matched decimals are
    # deliberately rejected, rather than silently accepted as quantities.
    for match in _BARE_DECIMAL_RE.finditer(text):
        if "." in match.group(0):
            candidates.append((match.start(), match.end(), match.group(0), "bare_decimal"))
    add_matches(_INTEGER_RE, "integer")
    add_matches(_FULLWIDTH_NUMERIC_RE, "fullwidth")
    add_matches(_CJK_NUMERIC_RE, "cjk")
    # A narrow grammatical phrase; other quantity words still require rejection.
    for match in _WORD_NUMBER_RE.finditer(text):
        if match.group(0).lower() == "one" and re.match(r"one set of options\b", text[match.start():], re.I):
            continue
        candidates.append((match.start(), match.end(), match.group(0), "word"))
    add_matches(_RAW_PUBLIC_REF_RE, "raw_ref")
    add_matches(_UNKNOWN_CURRENCY_RE, "currency_other")

    # Stable priority: source order first, then the order candidates were added
    # above.  The first selected candidate owns an overlapping region.
    candidates.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    spans: list[_Span] = []
    occupied = list(shielded)
    for start, end, raw, surface in candidates:
        if any(start < other_end and other_start < end for other_start, other_end in occupied):
            continue
        spans.append(_Span(start, end, raw, surface))
        occupied.append((start, end))
    spans.sort(key=lambda span: (span.start, span.end))
    return spans


def _validate_claims(
    *,
    text: str,
    claims: Any,
    spans: list[_Span],
    registry: Mapping[str, Mapping[str, Any]],
    declared: set[str],
    violations: list[str],
) -> dict[tuple[int, int], Mapping[str, Any]]:
    """Validate claim ranges/ref permissions and return usable exact bindings."""

    if claims is None:
        claims = []
    if isinstance(claims, (str, bytes)) or not isinstance(claims, Iterable):
        violations.append("claims must be an iterable of claim mappings")
        return {}

    # The documented shape is a mapping.  The pipeline also accepts a compact
    # positional binding [start, end, ref], which still carries no model value.
    # Treat one bare triple as one claim rather than three malformed claims.
    if (
        isinstance(claims, (list, tuple))
        and len(claims) == 3
        and isinstance(claims[0], int)
        and isinstance(claims[1], int)
        and isinstance(claims[2], str)
    ):
        claims = [claims]

    spans_by_range = {(span.start, span.end): span for span in spans}
    usable: list[tuple[int, int, int, Mapping[str, Any]]] = []
    for index, claim in enumerate(claims):
        prefix = f"claim {index}"
        if isinstance(claim, Mapping):
            start = claim.get("start")
            end = claim.get("end")
            ref = claim.get("ref")
            binding: Mapping[str, Any] = claim
        elif isinstance(claim, (list, tuple)) and len(claim) == 3:
            start, end, ref = claim
            binding = {"start": start, "end": end, "ref": ref}
        else:
            violations.append(f"{prefix} must be a mapping or [start, end, ref] triple")
            continue
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int):
            violations.append(f"{prefix} start/end must be integer offsets")
            continue
        if start < 0 or end > len(text) or start >= end:
            violations.append(f"{prefix} range {start}:{end} is outside text")
            continue
        if not isinstance(ref, str) or not ref:
            violations.append(f"{prefix} ref must be a non-empty string")
            continue
        if (start, end) not in spans_by_range:
            violations.append(f"{prefix} range {start}:{end} does not exactly match a numeric span")
            continue
        if ref not in declared:
            violations.append(f"{prefix} ref {ref!r} is undeclared")
            continue
        _, entry_error = _registry_entry(registry, ref)
        if entry_error:
            violations.append(f"{prefix} ref {ref!r}: {entry_error}")
            continue
        usable.append((start, end, index, binding))

    usable.sort(key=lambda item: (item[0], item[1], item[2]))
    overlapping_indices: set[int] = set()
    for position, (start, end, index, _) in enumerate(usable):
        for other_start, other_end, other_index, _ in usable[position + 1 :]:
            if other_start >= end:
                break
            if start < other_end and other_start < end:
                overlapping_indices.update({index, other_index})
                violations.append(f"claim {index} overlaps claim {other_index}")
    return {
        (start, end): claim
        for start, end, index, claim in usable
        if index not in overlapping_indices
    }


def _registry_entry(
    registry: Mapping[str, Mapping[str, Any]], ref: str
) -> tuple[Mapping[str, Any] | None, str | None]:
    """Return a minimally well-formed record; numeric values are checked later."""

    try:
        entry = registry.get(ref)
    except (AttributeError, TypeError):
        return None, "is absent from registry"
    if not isinstance(entry, Mapping):
        return None, "is absent from registry"
    missing = [key for key in ("value", "kind", "unit") if key not in entry]
    if missing:
        return None, f"registry entry is missing {', '.join(missing)}"
    if entry.get("kind") not in {"money", "percent", "units", "integer", "id", "date", "text"}:
        return None, f"registry entry has unsupported kind {entry.get('kind')!r}"
    if not isinstance(entry.get("unit"), str):
        return None, "registry entry unit must be a string"
    return entry, None


def _verify_span(span: _Span, ref: str, entry: Mapping[str, Any]) -> str | None:
    """Verify one claimed span against only its named registry entry."""

    kind = entry["kind"]
    if kind == "text":
        return f"numeric span {span.text!r} cannot bind text ref {ref!r}"

    if kind == "id":
        value = entry["value"]
        if not isinstance(value, str):
            return f"id ref {ref!r} has a non-string value"
        if span.surface != "id" or span.text != value:
            return f"identifier {span.text!r} does not exactly match ref {ref!r}"
        return None

    if kind == "date":
        value = entry["value"]
        if not isinstance(value, str):
            return f"date ref {ref!r} has a non-string value"
        if span.surface != "date" or not _valid_iso_date(span.text):
            return f"date {span.text!r} is invalid or unsupported"
        if span.text != value:
            return f"date {span.text!r} does not exactly match ref {ref!r}"
        return None

    expected, expected_error = _decimal_registry_value(entry["value"], ref)
    if expected_error:
        return expected_error
    assert expected is not None

    if kind == "money":
        if span.surface not in {"money", "compact", "integer"}:
            return f"{span.text!r} is not a supported money display for ref {ref!r}"
        actual, increment = _parse_money_or_compact(span)
        if actual is None or increment is None:
            return f"money display {span.text!r} is invalid"
        if abs(actual - expected) > increment / Decimal(2):
            return f"money display {span.text!r} does not match ref {ref!r}"
        return None

    if kind == "percent":
        if span.surface != "percent":
            return f"{span.text!r} is not a supported percent display for ref {ref!r}"
        actual, increment = _parse_percent(span.text)
        if actual is None or increment is None:
            return f"percent display {span.text!r} is invalid"
        if abs(actual - expected) > increment / Decimal(2):
            return f"percent display {span.text!r} does not match ref {ref!r}"
        return None

    # Contract quantities are integers.  Decimal displays, suffixes, booleans,
    # and currency displays cannot be coerced into an exact quantity.
    if span.surface != "integer":
        return f"{span.text!r} is not an integer display for ref {ref!r}"
    actual = _parse_integer(span.text)
    if actual is None or expected != expected.to_integral_value():
        return f"quantity ref {ref!r} requires an integer value"
    if actual != expected:
        return f"integer display {span.text!r} does not exactly match ref {ref!r}"
    return None


def _decimal_registry_value(value: Any, ref: str) -> tuple[Decimal | None, str | None]:
    """Convert JSON-compatible scalars without silently converting booleans."""

    if isinstance(value, bool):
        return None, f"ref {ref!r} has boolean numeric value"
    if isinstance(value, float) and not math.isfinite(value):
        return None, f"ref {ref!r} has non-finite numeric value"
    if not isinstance(value, (int, float, Decimal, str)):
        return None, f"ref {ref!r} has non-numeric value"
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None, f"ref {ref!r} has non-numeric value"
    if not decimal_value.is_finite():
        return None, f"ref {ref!r} has non-finite numeric value"
    return decimal_value, None


def _parse_money_or_compact(span: _Span) -> tuple[Decimal | None, Decimal | None]:
    """Parse USD/compact notation and return value plus display increment."""

    raw = span.text.strip().replace("\N{MINUS SIGN}", "-")
    negative_parentheses = raw.startswith("(") and raw.endswith(")")
    if negative_parentheses:
        raw = raw[1:-1].strip()
    raw = re.sub(r"(?i)US\$|USD|\$", "", raw)
    raw = re.sub(r"\s+", "", raw)
    if not raw:
        return None, None

    sign = Decimal(-1) if negative_parentheses else Decimal(1)
    signs = re.findall(r"[+-]", raw)
    if len(signs) > 1:
        return None, None
    if signs:
        if negative_parentheses:
            return None, None
        sign = Decimal(-1) if signs[0] == "-" else Decimal(1)
        raw = raw.replace(signs[0], "", 1)

    suffix = ""
    if raw and raw[-1:].lower() in {"k", "m", "b"}:
        suffix = raw[-1:].lower()
        raw = raw[:-1]
    if not re.fullmatch(_CORE, raw):
        return None, None
    number, precision = _decimal_and_precision(raw)
    if number is None:
        return None, None
    scale = {"": Decimal(1), "k": Decimal(1000), "m": Decimal(1_000_000), "b": Decimal(1_000_000_000)}[suffix]
    increment = scale * (Decimal(10) ** -precision)
    return sign * number * scale, increment


def _parse_percent(raw: str) -> tuple[Decimal | None, Decimal | None]:
    """Parse a displayed percentage into its contract decimal-fraction value."""

    value = raw.strip().replace("\N{MINUS SIGN}", "-")
    value = re.sub(r"(?i)(?:%|percent(?:age)?s?)\Z", "", value).strip()
    value = re.sub(r"\s+", "", value)
    sign = Decimal(1)
    if value[:1] in {"+", "-"}:
        if value[0] == "-":
            sign = Decimal(-1)
        value = value[1:]
    if not re.fullmatch(_CORE, value):
        return None, None
    number, precision = _decimal_and_precision(value)
    if number is None:
        return None, None
    increment = (Decimal(10) ** -precision) / Decimal(100)
    return sign * number / Decimal(100), increment


def _parse_integer(raw: str) -> Decimal | None:
    """Parse an ASCII signed integer display; grouped commas are accepted."""

    value = raw.strip().replace("\N{MINUS SIGN}", "-")
    sign = Decimal(1)
    if value[:1] in {"+", "-"}:
        if value[0] == "-":
            sign = Decimal(-1)
        value = value[1:]
    if not re.fullmatch(_INT_CORE, value):
        return None
    try:
        return sign * Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


def _decimal_and_precision(raw: str) -> tuple[Decimal | None, int]:
    """Parse a validated numeric core using Decimal and record shown precision."""

    precision = len(raw.rsplit(".", 1)[1]) if "." in raw else 0
    try:
        return Decimal(raw.replace(",", "")), precision
    except InvalidOperation:
        return None, precision


def _valid_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _where(span: _Span) -> str:
    return f"{span.start}:{span.end}"


__all__ = ["scan_text"]
