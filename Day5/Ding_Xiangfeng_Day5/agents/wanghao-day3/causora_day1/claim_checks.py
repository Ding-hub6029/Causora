"""Conservative Day 1 clause checks, not a general-purpose legal parser.

Only the five synthetic v4.1 clauses (plus auto-renew) are supported. Ambiguous
negative/exception context fails closed; human review is still mandatory.
"""
from __future__ import annotations

import re
import unicodedata
from math import isclose


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.translate(str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"',
                                        "\u201d": '"', "\u2013": "-", "\u2014": "-", "\u00a0": " "}))
    return re.sub(r"\s+", " ", text).strip()


PATTERNS = {
    "renewal_notice_days": re.compile(r"\bat\s+least\s+(?P<value>\d{1,4})\s+days?\s+before\s+renewal\b"),
    "auto_renew": re.compile(r"\b(?:agreement\s+)?automatically\s+renews?\b"),
    "renewal_term_months": re.compile(r"\bautomatically\s+renews?\s+for\s+(?P<value>\d{1,3})\s+months?\b"),
    "renewal_price_increase_pct": re.compile(r"\b(?P<value>\d{1,3}(?:\.\d+)?)\s*%\s+higher\s+unit\s+price\b"),
    "min_purchase_share_A": re.compile(r"\bminimum\s+purchase\s+commitment\s+equal\s+to\s+(?P<value>\d{1,3}(?:\.\d+)?)\s*%\s+of\s+forecast\s+demand\b"),
    # Consume the COMPLETE number, including decimals, rather than matching $25,000 as a prefix.
    "termination_fee": re.compile(r"\b(?:fixed\s+)?termination\s+fee\s+of\s+\$\s*(?P<value>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?)(?![\d,]|\.\d)"),
}

NEGATIVE = {
    "renewal_notice_days": r"\b(?:no\s+(?:written\s+)?notice\s+(?:period|requirement)|notice\s+(?:period|requirement)\s+(?:is\s+)?waived|does\s+not\s+require\s+(?:written\s+)?notice)\b",
    "auto_renew": r"\b(?:shall|will|does|do|may)\s+not\s+automatically\s+renew\b|\bno\s+automatic\s+renewal\b",
    "renewal_term_months": r"\b(?:shall|will|does|do|may)\s+not\s+automatically\s+renew\b|\bno\s+automatic\s+renewal\b",
    "renewal_price_increase_pct": r"\b(?:not|never|without)\b(?:\W+\w+){0,4}\W+\d+(?:\.\d+)?\s*%\s+higher\b|\b(?:no\s+(?:price\s+increase|price\s+uplift)|(?:price\s+)?(?:increase|uplift)\s+is\s+waived)\b",
    "min_purchase_share_A": r"\b(?:no\s+minimum\s+purchase(?:\s+commitment)?|minimum\s+purchase\s+commitment\s+(?:is\s+)?waived|minimum\s+purchase\s+commitment\s+does\s+not\s+apply|not\s+subject\s+to\s+(?:the\s+)?minimum\s+purchase)\b",
    "termination_fee": r"\b(?:no\s+(?:early\s+exit\s+|termination\s+)?fee|(?:this\s+|the\s+)?fee\s+is\s+waived|termination\s+fee\s+(?:does\s+not\s+apply|is\s+waived)|without\s+(?:a\s+)?termination\s+fee)\b",
}
GLOBAL_EXCEPTION = re.compile(r"\b(?:renewal\s+(?:clause|terms?)\s+do(?:es)?\s+not\s+apply\s+to\s+(?:the\s+)?current\s+customer|not\s+applicable\s+to\s+(?:the\s+)?current\s+customer|waived\s+for\s+(?:the\s+)?current\s+customer)\b")
# Do not "resolve" open-ended legal exceptions with a keyword regex. A human
# must assess any such clause. The known v4.1 notice condition ("If written
# notice is not received ...") is handled as a controlled fixture phrase.
UNRESOLVED_QUALIFIER = re.compile(
    r"\b(?:unless|except|subject\s+to|provided\s+that|notwithstanding|only\s+if|"
    r"otherwise\s+agreed|may\s+be\s+waived|waivable|waived\s+in\s+writing|"
    r"does\s+not\s+apply)\b"
)
UNITS = {
    "renewal_notice_days": "days", "auto_renew": "boolean", "renewal_term_months": "months",
    "renewal_price_increase_pct": "percent", "min_purchase_share_A": "share", "termination_fee": "USD",
}


def supported_claim(field: str, value: int | float | bool, unit: str, quote: str, *, context: str = "") -> bool:
    """Check semantic wording, complete numeric tokens and contradictory context.

    `quote` must itself support the typed value. `context` is source-side page text;
    if it contains a supported exception we do not silently approve a nearby clause.
    """
    if field not in PATTERNS or unit != UNITS[field]:
        return False
    if field == "auto_renew":
        if type(value) is not bool or value is not True:
            return False
    elif field in {"renewal_notice_days", "renewal_term_months", "termination_fee"}:
        if type(value) is not int or value < 0 or value > 1_000_000_000:
            return False
        if field == "renewal_notice_days" and not 1 <= value <= 3650:
            return False
        if field == "renewal_term_months" and not 1 <= value <= 120:
            return False
    elif field == "renewal_price_increase_pct":
        if type(value) not in (int, float) or not 0 <= value <= 100:
            return False
    elif field == "min_purchase_share_A":
        if type(value) is not float or not 0 <= value <= 1:
            return False

    q = normalize(quote)
    content = normalize(quote + " " + context)
    if (GLOBAL_EXCEPTION.search(content) or UNRESOLVED_QUALIFIER.search(content)
            or re.search(NEGATIVE[field], content)):
        return False
    match = PATTERNS[field].search(q)
    if not match:
        return False
    if field == "auto_renew":
        return True
    token = match.group("value")
    if field == "termination_fee":
        number = float(token.replace(",", ""))
        return number.is_integer() and int(number) == value
    number = float(token)
    if field == "min_purchase_share_A":
        number /= 100
    return isclose(number, value, rel_tol=0, abs_tol=1e-10)
