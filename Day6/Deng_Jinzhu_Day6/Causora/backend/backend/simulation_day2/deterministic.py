"""Real deterministic weekly state progression; never a Monte Carlo / public API result.

The source files are the team's synthetic dataset. Missing business policy
parameters are required explicitly; no model fills them. Preview inputs remain
unreviewed until Wang's 11-row human gate and team policy agreement are met.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_EVEN
from math import ceil
from pathlib import Path

from simulation_day1.build_day1_schemas import FROZEN_SOURCE_HASHES
from simulation_day1.interfaces import FROZEN_MOCK_SHA256, validate_request
from simulation_day1.source_models import DemoInputs
from simulation_day1.wire_models import ContractConstraint, SimulateRequest
from simulation_day2.models import Day2Policy, DeterministicPreview

ROOT = Path(__file__).resolve().parents[1]
N_WEEKS = 104
OPTIONS = ("D0", "D1", "D2")
SCENARIOS = ("baseline", "demand-drop", "lead-stress")
COMPONENTS = ("purchase", "holding", "stockoutLoss", "renewalPremium", "terminationFee")
# SHA-256 of the complete, byte-for-byte demo_inputs_v1.json in the user's
# original Day1.zip (Deng Jinzhu — Day 1). All five intermediate sections are
# frozen, not merely their raw-file hashes. Changing any field requires a new
# reviewed dataVersion and an intentionally updated reference snapshot.
FROZEN_INTERMEDIATE_SHA256 = "607ae2aedc059b1b9bea8fe46874ebee1868b4569132e94e2319072dc751fc3a"


class InputNotApproved(ValueError):
    """The normal/public path must not consume the pending human review."""


def read_source_manifest(project_root: Path = ROOT) -> dict:
    """Pin the full Day1 snapshot, verify five raw hashes and the 104 raw CSV rows."""
    raw_manifest = (project_root / "simulation_day1/demo_inputs_v1.json").read_bytes()
    if hashlib.sha256(raw_manifest).hexdigest() != FROZEN_INTERMEDIATE_SHA256:
        raise ValueError("Day 1 intermediate manifest changed without a new dataVersion/team review")
    data = DemoInputs.model_validate_json(raw_manifest)
    manifest = data.model_dump(mode="json")
    for key in ("historicalDemand", "supplierDelivery", "openingInventory", "noticeRegister", "contractAssumptions"):
        entry = manifest[key]
        path = entry["sourceFile"]
        digest = hashlib.sha256((project_root / path).read_bytes()).hexdigest()
        if digest != entry["sourceSha256"] or digest != FROZEN_SOURCE_HASHES[path]:
            raise ValueError(f"Day 2 source file changed without dataVersion/team review: {path}")
    # Independently reconstruct the demand sequence rather than trusting its
    # preserved total, continuity and sourceSha256 in the intermediate JSON.
    with (project_root / manifest["historicalDemand"]["sourceFile"]).open(
            newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["week_start", "units_demanded", "provenance"]:
            raise ValueError("historical demand source header differs from Day 1")
        observations = [{"weekStart": row["week_start"],
                         "unitsDemanded": int(row["units_demanded"]),
                         "provenance": row["provenance"]} for row in reader]
    if observations != manifest["historicalDemand"]["observations"]:
        raise ValueError("historical demand observations differ from original CSV")
    return manifest


def require_reviewed_bundle(project_root: Path, bundle: Path | None) -> ContractConstraint:
    """Verify Wang's exact post-review bundle; never self-sign his pending form."""
    if bundle is None or not (bundle / "bundle_manifest.json").is_file():
        raise InputNotApproved("11 human review rows are pending; Wang must supply his own promoted/verified bundle")
    from evidence_day2.cli import verify_bundle
    from evidence_day2.handoff_models import JinzhuContractHandoff

    verify_bundle(project_root, bundle)
    handoff = JinzhuContractHandoff.model_validate_json(
        (bundle / "jinzhu_contract_input.json").read_text(encoding="utf-8"))
    return handoff.contract


