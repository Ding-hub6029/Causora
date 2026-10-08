"""Focused tests for the strict Day 4 numeric guardrail."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_day4.numeric import scan_text


REGISTRY = {
    "delta_tco": {"value": -419_000, "kind": "money", "unit": "USD"},
    "stockout_probability": {"value": 0.0867, "kind": "percent", "unit": "fraction"},
    "cash_outflow_p90": {"value": 420_000, "kind": "money", "unit": "USD"},
    "units": {"value": 26_000, "kind": "units", "unit": "units"},
    "option": {"value": "D1", "kind": "id", "unit": "id"},
    "decision_date": {"value": "2026-10-04", "kind": "date", "unit": "ISO-8601"},
}


def claim(text: str, displayed: str, ref: str) -> dict[str, object]:
    start = text.index(displayed)
    return {"start": start, "end": start + len(displayed), "ref": ref}


def test_public_tokens_are_narrow_and_must_be_declared() -> None:
    assert scan_text(
        "Cost {{delta_tco}} and risk {{stockout_probability}}.",
        registry=REGISTRY,
        declared_refs=["delta_tco", "stockout_probability"],
    ) == []

    undeclared = scan_text(
        "{{delta_tco}}", registry=REGISTRY, declared_refs=[]
    )
    assert any("not declared" in error for error in undeclared)

    for text in ("{{stockout_prob}}", "{{stockout_prob", "{{delta_tco:other}}"):
        errors = scan_text(text, registry=REGISTRY, declared_refs=["delta_tco"])
        assert errors, text
        assert any("token" in error or "brace" in error for error in errors)


def test_currency_is_bound_per_span_with_display_precision() -> None:
    text = "Cash is $420.0k, while the delta is −$419k."
    assert scan_text(
        text,
        registry=REGISTRY,
        declared_refs=["cash_outflow_p90", "delta_tco"],
        claims=[
            claim(text, "$420.0k", "cash_outflow_p90"),
            claim(text, "−$419k", "delta_tco"),
        ],
    ) == []

    wrong_same_word = "The cash P90 is $400k."
    errors = scan_text(
        wrong_same_word,
        registry=REGISTRY,
        declared_refs=["cash_outflow_p90"],
        claims=[claim(wrong_same_word, "$400k", "cash_outflow_p90")],
    )
    assert any("does not match" in error for error in errors)

    # One valid claim does not authorise a later, unrelated amount in the same
    # sentence.  This is the important no-blanket-sentence behaviour.
    extra = "The cash P90 is $420k, not $1."
    errors = scan_text(
        extra,
        registry=REGISTRY,
        declared_refs=["cash_outflow_p90"],
        claims=[claim(extra, "$420k", "cash_outflow_p90")],
    )
    assert any("unbound numeric span" in error and "$1" in error for error in errors)


def test_percent_uses_fraction_registry_value_and_display_precision() -> None:
    text = "The probability is 8.7%."
    assert scan_text(
        text,
        registry=REGISTRY,
        declared_refs=["stockout_probability"],
        claims=[claim(text, "8.7%", "stockout_probability")],
    ) == []

    wrong = "The probability is 7%."
    errors = scan_text(
        wrong,
        registry=REGISTRY,
        declared_refs=["stockout_probability"],
        claims=[claim(wrong, "7%", "stockout_probability")],
    )
    assert any("does not match" in error for error in errors)


def test_exact_integer_id_and_date_context() -> None:
    units = "Commitment is 26,000 units."
    assert scan_text(
        units,
        registry=REGISTRY,
        declared_refs=["units"],
        claims=[claim(units, "26,000", "units")],
    ) == []

    date = "Decision date: 2026-10-04."
    assert scan_text(
        date,
        registry=REGISTRY,
        declared_refs=["decision_date"],
        claims=[claim(date, "2026-10-04", "decision_date")],
    ) == []

    assert scan_text(
        "Recommend D1.", registry=REGISTRY, declared_refs=[], allowed_ids=["D1"]
    ) == []
    assert scan_text(
        "Recommend D2.", registry=REGISTRY, declared_refs=[], allowed_ids=["D1"]
    )

    wrong_date = "Decision date: 2026-10-05."
    errors = scan_text(
        wrong_date,
        registry=REGISTRY,
        declared_refs=["decision_date"],
        claims=[claim(wrong_date, "2026-10-05", "decision_date")],
    )
    assert any("does not exactly match" in error for error in errors)


def test_claim_ranges_are_exact_nonoverlapping_and_declared() -> None:
    text = "Cash is $420k."
    start = text.index("$420k")
    common = dict(registry=REGISTRY, declared_refs=["cash_outflow_p90"])

    # Pipeline compatibility: a positional [start, end, ref] binding remains
    # exactly as strict as the documented mapping form.
    assert scan_text(
        text,
        **common,
        claims=[start, start + len("$420k"), "cash_outflow_p90"],
    ) == []

    errors = scan_text(
        text,
        **common,
        claims=[{"start": start + 1, "end": start + 5, "ref": "cash_outflow_p90"}],
    )
    assert any("exactly match" in error for error in errors)

    errors = scan_text(
        text,
        **common,
        claims=[
            {"start": start, "end": start + 5, "ref": "cash_outflow_p90"},
            {"start": start, "end": start + 5, "ref": "cash_outflow_p90"},
        ],
    )
    assert any("overlaps" in error for error in errors)

    errors = scan_text(
        text,
        registry=REGISTRY,
        declared_refs=[],
        claims=[claim(text, "$420k", "cash_outflow_p90")],
    )
    assert any("undeclared" in error for error in errors)


def test_compact_tolerance_and_technical_identifier_context_are_narrow() -> None:
    rounded_registry = dict(REGISTRY)
    rounded_registry["cash_outflow_p90"] = {
        "value": 419_400,
        "kind": "money",
        "unit": "USD",
    }
    text = "Cash is 419k."
    assert scan_text(
        text,
        registry=rounded_registry,
        declared_refs=["cash_outflow_p90"],
        claims=[claim(text, "419k", "cash_outflow_p90")],
    ) == []  # 419k has a ±$500 displayed half-unit tolerance.

    assert scan_text("P90", registry=REGISTRY, declared_refs=[])
    assert scan_text("P90", registry=REGISTRY, declared_refs=[], allowed_ids=["P90"]) == []
    # A formula version is not an allowed-id loophole; formula verification is
    # deliberately a separate API/field concern.
    assert scan_text("tco-v1", registry=REGISTRY, declared_refs=[], allowed_ids=["tco-v1"])


def test_spelled_cjk_scientific_decimal_and_boolean_cannot_bypass() -> None:
    for text in (
        "five units",
        "二十 units",
        "１２％",
        "1e3 units",
        "26.0 units",
        "tco-v1",
    ):
        assert scan_text(text, registry=REGISTRY, declared_refs=[]), text

    boolean_registry = dict(REGISTRY)
    boolean_registry["units"] = {"value": True, "kind": "units", "unit": "units"}
    text = "Commitment is 1."
    errors = scan_text(
        text,
        registry=boolean_registry,
        declared_refs=["units"],
        claims=[claim(text, "1", "units")],
    )
    assert any("boolean" in error for error in errors)
