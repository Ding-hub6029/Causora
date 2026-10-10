"""Numerical claim audit. Local deterministic statements, never model quality."""
from pathlib import Path
import argparse
import hashlib
import json

import pytest
from agent_day4.numeric import scan_text

REGISTRY = {
    "cash": {"value": 12345, "kind": "money", "unit": "USD"},
    "probability": {"value": 0.087, "kind": "percent", "unit": "fraction"},
    "minimum": {"value": 15600, "kind": "units", "unit": "units"},
    "weeks": {"value": 104, "kind": "integer", "unit": "weeks"},
    "notice": {"value": "2026-10-07", "kind": "date", "unit": "date"},
}
CASES = [
    ("money_correct", "Cash is $12,345.", "$12,345", "cash", True),
    ("money_tampered", "Cash is $12,346.", "$12,346", "cash", False),
    ("currency_unit_wrong", "Cash is 12,345 USD.", "12,345 USD", "minimum", False),
    ("probability_correct", "Probability is 8.7%.", "8.7%", "probability", True),
    ("probability_value_wrong", "Probability is 87%.", "87%", "probability", False),
    ("probability_pp_wrong", "Probability is 8.7 percentage points.", "8.7 percentage points", "probability", False),
    ("probability_pp_short_wrong", "Probability is 8.7 pp.", "8.7 pp", "probability", False),
    ("probability_bare_wrong", "Probability is 0.087.", "0.087", "probability", False),
    ("units_correct", "Minimum is 15,600 units.", "15,600", "minimum", True),
    ("units_wrong", "Minimum is 15,599 units.", "15,599", "minimum", False),
    ("units_money_wrong", "Minimum is $15,600.", "$15,600", "minimum", False),
    ("weeks_correct", "Horizon is 104 weeks.", "104", "weeks", True),
    ("weeks_wrong", "Horizon is 103 weeks.", "103", "weeks", False),
    ("weeks_as_days_wrong", "Horizon is 104 days.", "104", "weeks", False),
    ("weeks_as_units_wrong", "Horizon is 104 units.", "104", "weeks", False),
    ("units_as_weeks_wrong", "Minimum is 15,600 weeks.", "15,600", "minimum", False),
    ("date_correct", "Notice is 2026-10-07.", "2026-10-07", "notice", True),
    ("date_wrong", "Notice is 2026-10-08.", "2026-10-08", "notice", False),
    ("unbound_number", "Cash is $12,345.", None, "cash", False),
]


def validate(case):
    ident, text, span, ref, expected = case
    claims = [] if span is None else [{"start": text.index(span), "end": text.index(span) + len(span), "ref": ref}]
    errors = scan_text(text, registry=REGISTRY, declared_refs=[ref], claims=claims)
    return {"caseId": ident, "input": {"text": text, "registry": REGISTRY, "declaredRefs": [ref], "claims": claims},
            "expectedNumericValid": expected, "actualNumericValid": not errors,
            "reasons": errors or ["exact field-bound number matches typed registry"],
            "expectedOutcomeMet": (not errors) == expected}


@pytest.mark.parametrize("case", CASES, ids=[case[0] for case in CASES])
def test_number_statement_is_bound_and_uses_correct_unit(case):
    row = validate(case)
    assert row["expectedOutcomeMet"], row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Never overwrite prior numerical evidence.")
    rows = [validate(case) for case in CASES]
    valid = sum(row["actualNumericValid"] for row in rows)
    positives = sum(row["expectedNumericValid"] for row in rows)
    result = {"kind": "OFFLINE_NUMERICAL_STATEMENTS_NOT_MODEL_PERFORMANCE", "networkCalls": 0,
              "sourceSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "sampleScope": "Nineteen author-visible deterministic statements, including intentional invalid statements; not unseen.",
              "numericValidationPassCount": valid, "checkedNumericStatementCount": len(rows),
              "validControlsAccepted": valid, "validControlCount": positives,
              "expectedOutcomesMet": sum(row["expectedOutcomeMet"] for row in rows),
              "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Numerical statements: {valid}/{len(rows)} pass numeric validation; {result['expectedOutcomesMet']}/{len(rows)} expected control outcomes met. Not model fidelity.")


if __name__ == "__main__":
    main()
