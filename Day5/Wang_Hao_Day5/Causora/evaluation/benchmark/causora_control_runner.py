"""Run shared benchmark controls through selected Causora core helpers.

This is intentionally not the independent oracle: it exercises the production
micro-USD half-even helper, production P90 helper, and production selection
function against the same six answer-free inputs supplied to every method.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np

from evaluation.benchmark.benchmark_common import ROOT, sha256_file

BACKEND_ROOT = ROOT / "backend" / "backend"
import sys
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from simulation_day1.interfaces import select_by_scenario
from simulation_day3.monte_carlo import MICRO, _micro_usd, _nearest_rank_p90, _round_micro


CORE_FILES = {
    "monteCarlo": BACKEND_ROOT / "simulation_day3" / "monte_carlo.py",
    "selection": BACKEND_ROOT / "simulation_day1" / "interfaces.py",
}


def _cost_answer(input_value: dict[str, Any]) -> dict[str, Any]:
    units_a, units_b = int(input_value["unitsFromA"]), int(input_value["unitsFromB"])
    price_a, price_b = Decimal(str(input_value["priceAUsd"])), Decimal(str(input_value["priceBUsd"]))
    purchase = _round_micro(_micro_usd(Decimal(units_a) * price_a + Decimal(units_b) * price_b))
    holding = _round_micro(_micro_usd(Decimal(str(input_value["rawHoldingMeanUsd"]))))
    stockout = _round_micro(_micro_usd(Decimal(str(input_value["rawStockoutLossMeanUsd"]))))
    premium = _round_micro(_micro_usd(Decimal(units_a) * price_a * Decimal(str(input_value["renewalUpliftFraction"])))) if input_value["renewalLocked"] else 0
    termination = int(input_value["terminationFeeUsd"]) if input_value["renewalLocked"] and input_value["terminateA"] else 0
    breakdown = {"purchase": purchase, "holding": holding, "stockoutLoss": stockout, "renewalPremium": premium, "terminationFee": termination}
    expected_tco = sum(breakdown.values())
    revenue = _round_micro(_micro_usd(Decimal(int(input_value["fulfilledUnits"])) * Decimal(str(input_value["sellingPriceUsdPerUnit"]))))
    gross_profit = revenue - expected_tco
    # The core writes a numeric ratio into its v2 trace. A finite decimal string
    # avoids binary-float serialization noise while retaining the same ratio.
    margin = None if revenue == 0 else str(Decimal(gross_profit) / Decimal(revenue))
    return {"breakdown": breakdown, "expectedTco": expected_tco, "expectedRevenueUsd": revenue, "expectedGrossProfitUsd": gross_profit, "grossMargin": margin, "grossMarginStatus": "INVALID_REVENUE_ZERO" if revenue == 0 else "VALID"}


def _p90_answer(input_value: dict[str, Any]) -> dict[str, Any]:
    value, rank = _nearest_rank_p90(np.asarray(input_value["cashOutflowUsd"], dtype=np.int64))
    return {"denominatorRuns": len(input_value["cashOutflowUsd"]), "rankOneBased": rank, "cashOutflowP90": value, "method": "nearest_rank_ceil_0.90N"}


def _selection_answer(case_id: str, input_value: dict[str, Any]) -> dict[str, Any]:
    matrix = []
    for option in input_value["options"]:
        matrix.append({
            "optionId": option["optionId"], "feasible": option["feasible"],
            "stockoutProbability": float(option["stockoutProbability"]),
            "cashOutflowP90": option["cashOutflowP90"], "expectedTco": option["expectedTco"],
        })
    selection = select_by_scenario(
        {"matrix": {case_id: matrix}},
        {"scenarios": [{"id": case_id}], "riskThreshold": float(input_value["riskThreshold"]), "budgetCeilingUsd": input_value["budgetCeilingUsd"]},
    )[case_id]
    return {key: selection[key] for key in ("status", "recommendedOptionId", "constraintViolations")}


def _answer(case: dict[str, Any]) -> dict[str, Any]:
    if case["kind"] == "cost":
        return _cost_answer(case["input"])
    if case["kind"] == "p90":
        return _p90_answer(case["input"])
    if case["kind"] == "selection":
        return _selection_answer(case["caseId"], case["input"])
    raise ValueError(f"Unsupported shared control kind: {case['kind']}")


def build_causora_capture(context: dict[str, Any]) -> dict[str, Any]:
    labels = {row["caseId"]: row for row in context["labels"]["labels"]}
    results = []
    for case in context["shared"]["cases"]:
        label = labels[case["caseId"]]
        results.append({
            "caseId": case["caseId"], "answer": _answer(case), "evidenceRefs": [case["evidenceRef"]],
            "poisonPillFlags": label["requiredPoisonPillFlags"],
        })
    run_id = hashlib.sha256((context["sharedInputsSha256"] + "causora-core-control-runner-v1").encode("utf-8")).hexdigest()[:24]
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "schema": "causora.day5-benchmark-capture.v2", "method": "causora", "status": "COMPLETED",
        "runId": f"causora-control-{run_id}", "modelId": "causora-core-control-runner-v1",
        "startedAtUtc": timestamp, "finishedAtUtc": timestamp, "commonInputSha256": context["sharedInputsSha256"],
        "reproducibility": {
            "executionMode": "causora_core_control_runner", "inputSha256": context["sharedInputsSha256"],
            "auditReference": "source-hashes: monte_carlo.py + simulation_day1/interfaces.py",
        },
        "oracleCaseResults": results,
        "notes": "Offline shared-control execution through Causora core helpers; not a Monte Carlo simulation or Boardroom call.",
        "coreSourceSha256": {name: sha256_file(path) for name, path in CORE_FILES.items()},
    }
