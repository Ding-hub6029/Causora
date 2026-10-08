"""Day 3 *internal* stochastic 104-week Option × Scenario calculation.

The computed numbers are real Monte Carlo results on synthetic source inputs,
not a public SimulateSuccess. Human contract review and modeling-policy approval
remain required before a live /api/simulate success can be served.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_EVEN
from math import ceil
from pathlib import Path

import numpy as np

from simulation_day1.interfaces import (
    FROZEN_MOCK_SHA256, calculate_deltas, select_by_scenario, validate_request,
)
from simulation_day1.wire_models import SimulateRequest
from simulation_day2.deterministic import _lead_days, read_source_manifest
from simulation_day2.models import WeekTrace
from simulation_day3.models import MonteCarloPreview
from simulation_day3.policy import Day3Policy, OperatingPolicy

ROOT = Path(__file__).resolve().parents[1]
WEEKS = 104
MICRO = 1_000_000
COMPONENTS = ("purchase", "holding", "stockoutLoss", "renewalPremium", "terminationFee")
OPTIONS = ("D0", "D1", "D2")
SCENARIOS = ("baseline", "demand-drop", "lead-stress")


def _micro_usd(value: Decimal) -> int:
    amount = value * MICRO
    if amount != amount.to_integral_value():
        raise ValueError("monetary input requires more than six USD decimal places; no implicit rounding")
    return int(amount)


def _round_micro(raw: np.ndarray | int) -> np.ndarray | int:
    """Nonnegative micro-USD -> whole USD, exactly half-even (not float rounding)."""
    array = np.asarray(raw, dtype=np.int64)
    whole, rest = np.divmod(array, MICRO)
    rounded = whole + ((rest > MICRO // 2) | ((rest == MICRO // 2) & ((whole & 1) == 1)))
    return int(rounded) if rounded.ndim == 0 else rounded


def _nearest_rank_p90(values: np.ndarray) -> tuple[int, int]:
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("P90 requires actual trial cash values")
    rank = ceil(Decimal(9) * len(values) / Decimal(10))
    return int(np.partition(values, rank - 1)[rank - 1]), rank


def _source_and_request(request: dict, policy: Day3Policy, project_root: Path) -> tuple[dict, dict, dict, dict[str, list[int]], dict[str, Decimal]]:
    parsed = SimulateRequest.model_validate_json(json.dumps(request, ensure_ascii=False, allow_nan=False))
    manifest = read_source_manifest(project_root)  # pins the whole manifest, all five raw hashes, all 104 CSV rows
    raw = (project_root / "demo_data/causora_day1_mock.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != FROZEN_MOCK_SHA256:
        raise ValueError("the team's v4.1 mock changed without an agreed dataVersion")
    contract = json.loads(raw.decode("utf-8"))["contract"]
    validate_request(request, dataset_id="ds-001", contract=contract, allow_unfrozen_scenarios=True)
    if parsed.datasetId != "ds-001" or policy.operatingPolicy.horizonStartDate.isoformat() != contract["renewalDate"]:
        raise ValueError("named synthetic dataset and renewal-date opening inventory required")
    if any(s["demandUnits24m"] > 1_000_000 for s in request["scenarios"]):
        raise ValueError("trial demand exceeds safe internal arithmetic range")
    history = manifest["historicalDemand"]["observations"]
    leads, prices = _lead_days(manifest["supplierDelivery"]["orders"])
    if len(history) < 52 or len(leads["A"]) < 30:
        raise ValueError("insufficient historical weekly demand or Supplier A POs for an empirical bootstrap")
    if len(leads["B"]) >= 30:
        raise ValueError("B has enough POs; re-review its distribution before using a user-assumed fallback")
    if policy.operatingPolicy.targetStockUnits <= policy.operatingPolicy.safetyStockUnits:
        raise ValueError("target stock must exceed explicit safety stock")
    return manifest, contract, parsed.model_dump(mode="json"), leads, prices


def _draw_master(*, history: list[dict], leads_a: list[int], policy: Day3Policy, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """Draw once; same external-world trials across all options and scenarios."""
    generator = np.random.Generator(np.random.PCG64(seed))
    n = policy.monteCarloRuns
    hist = np.asarray([row["unitsDemanded"] for row in history], dtype=np.int64)
    a = np.asarray(leads_a, dtype=np.int64)
    demand_idx = generator.integers(0, len(hist), size=(n, WEEKS), dtype=np.int32)
    lead_a_idx = generator.integers(0, len(a), size=(n, WEEKS), dtype=np.int32)
    triangular = policy.supplierBLeadFallback
    # B has only twelve POs; no claim that these illustrative parameters were
    # estimated or human-approved from the small sample.
    lead_b_days = np.clip(np.rint(generator.triangular(
        triangular.minDays, triangular.modeDays, triangular.maxDays,
        size=(n, WEEKS))), triangular.minDays, triangular.maxDays).astype(np.int64)
    sampled_history = hist[demand_idx]
    lead_a_days = a[lead_a_idx]
    digest = hashlib.sha256(demand_idx.tobytes() + lead_a_idx.tobytes() + lead_b_days.tobytes()).hexdigest()
    return sampled_history, lead_a_days, lead_b_days, digest


def _simulate_cell(*, scenario: dict, option: dict, contract: dict,
                   policy: OperatingPolicy, demands: np.ndarray,
                   leads_a: np.ndarray, leads_b: np.ndarray,
                   prices: dict[str, Decimal], runs: int,
                   expected_lead_days_a: Decimal, expected_lead_days_b: Decimal) -> tuple[dict, dict]:
    """Every trial advances its own inventory, due orders, commitment and cost."""
    if demands.shape != (runs, WEEKS) or leads_a.shape != demands.shape or leads_b.shape != demands.shape:
        raise ValueError("all Monte Carlo demand/lead draws need one independent 104-week path per trial")
    shares = Decimal(str(option["shareA"]))
    lead_factor_a = Decimal(str(scenario["leadTimeMultiplier"]))
    lead_factor_b = lead_factor_a if policy.leadStressAppliesTo == "all_suppliers" else Decimal(1)
    # The reorder policy must not drift with the seed or the number of trials:
    # use A's exact 36-PO historical mean and the explicit *theoretical* B
    # triangular mean. Random lead draws only influence physical arrivals.
    mean_weeks = (shares * expected_lead_days_a * lead_factor_a +
                  (Decimal(1) - shares) * expected_lead_days_b * lead_factor_b) / Decimal(7)
    point = ceil(Decimal(scenario["demandUnits24m"]) / WEEKS * mean_weeks + policy.safetyStockUnits)
    if policy.targetStockUnits <= point:
        raise ValueError(f"targetStockUnits must exceed reorder point {point} for {scenario['id']}/{option['id']}")
    fixed_a = contract["minPurchaseUnitsA"] if option["id"] == "D1" else None
    fixed_b = contract["lockedForecastUnits24m"] - fixed_a if fixed_a is not None else None
    min_a = contract["minPurchaseUnitsA"] if contract["renewalLocked"] and not option["terminateA"] else 0
    on_hand = np.full(runs, policy.openingInventoryUnits, dtype=np.int64)
    # Arrival after week 104 stays in ordered-minus-delivered/on-order, but not in
    # the 104-week holding or service totals. No giant arrays for extreme delays.
    due_a, due_b = np.zeros((WEEKS, runs), dtype=np.int64), np.zeros((WEEKS, runs), dtype=np.int64)
    ordered_a, ordered_b = np.zeros(runs, dtype=np.int64), np.zeros(runs, dtype=np.int64)
    delivered_a, delivered_b = np.zeros(runs, dtype=np.int64), np.zeros(runs, dtype=np.int64)
    filled_total, lost_total, demand_total = (np.zeros(runs, dtype=np.int64) for _ in range(3))
    purchase_micro, holding_micro, loss_micro, premium_micro = (np.zeros(runs, dtype=np.int64) for _ in range(4))
    price_a, price_b = (_micro_usd(prices[s]) for s in ("A", "B"))
    selling_price = _micro_usd(policy.sellingPriceUsdPerUnit)
    premium_per_a = _micro_usd(prices["A"] * Decimal(str(contract["renewalPriceIncreasePct"])))
    hold_half = _micro_usd(policy.holdingCostUsdPerUnitWeek / 2)
    loss_per_unit = _micro_usd(policy.lostContributionMarginUsdPerUnit)
    fee_usd = contract["terminationFeeUsd"] if contract["renewalLocked"] and option["terminateA"] else 0
    trace = []
    draw_indices = np.arange(runs)
    for t in range(WEEKS):
        opening = on_hand.copy()
        arrival_a, arrival_b = due_a[t], due_b[t]
        delivered_a += arrival_a
        delivered_b += arrival_b
        available = on_hand + arrival_a + arrival_b
        demand_week = demands[:, t]
        filled = np.minimum(demand_week, available)
        shortage = demand_week - filled
        on_hand = available - filled
        filled_total += filled
        lost_total += shortage
        demand_total += demand_week
        before_order = ordered_a + ordered_b - delivered_a - delivered_b
        position = on_hand + before_order
        reorder = np.where(position <= point, np.maximum(0, policy.targetStockUnits - position), 0)
        if fixed_a is not None:
            need_a = np.maximum(0, (fixed_a * (t + 1) + WEEKS - 1) // WEEKS - ordered_a)
            need_b = np.maximum(0, (fixed_b * (t + 1) + WEEKS - 1) // WEEKS - ordered_b)
            qty = np.minimum(np.maximum(reorder, need_a + need_b), fixed_a + fixed_b - ordered_a - ordered_b)
            low = np.maximum(0, qty - (fixed_b - ordered_b))
            high = np.minimum(qty, fixed_a - ordered_a)
            if np.any(low > high):
                raise AssertionError("fixed purchased-unit quota impossible")
            a_qty = np.clip(np.rint(qty * float(shares)).astype(np.int64), low, high)
            b_qty = qty - a_qty
        else:
            commitment = np.maximum(0, (min_a * (t + 1) + WEEKS - 1) // WEEKS - ordered_a)
            qty = np.maximum(reorder, commitment)
            a_qty = qty if option["id"] == "D0" else np.zeros(runs, dtype=np.int64)
            b_qty = qty - a_qty
        week_purchase = a_qty * price_a + b_qty * price_b
        week_hold = (available + on_hand) * hold_half
        week_loss = shortage * loss_per_unit
        week_premium = a_qty * premium_per_a if contract["renewalLocked"] else np.zeros(runs, dtype=np.int64)
        purchase_micro += week_purchase
        holding_micro += week_hold
        loss_micro += week_loss
        premium_micro += week_premium
        a_weeks = np.maximum(1, np.ceil(leads_a[:, t].astype(float) * float(lead_factor_a) / 7).astype(np.int64))
        b_weeks = np.maximum(1, np.ceil(leads_b[:, t].astype(float) * float(lead_factor_b) / 7).astype(np.int64))
        at_a, at_b = t + a_weeks, t + b_weeks
        mask_a, mask_b = (a_qty > 0) & (at_a < WEEKS), (b_qty > 0) & (at_b < WEEKS)
        np.add.at(due_a, (at_a[mask_a], draw_indices[mask_a]), a_qty[mask_a])
        np.add.at(due_b, (at_b[mask_b], draw_indices[mask_b]), b_qty[mask_b])
        ordered_a += a_qty
        ordered_b += b_qty
        # Trial zero is an auditable realised path. Aggregate statistics below
        # use ALL trials; this row is never passed off as an expected path.
        row = {"week": t + 1, "startDate": (policy.horizonStartDate + timedelta(weeks=t)).isoformat(),
               "openingUnits": int(opening[0]), "arrivalsA": int(arrival_a[0]), "arrivalsB": int(arrival_b[0]),
               "demandUnits": int(demand_week[0]), "availableUnits": int(available[0]),
               "fulfilledUnits": int(filled[0]), "lostUnits": int(shortage[0]), "endingUnits": int(on_hand[0]),
               "onOrderUnitsBefore": int(before_order[0]), "inventoryPositionBefore": int(position[0]),
               "reorderPointUnits": int(point), "orderedA": int(a_qty[0]), "orderedB": int(b_qty[0]),
               "sampledLeadDaysA": int(leads_a[0, t]) if a_qty[0] else None,
               "sampledLeadDaysB": int(leads_b[0, t]) if b_qty[0] else None,
               "plannedArrivalWeekA": int(at_a[0] + 1) if a_qty[0] else None,
               "plannedArrivalWeekB": int(at_b[0] + 1) if b_qty[0] else None,
               "onOrderUnitsAfter": int((ordered_a + ordered_b - delivered_a - delivered_b)[0]),
               "holdingRawUsd": str(Decimal(int(week_hold[0])) / MICRO),
               "stockoutLossRawUsd": str(Decimal(int(week_loss[0])) / MICRO),
               "basePurchaseRawUsd": str(Decimal(int(week_purchase[0])) / MICRO),
               "renewalPremiumRawUsd": str(Decimal(int(week_premium[0])) / MICRO),
               "terminationFeeRawUsd": str(fee_usd if t == 0 else 0)}
        WeekTrace.model_validate_json(json.dumps(row, allow_nan=False))
        trace.append(row)
    if fixed_a is not None and (np.any(ordered_a != fixed_a) or np.any(ordered_b != fixed_b)):
        raise AssertionError("each D1 trial must actually purchase exactly 15,600 A + 10,400 B")
    feasible = bool(np.all(ordered_a >= min_a) and (fixed_a is None or np.all(ordered_b == fixed_b)))
    fee_micro = np.full(runs, fee_usd * MICRO, dtype=np.int64)
    raw_cost = {"purchase": purchase_micro, "holding": holding_micro, "stockoutLoss": loss_micro,
                "renewalPremium": premium_micro, "terminationFee": fee_micro}
    rounded_runs = {k: _round_micro(v) for k, v in raw_cost.items()}
    cash_run = sum(rounded_runs[k] for k in ("purchase", "holding", "renewalPremium", "terminationFee"))
    p90, rank = _nearest_rank_p90(cash_run)
    displayed_a = int(np.rint(np.mean(ordered_a)))
    displayed_b = int(np.rint(np.mean(ordered_b)))
    # Integer purchased units are required by v1 and Ding's cross-language
    # purchase validation. Reconcile the public-shaped purchase/premium with
    # those units; retain exact per-trial means below for auditing the rounding.
    purchase = int((Decimal(displayed_a) * prices["A"] + Decimal(displayed_b) * prices["B"]).quantize(
        Decimal(1), rounding=ROUND_HALF_EVEN))
    premium = (int((Decimal(displayed_a) * prices["A"] * Decimal(str(contract["renewalPriceIncreasePct"]))).quantize(
        Decimal(1), rounding=ROUND_HALF_EVEN)) if contract["renewalLocked"] else 0)
    breakdown = {"purchase": purchase, "holding": _round_micro(int(np.rint(np.mean(holding_micro)))),
                 "stockoutLoss": _round_micro(int(np.rint(np.mean(loss_micro)))),
                 "renewalPremium": premium, "terminationFee": fee_usd}
    expected_tco = sum(breakdown.values())
    raw_revenue_micro = filled_total * selling_price
    expected_revenue = _round_micro(int(np.rint(np.mean(raw_revenue_micro))))
    expected_gross_profit = expected_revenue - expected_tco
    gross_margin = expected_gross_profit / expected_revenue if expected_revenue else None
    stockout_count = int(np.count_nonzero(lost_total))
    total_demand = int(np.sum(demand_total))
    total_filled = int(np.sum(filled_total))
    cell = {"optionId": option["id"], "feasible": feasible, "expectedTco": expected_tco,
            "stockoutProbability": stockout_count / runs,
            "serviceLevel": total_filled / total_demand if total_demand else 1.0,
            "cashOutflowP90": p90, "breakdown": breakdown,
            "unitsFromA": displayed_a, "unitsFromB": displayed_b,
            "tone": "neutral" if feasible else "risk"}
    math_trace = {"scenarioId": scenario["id"], "optionId": option["id"], "sampleRunIndex": 0,
                  "sampleRunNote": "One realised stochastic path, not the expectation or a public v1 weekly trace",
                  "weeks": trace, "reorderPointUnits": point,
                  "leadTimeSourceA": "historical-fit: 36 synthetic POs",
                  "leadTimeSourceB": "user-assumed: explicit triangular input; 12 synthetic POs below threshold",
                  "stockoutRuns": stockout_count, "monteCarloRuns": runs,
                  "fulfilledUnitsAllRuns": total_filled, "demandUnitsAllRuns": total_demand,
                  "p90CashRankOneBased": rank, "cashOutflowP90Usd": p90,
                  "meanOrderedAExact": str(Decimal(int(np.sum(ordered_a))) / runs),
                  "meanOrderedBExact": str(Decimal(int(np.sum(ordered_b))) / runs),
                  "rawMeanCostsUsd": {k: str(Decimal(int(np.sum(v))) / (MICRO * runs)) for k, v in raw_cost.items()},
                  "displayedWholeUsdBreakdown": breakdown,
                  "rawMeanRevenueUsd": str(Decimal(int(np.sum(raw_revenue_micro))) / (MICRO * runs)),
                  "expectedRevenueUsd": expected_revenue,
                  "expectedGrossProfitUsd": expected_gross_profit,
                  "grossMargin": gross_margin,
                  "grossMarginStatus": "VALID" if expected_revenue else "INVALID_REVENUE_ZERO",
                  "summaryRoundingRule": "Round mean A/B units to integers half-even; compute base purchase and A premium from those integers; other component means half-even USD. P90 uses rounded per-run cash lines.",
                  "runCashSha256": hashlib.sha256(cash_run.tobytes()).hexdigest()}
    return cell, math_trace


def run_unapproved_monte_carlo(request: dict, policy_data: dict, *, project_root: Path = ROOT) -> dict:
    """Produce a typed NON-PUBLIC preview; no approved/HTTP 200 path exists here."""
    policy = Day3Policy.model_validate_json(json.dumps(policy_data, ensure_ascii=False, allow_nan=False))
    manifest, contract, parsed_request, leads, prices = _source_and_request(request, policy, project_root)
    historical = manifest["historicalDemand"]["observations"]
    sampled_history, lead_a, lead_b, draws_sha = _draw_master(
        history=historical, leads_a=leads["A"], policy=policy, seed=request["seed"])
    by_scenario = {s["id"]: s for s in request["scenarios"]}
    by_option = {o["id"]: o for o in request["options"]}
    matrix, formula_traces = {}, {}
    historical_total = manifest["historicalDemand"]["totalUnits"]
    expected_lead_a = Decimal(sum(leads["A"])) / Decimal(len(leads["A"]))
    triangle = policy.supplierBLeadFallback
    expected_lead_b = Decimal(triangle.minDays + triangle.modeDays + triangle.maxDays) / Decimal(3)
    for sid in SCENARIOS:
        scenario = by_scenario[sid]
        factor = scenario["demandUnits24m"] / historical_total
        demand = np.maximum(0, np.rint(sampled_history.astype(np.float64) * factor)).astype(np.int64)
        rows, traces = [], {}
        for oid in OPTIONS:
            cell, math_trace = _simulate_cell(
                scenario=scenario, option=by_option[oid], contract=contract,
                policy=policy.operatingPolicy, demands=demand, leads_a=lead_a,
                leads_b=lead_b, prices=prices, runs=policy.monteCarloRuns,
                expected_lead_days_a=expected_lead_a, expected_lead_days_b=expected_lead_b)
            rows.append(cell)
            traces[oid] = math_trace
        matrix[sid], formula_traces[sid] = rows, traces
    code_hashes = {file: hashlib.sha256((Path(__file__).parent / file).read_bytes()).hexdigest()
                   for file in ("monte_carlo.py", "models.py", "policy.py")}
    input_digest = hashlib.sha256(json.dumps({"request": parsed_request, "policy": policy.model_dump(mode="json"),
        "manifestSha256": hashlib.sha256((project_root / "simulation_day1/demo_inputs_v1.json").read_bytes()).hexdigest(),
        "drawsSha256": draws_sha, "code": code_hashes, "numpyVersion": np.__version__},
        sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    # Internal metrics only: do not emit SimulateResponse, simulationId or a
    # recommendedOptionId. The shared response DTO alone cannot enforce
    # approval status, so a ready-to-wrap testOnlyData would be unsafe.
    computed = {"matrix": matrix}
    deltas = calculate_deltas(computed, request["scenarios"])
    selections = select_by_scenario(computed, request)
    screenings = {}
    for sid in SCENARIOS:
        violations = selections[sid]["constraintViolations"]
        failed = {v["optionId"] for v in violations}
        screenings[sid] = {"scenarioId": sid, "status": "screening_only_unapproved",
            "eligibleOptionIds": [oid for oid in OPTIONS if oid not in failed],
            "constraintViolations": violations}
    preview = {"kind": "CAUSORA_DAY3_INTERNAL_MONTE_CARLO_PREVIEW_V1",
            "internalSchemaVersion": "jinzhu.mc-preview.v1",
            "referencedContractVersion": "causora.contract.v1",
            "status": "UNREVIEWED_SYNTHETIC_TEST_ONLY_NO_PUBLIC_SUCCESS",
            "decisionReady": False,
            "reviewStatus": "PENDING_11_HUMAN_REVIEW_ROWS",
            "policyStatus": policy.policyStatus,
            "sourceDataVersion": manifest["dataVersion"],
            "formulaVersion": "tco-v1", "previewId": "mc-preview-" + input_digest[:20],
            "seed": request["seed"], "weeks": WEEKS,
            "monteCarloRuns": policy.monteCarloRuns,
            "distributionProvenance": {"demand": "historical-fit: 104 synthetic weekly observations",
                "supplierA": f"historical-fit: {len(leads['A'])} synthetic POs",
                "supplierB": "user-assumed triangular; 12 synthetic POs below 30-PO threshold",
                "supplierBParameters": policy.supplierBLeadFallback.model_dump(mode="json"),
                "sellingPrice": "user-assumed unapproved", "unitPrices": "frozen synthetic supplier_delivery_history.xlsx",
                "randomGenerator": f"numpy.PCG64 / numpy {np.__version__}", "drawsSha256": draws_sha,
                "cashP90": policy.cashP90Method},
            "inputHashesSha256": {key: manifest[key]["sourceSha256"] for key in
                ("historicalDemand", "supplierDelivery", "openingInventory", "noticeRegister", "contractAssumptions")},
            "intermediateManifestSha256": hashlib.sha256((project_root / "simulation_day1/demo_inputs_v1.json").read_bytes()).hexdigest(),
            "engineSourceSha256": code_hashes,
            "note": "Only a mathematical test preview. Screening lists eligible IDs, never a recommended winner. This is NOT a SimulateResponse/ApiSuccess, public /api/simulate 200, or approval.",
            "unitPricesUsd": {s: float(prices[s]) for s in ("A", "B")},
            "computedMatrix": matrix, "decisionDeltas": deltas,
            "constraintScreening": screenings, "formulaTraces": formula_traces}
    return MonteCarloPreview.model_validate_json(
        json.dumps(preview, ensure_ascii=False, allow_nan=False)).model_dump(mode="json")


def run_reviewed_monte_carlo(request: dict, policy_data: dict, *, reviewed_contract: dict,
                              reviewed_data_version: str, project_root: Path = ROOT) -> dict:
    """Run the physical 104-week engine with externally verified inputs.

    The HTTP gate owns verification. Callers must supply the contract emitted by
    Wang's verifier and the policy emitted by the team verifier; a locally
    self-declared approval field is not an authorization to call this function.
    """
    policy = Day3Policy.model_validate_json(json.dumps(policy_data, ensure_ascii=False, allow_nan=False))
    if policy.policyStatus != "TEAM_APPROVED":
        raise ValueError("reviewed Monte Carlo requires a team-approved policy")
    manifest = read_source_manifest(project_root)
    raw = (project_root / "demo_data/causora_day1_mock.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != FROZEN_MOCK_SHA256:
        raise ValueError("the frozen synthetic source snapshot changed without a new reviewed data version")
    validate_request(request, dataset_id="ds-001", contract=reviewed_contract, allow_unfrozen_scenarios=True)
    if policy.operatingPolicy.horizonStartDate.isoformat() != reviewed_contract["renewalDate"]:
        raise ValueError("approved policy horizon must begin on the reviewed renewal date")
    if any(s["demandUnits24m"] > 1_000_000 for s in request["scenarios"]):
        raise ValueError("trial demand exceeds safe internal arithmetic range")

    history = manifest["historicalDemand"]["observations"]
    leads, prices = _lead_days(manifest["supplierDelivery"]["orders"])
    if len(history) < 52 or len(leads["A"]) < 30:
        raise ValueError("insufficient historical demand or Supplier A POs for empirical bootstrap")
    if len(leads["B"]) >= 30:
        raise ValueError("Supplier B distribution needs re-review before retaining a fallback")
    if policy.operatingPolicy.targetStockUnits <= policy.operatingPolicy.safetyStockUnits:
        raise ValueError("approved target stock must exceed explicit safety stock")

    sampled_history, lead_a, lead_b, draws_sha = _draw_master(
        history=history, leads_a=leads["A"], policy=policy, seed=request["seed"])
    by_scenario = {scenario["id"]: scenario for scenario in request["scenarios"]}
    by_option = {option["id"]: option for option in request["options"]}
    historical_total = manifest["historicalDemand"]["totalUnits"]
    expected_lead_a = Decimal(sum(leads["A"])) / Decimal(len(leads["A"]))
    triangle = policy.supplierBLeadFallback
    expected_lead_b = Decimal(triangle.minDays + triangle.modeDays + triangle.maxDays) / Decimal(3)
    matrix: dict[str, list[dict]] = {}
    formula_traces: dict[str, dict[str, dict]] = {}
    for scenario_id in SCENARIOS:
        scenario = by_scenario[scenario_id]
        factor = scenario["demandUnits24m"] / historical_total
        demand = np.maximum(0, np.rint(sampled_history.astype(np.float64) * factor)).astype(np.int64)
        rows: list[dict] = []
        traces: dict[str, dict] = {}
        for option_id in OPTIONS:
            cell, trace = _simulate_cell(
                scenario=scenario, option=by_option[option_id], contract=reviewed_contract,
                policy=policy.operatingPolicy, demands=demand, leads_a=lead_a, leads_b=lead_b,
                prices=prices, runs=policy.monteCarloRuns,
                expected_lead_days_a=expected_lead_a, expected_lead_days_b=expected_lead_b)
            rows.append(cell)
            traces[option_id] = trace
        matrix[scenario_id] = rows
        formula_traces[scenario_id] = traces

    code_hashes = {file: hashlib.sha256((Path(__file__).parent / file).read_bytes()).hexdigest()
                   for file in ("monte_carlo.py", "models.py", "policy.py")}
    return {
        "matrix": matrix,
        "deltas": calculate_deltas({"matrix": matrix}, request["scenarios"]),
        "formulaTraces": formula_traces,
        "seed": request["seed"],
        "dataVersion": reviewed_data_version,
        "formulaVersion": "tco-v1",
        "weeks": WEEKS,
        "monteCarloRuns": policy.monteCarloRuns,
        "unitPricesUsd": {supplier: float(prices[supplier]) for supplier in ("A", "B")},
        "distributionProvenance": {
            "demand": "historical-fit: 104 synthetic weekly observations",
            "supplierA": f"historical-fit: {len(leads['A'])} synthetic POs",
            "supplierB": "team-approved triangular fallback; 12 synthetic POs below 30-PO threshold",
            "supplierBParameters": policy.supplierBLeadFallback.model_dump(mode="json"),
            "randomGenerator": f"numpy.PCG64 / numpy {np.__version__}",
            "drawsSha256": draws_sha,
            "cashP90": policy.cashP90Method,
        },
        "inputHashesSha256": {key: manifest[key]["sourceSha256"] for key in
            ("historicalDemand", "supplierDelivery", "openingInventory", "noticeRegister", "contractAssumptions")},
        "engineSourceSha256": code_hashes,
    }
