#!/usr/bin/env python3
"""Independent, pure-Python Day 5 arithmetic oracle.

This module is intentionally isolated: it imports neither the Causora simulation
engine nor its data models.  Frozen controls are explicit Decimal arithmetic used
to audit the public cost/constraint semantics, not a second Monte Carlo engine.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal, ROUND_HALF_EVEN
from math import ceil
from pathlib import Path
from typing import Any

ZERO = Decimal("0")


def money(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"Invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise ValueError("Non-finite decimals are not allowed")
    return result


def whole_usd(value: Any) -> int:
    """Round a decimal value to whole USD using explicit banker rounding."""
    return int(money(value).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


def cost_control(input_value: dict[str, Any]) -> dict[str, Any]:
    """Compute five displayed TCO lines from independently specified test inputs."""
    units_a = int(input_value["unitsFromA"])
    units_b = int(input_value["unitsFromB"])
    if units_a < 0 or units_b < 0:
        raise ValueError("Purchased units must be non-negative")
    locked = bool(input_value["renewalLocked"])
    terminate = bool(input_value["terminateA"])
    purchase = whole_usd(money(units_a) * money(input_value["priceAUsd"]) + money(units_b) * money(input_value["priceBUsd"]))
    holding = whole_usd(input_value["rawHoldingMeanUsd"])
    stockout = whole_usd(input_value["rawStockoutLossMeanUsd"])
    renewal = whole_usd(money(units_a) * money(input_value["priceAUsd"]) * money(input_value["renewalUpliftFraction"])) if locked else 0
    termination = int(input_value["terminationFeeUsd"]) if locked and terminate else 0
    if termination < 0:
        raise ValueError("Termination fee must be non-negative")
    components = {
        "purchase": purchase,
        "holding": holding,
        "stockoutLoss": stockout,
        "renewalPremium": renewal,
        "terminationFee": termination,
    }
    expected_tco = sum(components.values())
    revenue = whole_usd(money(input_value["fulfilledUnits"]) * money(input_value["sellingPriceUsdPerUnit"]))
    gross_profit = revenue - expected_tco
    return {
        "breakdown": components,
        "expectedTco": expected_tco,
        "expectedRevenueUsd": revenue,
        "expectedGrossProfitUsd": gross_profit,
        "grossMargin": None if revenue == 0 else str(money(gross_profit) / money(revenue)),
        "grossMarginStatus": "INVALID_REVENUE_ZERO" if revenue == 0 else "VALID",
    }


def p90_control(input_value: dict[str, Any]) -> dict[str, Any]:
    values = input_value["cashOutflowUsd"]
    if not isinstance(values, list) or not values:
        raise ValueError("cashOutflowUsd must be a non-empty list")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
        raise ValueError("cashOutflowUsd values must be non-negative whole USD")
    rank = ceil(0.9 * len(values))
    return {"denominatorRuns": len(values), "rankOneBased": rank, "cashOutflowP90": sorted(values)[rank - 1], "method": "nearest_rank_ceil_0.90N"}


def selection_control(input_value: dict[str, Any]) -> dict[str, Any]:
    """Independently apply the documented feasibility/risk/cash rule in option order."""
    threshold = money(input_value["riskThreshold"])
    ceiling = int(input_value["budgetCeilingUsd"])
    if threshold < ZERO or threshold > Decimal("1") or ceiling < 0:
        raise ValueError("Invalid selection threshold or cash ceiling")
    options = input_value["options"]
    expected_order = ["D0", "D1", "D2"]
    if not isinstance(options, list) or [item.get("optionId") for item in options] != expected_order:
        raise ValueError("Selection control requires D0, D1, D2 in canonical order")
    violations: list[dict[str, str]] = []
    eligible: list[dict[str, Any]] = []
    for option in options:
        codes: list[str] = []
        if option.get("feasible") is not True:
            codes.append("infeasible")
        if money(option["stockoutProbability"]) > threshold:
            codes.append("stockout_threshold")
        if int(option["cashOutflowP90"]) > ceiling:
            codes.append("cash_ceiling")
        for code in codes:
            violations.append({"optionId": option["optionId"], "code": code})
        if not codes:
            eligible.append({"optionId": option["optionId"], "expectedTco": int(option["expectedTco"])})
    eligible.sort(key=lambda item: (item["expectedTco"], item["optionId"]))
    return {
        "status": "selected" if eligible else "no_feasible_option",
        "recommendedOptionId": eligible[0]["optionId"] if eligible else None,
        "constraintViolations": violations,
    }


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    kind = case.get("kind")
    if kind == "cost":
        actual = cost_control(case["input"])
    elif kind == "p90":
        actual = p90_control(case["input"])
    elif kind == "selection":
        actual = selection_control(case["input"])
    else:
        raise ValueError(f"Unsupported oracle case kind: {kind!r}")
    expected = case["expected"]
    return {"id": case["id"], "kind": kind, "status": "PASS" if actual == expected else "FAIL", "expected": expected, "actual": actual}


def evaluate_document(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("schema") != "causora.independent-oracle-controls.v1":
        raise ValueError("Unsupported oracle fixture schema")
    rows = [evaluate_case(case) for case in document.get("cases", [])]
    return {
        "schema": "causora.independent-oracle-result.v1",
        "oracleImplementation": "pure-python-decimal-no-simulation-imports",
        "caseCount": len(rows),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "failed": sum(row["status"] != "PASS" for row in rows),
        "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = json.loads(args.input.read_text(encoding="utf-8"))
    result = evaluate_document(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