def _usd(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


def _distribute_history(history: list[dict], target: int) -> list[int]:
    """Fixed 104-week seasonality; largest remainder gives the exact scenario total."""
    if target < 0 or len(history) != N_WEEKS:
        raise ValueError("104 observations and a nonnegative scenario total are required")
    base = [r["unitsDemanded"] for r in history]
    total = sum(base)
    if total <= 0:
        if target != 0:
            raise ValueError("cannot rescale all-zero history to positive forecast")
        return [0] * N_WEEKS
    div, mod = zip(*(divmod(n * target, total) for n in base))
    out = list(div)
    need = target - sum(out)
    for i in sorted(range(N_WEEKS), key=lambda idx: (-mod[idx], idx))[:need]:
        out[i] += 1
    if sum(out) != target:
        raise AssertionError("demand mass balance lost")
    return out


def _lead_days(orders: list[dict]) -> tuple[dict[str, list[int]], dict[str, Decimal]]:
    days: dict[str, list[int]] = defaultdict(list)
    prices: dict[str, set[Decimal]] = defaultdict(set)
    for row in sorted(orders, key=lambda x: (x["orderDate"], x["orderId"])):
        length = (date.fromisoformat(row["arrivalDate"]) - date.fromisoformat(row["orderDate"])).days
        if length <= 0:
            raise ValueError("nonpositive historical lead time")
        days[row["supplier"]].append(length)
        prices[row["supplier"]].add(Decimal(str(row["basePriceUsd"])))
    if set(days) != {"A", "B"} or any(not seq for seq in days.values()) or any(len(p) != 1 for p in prices.values()):
        raise ValueError("both suppliers need historical leads and one unambiguous base price")
    return days, {supplier: next(iter(p)) for supplier, p in prices.items()}


def _split_order(qty: int, share_a: Decimal, *, remaining_a: int | None = None, remaining_b: int | None = None) -> tuple[int, int]:
    if qty < 0:
        raise ValueError("negative order")
    if remaining_a is None:
        a = _usd(Decimal(qty) * share_a)
        return a, qty - a
    if remaining_b is None:
        raise ValueError("missing other quota")
    low = max(0, qty - remaining_b)
    high = min(qty, remaining_a)
    if low > high:
        raise ValueError("order exceeds fixed purchased-unit quota")
    a = min(high, max(low, _usd(Decimal(qty) * share_a)))
    return a, qty - a


def _one_run(*, scenario: dict, option: dict, contract: dict, policy: Day2Policy,
             historical: list[dict], lead_days: dict[str, list[int]], prices: dict[str, Decimal], seed: int) -> dict:
    target = scenario["demandUnits24m"]
    demand = _distribute_history(historical, target)
    shares = Decimal(str(option["shareA"]))
    mean_lead_a = Decimal(sum(lead_days["A"])) / Decimal(len(lead_days["A"])) / Decimal(7)
    mean_lead_b = Decimal(sum(lead_days["B"])) / Decimal(len(lead_days["B"])) / Decimal(7)
    lead_factor_a = Decimal(str(scenario["leadTimeMultiplier"]))
    lead_factor_b = (lead_factor_a if policy.leadStressAppliesTo == "all_suppliers" else Decimal(1))
    mean_lead = shares * mean_lead_a * lead_factor_a + (Decimal(1) - shares) * mean_lead_b * lead_factor_b
    point = ceil(Decimal(target) / N_WEEKS * mean_lead + policy.safetyStockUnits)
    if policy.targetStockUnits <= point:
        raise ValueError(f"targetStockUnits must exceed computed reorder point {point} for {scenario['id']}/{option['id']}")

    # Contractual purchased-unit commitments are counted from the renewed term,
    # so this 104-week internal preview starts at renewal, not at the decision date.
    fixed_a = contract["minPurchaseUnitsA"] if option["id"] == "D1" else None
    fixed_b = contract["lockedForecastUnits24m"] - fixed_a if fixed_a is not None else None
    min_a = contract["minPurchaseUnitsA"] if contract["renewalLocked"] and not option["terminateA"] else 0
    on_hand = policy.openingInventoryUnits
    due: dict[int, dict[str, int]] = defaultdict(lambda: {"A": 0, "B": 0})
    costs = {key: Decimal(0) for key in COMPONENTS}
    total_ordered = {"A": 0, "B": 0}
    total_delivered = {"A": 0, "B": 0}
    supplier_order_count = {"A": 0, "B": 0}
    fulfilled = lost = 0
    trace = []
    for i in range(N_WEEKS):
        start = policy.horizonStartDate + timedelta(weeks=i)
        opening = on_hand
        arrivals = due.pop(i, {"A": 0, "B": 0})
        for s in ("A", "B"):
            total_delivered[s] += arrivals[s]
        available = opening + arrivals["A"] + arrivals["B"]
        filled = min(demand[i], available)
        shortage = demand[i] - filled
        on_hand = available - filled
        fulfilled += filled
        lost += shortage
        in_transit_before = sum(x["A"] + x["B"] for x in due.values())
        position = on_hand + in_transit_before
        reorder = max(0, policy.targetStockUnits - position) if position <= point else 0
        if fixed_a is not None:
            # Pace both commitments across the term, while allowing policy to
            # pull purchases forward. Never exceed the exact fixed 60/40 total.
            a_need = max(0, ceil(Decimal(fixed_a) * (i + 1) / N_WEEKS) - total_ordered["A"])
            b_need = max(0, ceil(Decimal(fixed_b) * (i + 1) / N_WEEKS) - total_ordered["B"])
            order_qty = min(max(reorder, a_need + b_need), fixed_a + fixed_b - sum(total_ordered.values()))
            a_qty, b_qty = _split_order(order_qty, shares,
                remaining_a=fixed_a - total_ordered["A"], remaining_b=fixed_b - total_ordered["B"])
        else:
            commitment_due = max(0, ceil(Decimal(min_a) * (i + 1) / N_WEEKS) - total_ordered["A"])
            order_qty = max(reorder, commitment_due)
            a_qty, b_qty = _split_order(order_qty, shares)
        week_purchase = a_qty * prices["A"] + b_qty * prices["B"]
        week_premium = (a_qty * prices["A"] * Decimal(str(contract["renewalPriceIncreasePct"]))
                        if contract["renewalLocked"] else Decimal(0))
        week_fee = (Decimal(contract["terminationFeeUsd"]) if i == 0 and option["terminateA"]
                    and contract["renewalLocked"] else Decimal(0))
        week_holding = (Decimal(available + on_hand) / 2) * policy.holdingCostUsdPerUnitWeek
        week_lost = Decimal(shortage) * policy.lostContributionMarginUsdPerUnit
        for name, value in (("purchase", week_purchase), ("holding", week_holding),
                            ("stockoutLoss", week_lost), ("renewalPremium", week_premium),
                            ("terminationFee", week_fee)):
            costs[name] += value
        sampled_days = {"A": None, "B": None}
        planned_weeks = {"A": None, "B": None}
        for s, qty in (("A", a_qty), ("B", b_qty)):
            if qty:
                sample = lead_days[s][(seed + supplier_order_count[s]) % len(lead_days[s])]
                supplier_order_count[s] += 1
                factor = lead_factor_a if s == "A" else lead_factor_b
                lead_weeks = max(1, ceil(Decimal(sample) * factor / Decimal(7)))
                due[i + lead_weeks][s] += qty
                total_ordered[s] += qty
                sampled_days[s] = sample
                planned_weeks[s] = i + lead_weeks + 1
        trace.append({"week": i + 1, "startDate": start.isoformat(), "openingUnits": opening,
            "arrivalsA": arrivals["A"], "arrivalsB": arrivals["B"], "demandUnits": demand[i],
            "availableUnits": available, "fulfilledUnits": filled, "lostUnits": shortage,
            "endingUnits": on_hand, "onOrderUnitsBefore": in_transit_before,
            "inventoryPositionBefore": position, "reorderPointUnits": point,
            "orderedA": a_qty, "orderedB": b_qty,
            "sampledLeadDaysA": sampled_days["A"], "sampledLeadDaysB": sampled_days["B"],
            "plannedArrivalWeekA": planned_weeks["A"], "plannedArrivalWeekB": planned_weeks["B"],
            "onOrderUnitsAfter": sum(x["A"] + x["B"] for x in due.values()),
            "holdingRawUsd": str(week_holding), "stockoutLossRawUsd": str(week_lost),
            "basePurchaseRawUsd": str(week_purchase), "renewalPremiumRawUsd": str(week_premium),
            "terminationFeeRawUsd": str(week_fee)})
    if fixed_a is not None and (total_ordered["A"], total_ordered["B"]) != (fixed_a, fixed_b):
        raise AssertionError("fixed D1 purchase commitment was not fulfilled")
    if total_ordered["A"] < min_a:
        raise AssertionError("A contractual minimum was not fulfilled")
    rounded = {name: _usd(value) for name, value in costs.items()}
    tco = sum(rounded.values())
    revenue = _usd(Decimal(fulfilled) * policy.sellingPriceUsdPerUnit)
    gp = revenue - tco
    # Lost contribution is an opportunity cost, not an at-order cash payment.
    cash = sum(rounded[name] for name in ("purchase", "holding", "renewalPremium", "terminationFee"))
    return {"scenarioId": scenario["id"], "optionId": option["id"], "demandUnits": target,
        "fulfilledUnits": fulfilled, "lostUnits": lost,
        "orderedUnitsA": total_ordered["A"], "orderedUnitsB": total_ordered["B"],
        "deliveredUnitsA": total_delivered["A"], "deliveredUnitsB": total_delivered["B"],
        "unitsInTransitAtEnd": sum(x["A"] + x["B"] for x in due.values()),
        "endingInventoryUnits": on_hand, "stockoutOccurred": lost > 0,
        "serviceLevel": fulfilled / target if target else 1.0,
        "feasible": total_ordered["A"] >= min_a and
            (fixed_a is None or (total_ordered["A"], total_ordered["B"]) == (fixed_a, fixed_b)),
        "revenueUsd": revenue, "grossProfitUsd": gp,
        "grossMargin": gp / revenue if revenue else None,
        "grossMarginStatus": "VALID" if revenue else "INVALID_REVENUE_ZERO",
        "cashOutflowUsd": cash, "costBreakdownUsd": rounded, "tcoUsd": tco, "weeklyTrace": trace}


def _calculate_preview(request: dict, policy_data: dict, *, project_root: Path,
                       contract_override: dict | None = None, reviewed_data_version: str | None = None,
                       review_sha256: str | None = None) -> dict:
    policy = Day2Policy.model_validate_json(json.dumps(policy_data, ensure_ascii=False))
    parsed = SimulateRequest.model_validate_json(json.dumps(request, ensure_ascii=False))
    manifest = read_source_manifest(project_root)  # freezes source bytes and 104 ordered observations
    intermediate_digest = hashlib.sha256((project_root / "simulation_day1/demo_inputs_v1.json").read_bytes()).hexdigest()
    mock_bytes = (project_root / "demo_data/causora_day1_mock.json").read_bytes()
    if hashlib.sha256(mock_bytes).hexdigest() != FROZEN_MOCK_SHA256:
        raise ValueError("frozen v4.1 mock changed without review/dataVersion update")
    mock = json.loads(mock_bytes.decode("utf-8"))
    contract = contract_override if contract_override is not None else mock["contract"]
    ContractConstraint.model_validate_json(json.dumps(contract, ensure_ascii=False))
    if policy.horizonStartDate.isoformat() != contract["renewalDate"]:
        raise ValueError("renewal-term 104-week preview must start on the synthetic renewal date")
    if request["datasetId"] != "ds-001":
        raise ValueError("only the named synthetic dataset is supported")
    validate_request(request, dataset_id="ds-001", contract=contract, allow_unfrozen_scenarios=True)
    lead_days, prices = _lead_days(manifest["supplierDelivery"]["orders"])
    by_scenario = {s["id"]: s for s in request["scenarios"]}
    by_option = {o["id"]: o for o in request["options"]}
    matrix = {sid: [_one_run(scenario=by_scenario[sid], option=by_option[oid],
               contract=contract, policy=policy,
               historical=manifest["historicalDemand"]["observations"],
               lead_days=lead_days, prices=prices, seed=request["seed"])
               for oid in OPTIONS] for sid in SCENARIOS}
    engine_hashes = {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                     for name in ("deterministic.py", "models.py")}
    canonical = json.dumps({"request": parsed.model_dump(mode="json"), "policy": policy.model_dump(mode="json"),
                            "sources": reviewed_data_version or manifest["dataVersion"], "review": review_sha256,
                            "contract": contract, "engineSourceSha256": engine_hashes,
                            "intermediateManifestSha256": intermediate_digest,
                            "hashes": {key:manifest[key]["sourceSha256"]
                            for key in ("historicalDemand", "supplierDelivery", "openingInventory", "noticeRegister", "contractAssumptions")}},
                            ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    result = {"kind": "CAUSORA_DAY2_INTERNAL_DETERMINISTIC_PREVIEW_V1",
        "status": ("REVIEWED_SYNTHETIC_POLICY_UNAPPROVED_NO_RECOMMENDATION" if review_sha256
                   else "UNREVIEWED_TEST_ONLY_NO_RECOMMENDATION"), "decisionReady": False,
        "internalSchemaVersion": "jinzhu.deterministic-preview.v1",
        "referencedContractVersion": "causora.contract.v1",
        "sourceDataVersion": reviewed_data_version or manifest["dataVersion"],
        "previewId": "preview-day2-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20],
        "formulaVersion": "tco-v1", "seed": request["seed"], "weeks": N_WEEKS,
        "deterministicRuns": 1, "monteCarloRuns": 0,
        "reviewStatus": "SELF_ATTESTED_SYNTHETIC_REVIEW" if review_sha256 else "PENDING_HUMAN_REVIEW",
        "reviewSha256": review_sha256, "engineSourceSha256": engine_hashes,
        "assumptionStatus": policy.assumptionStatus,
        "note": ("104-week deterministic inventory on synthetic inputs. NOT Monte Carlo or public SimulateSuccess; no probability/P90 or recommendation. "
                 + ("Wang's own synthetic self-review was bundle-verified, but the modeling policy is not team-approved."
                    if review_sha256 else "Wang's 11 human review rows AND modeling policy are pending.")),
        "inputHashesSha256": {key:manifest[key]["sourceSha256"] for key in
            ("historicalDemand", "supplierDelivery", "openingInventory", "noticeRegister", "contractAssumptions")},
        "intermediateManifestSha256": intermediate_digest,
        "unitPricesUsd": {s: float(prices[s]) for s in ("A", "B")},
        "policy": policy.model_dump(mode="json"), "matrix": matrix}
    return DeterministicPreview.model_validate_json(json.dumps(result, ensure_ascii=False, allow_nan=False)).model_dump(mode="json")


def run_unreviewed_preview(request: dict, policy_data: dict, *, project_root: Path = ROOT) -> dict:
    """Run 3×3 physical cells for development; never emit a recommendation/DTO."""
    return _calculate_preview(request, policy_data, project_root=project_root)


def run_reviewed_internal(request: dict, policy_data: dict, *, project_root: Path,
                          reviewed_bundle: Path) -> dict:
    """Only Wang's exact verified output may supply the revised contract/version."""
    contract = require_reviewed_bundle(project_root, reviewed_bundle)
    from evidence_day2.handoff_models import JinzhuContractHandoff

    handoff = JinzhuContractHandoff.model_validate_json(
        (reviewed_bundle / "jinzhu_contract_input.json").read_text(encoding="utf-8"))
    manifest = read_source_manifest(project_root)
    for entry in ("historicalDemand", "supplierDelivery", "openingInventory", "noticeRegister", "contractAssumptions"):
        path = manifest[entry]["sourceFile"]
        if handoff.sourceHashes.get(path) != manifest[entry]["sourceSha256"]:
            raise InputNotApproved(f"reviewed bundle does not bind current {path}")
    if handoff.sourceHashes.get("demo_data/causora_day1_mock.json") != FROZEN_MOCK_SHA256:
        raise InputNotApproved("reviewed handoff is not bound to frozen mock")
    return _calculate_preview(request, policy_data, project_root=project_root,
                              contract_override=contract.model_dump(mode="json"),
                              reviewed_data_version=handoff.dataVersion,
                              review_sha256=handoff.reviewSha256)
