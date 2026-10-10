"""Independent audit of Jinzhu's development-only deterministic preview traces.

This module deliberately does not call the deterministic engine's private calculation
helpers.  It only uses its public source-manifest reader and strict DTO classes as a
schema/source boundary, then reconstructs every inventory transition, lead-time
selection, commitment order, and monetary total from the supplied trace.

It is intentionally a development-only control: a successful audit is never a
recommendation, policy approval, or human-review substitute.
"""
from __future__ import annotations

import csv
import hashlib
import importlib
import json
import math
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any


N_WEEKS = 104
SCENARIOS = ("baseline", "demand-drop", "lead-stress")
OPTIONS = ("D0", "D1", "D2")
SOURCE_SECTIONS = (
    "historicalDemand",
    "supplierDelivery",
    "openingInventory",
    "noticeRegister",
    "contractAssumptions",
)
COST_COMPONENTS = (
    "purchase",
    "holding",
    "stockoutLoss",
    "renewalPremium",
    "terminationFee",
)


class TraceMismatch(ValueError):
    """Raised when a preview cannot be independently reconciled to its inputs."""


def _fail(where: str, expected: Any, actual: Any) -> None:
    raise TraceMismatch(f"{where}: expected {expected!r}, got {actual!r}")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TraceMismatch(message)


def _canonical(value: Any) -> str:
    """Return the compact canonical JSON form used in Jinzhu's public preview ID."""
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise TraceMismatch(f"value is not canonical-JSON serializable: {exc}") from exc


def _json_model(model: Any, value: dict, label: str) -> dict:
    """Validate through Jinzhu's strict DTO, retaining JSON-mode normalized values."""
    try:
        parsed = model.model_validate_json(json.dumps(value, ensure_ascii=False, allow_nan=False))
        return parsed.model_dump(mode="json")
    except Exception as exc:  # Pydantic's exception type is deliberately not a dependency here.
        raise TraceMismatch(f"{label} fails Jinzhu strict schema: {exc}") from exc


def _load_jinzhu_modules(project_root: Path) -> tuple[Any, Any, Any, Any, Any]:
    """Load only strict schema/source helpers; no calculation helper is referenced."""
    root = project_root.resolve()
    if not (root / "simulation_day1").is_dir() or not (root / "simulation_day2").is_dir():
        raise TraceMismatch(f"project_root is not a Jinzhu causora source root: {root}")
    added = str(root) not in sys.path
    if added:
        sys.path.insert(0, str(root))
    try:
        source_models = importlib.import_module("simulation_day1.source_models")
        wire_models = importlib.import_module("simulation_day1.wire_models")
        interfaces = importlib.import_module("simulation_day1.interfaces")
        day2_models = importlib.import_module("simulation_day2.models")
        deterministic = importlib.import_module("simulation_day2.deterministic")
    except Exception as exc:
        raise TraceMismatch(
            "unable to load Jinzhu strict schema/source helpers; install the Jinzhu test dependencies "
            f"and use its causora root: {exc}"
        ) from exc
    finally:
        if added:
            sys.path.remove(str(root))

    for module in (source_models, wire_models, interfaces, day2_models, deterministic):
        module_file = Path(getattr(module, "__file__", "")).resolve()
        try:
            module_file.relative_to(root)
        except ValueError as exc:
            raise TraceMismatch(f"loaded {module.__name__} from a different project root: {module_file}") from exc
    return source_models, wire_models, interfaces, day2_models, deterministic


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise TraceMismatch(f"cannot read required source {path}: {exc}") from exc


def _decimal(value: Any, where: str) -> Decimal:
    if not isinstance(value, str):
        raise TraceMismatch(f"{where}: raw monetary trace value must be a string, got {type(value).__name__}")
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise TraceMismatch(f"{where}: invalid Decimal {value!r}") from exc
    if not result.is_finite():
        raise TraceMismatch(f"{where}: Decimal must be finite")
    return result


def _usd(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


def _ceil(value: Decimal) -> int:
    return int(value.to_integral_value(rounding="ROUND_CEILING"))


def _history_distribution(history: list[dict], target: int) -> list[int]:
    """Independently reproduce fixed-seasonality largest-remainder allocation."""
    if len(history) != N_WEEKS or target < 0:
        raise TraceMismatch("historical seasonality requires 104 observations and nonnegative target")
    base = [row["unitsDemanded"] for row in history]
    if any(not isinstance(n, int) or isinstance(n, bool) or n < 0 for n in base):
        raise TraceMismatch("historical demand observations are not nonnegative integer units")
    total = sum(base)
    if total == 0:
        if target:
            raise TraceMismatch("positive scenario demand cannot be allocated over zero historical demand")
        return [0] * N_WEEKS
    quotient_remainder = [divmod(units * target, total) for units in base]
    result = [pair[0] for pair in quotient_remainder]
    required = target - sum(result)
    for index in sorted(range(N_WEEKS), key=lambda idx: (-quotient_remainder[idx][1], idx))[:required]:
        result[index] += 1
    if sum(result) != target:
        raise TraceMismatch("independent largest-remainder demand mass balance failed")
    return result


def _lead_history(orders: list[dict]) -> tuple[dict[str, list[int]], dict[str, Decimal]]:
    days: dict[str, list[int]] = {"A": [], "B": []}
    prices: dict[str, set[Decimal]] = {"A": set(), "B": set()}
    try:
        ordered = sorted(orders, key=lambda row: (row["orderDate"], row["orderId"]))
    except (KeyError, TypeError) as exc:
        raise TraceMismatch(f"supplier delivery source is malformed: {exc}") from exc
    for row in ordered:
        supplier = row.get("supplier")
        if supplier not in days:
            raise TraceMismatch(f"supplier delivery contains unsupported supplier {supplier!r}")
        try:
            lead = (date.fromisoformat(row["arrivalDate"]) - date.fromisoformat(row["orderDate"])).days
            price = Decimal(str(row["basePriceUsd"]))
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise TraceMismatch(f"invalid historical order record {row!r}: {exc}") from exc
        if lead <= 0 or not price.is_finite():
            raise TraceMismatch(f"invalid historical lead/price in order {row.get('orderId')!r}")
        days[supplier].append(lead)
        prices[supplier].add(price)
    if any(not days[supplier] for supplier in ("A", "B")) or any(len(prices[supplier]) != 1 for supplier in ("A", "B")):
        raise TraceMismatch("both suppliers require positive lead samples and one unambiguous base price")
    return days, {supplier: next(iter(prices[supplier])) for supplier in ("A", "B")}


def _split_order(quantity: int, share_a: Decimal, *, remaining_a: int | None = None,
                 remaining_b: int | None = None) -> tuple[int, int]:
    """Independent half-even allocation and fixed-quota clamp for D1 purchases."""
    if quantity < 0:
        raise TraceMismatch("recomputed order quantity is negative")
    proposed_a = _usd(Decimal(quantity) * share_a)
    if remaining_a is None:
        return proposed_a, quantity - proposed_a
    if remaining_b is None:
        raise TraceMismatch("D1 fixed allocation is missing supplier-B quota")
    low = max(0, quantity - remaining_b)
    high = min(quantity, remaining_a)
    if low > high:
        raise TraceMismatch("recomputed D1 order exceeds fixed purchased-unit quota")
    a_quantity = min(high, max(low, proposed_a))
    return a_quantity, quantity - a_quantity


def _source_context(project_root: Path, modules: tuple[Any, Any, Any, Any, Any]) -> tuple[dict, dict, dict, dict]:
    """Validate frozen manifest/raw sources and return independently usable source facts."""
    source_models, wire_models, interfaces, _day2_models, deterministic = modules
    manifest_path = project_root / "simulation_day1" / "demo_inputs_v1.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()

    # The public source reader is permitted as a source-integrity check.  No
    # simulation/calculation function is invoked or used as an audit oracle.
    try:
        manifest_from_reader = deterministic.read_source_manifest(project_root)
    except Exception as exc:
        raise TraceMismatch(f"Jinzhu read_source_manifest rejects project sources: {exc}") from exc
    manifest = _json_model(source_models.DemoInputs, json.loads(manifest_bytes.decode("utf-8")), "source manifest")
    if _canonical(manifest_from_reader) != _canonical(manifest):
        raise TraceMismatch("read_source_manifest result differs from strict manifest JSON")

    expected_source_hashes: dict[str, str] = {}
    for section in SOURCE_SECTIONS:
        entry = manifest[section]
        source_file = entry["sourceFile"]
        digest = _sha256_file(project_root / source_file)
        if digest != entry["sourceSha256"]:
            _fail(f"source manifest {section}.sourceSha256", digest, entry["sourceSha256"])
        expected_source_hashes[section] = digest

    historical_csv = project_root / manifest["historicalDemand"]["sourceFile"]
    try:
        with historical_csv.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != ["week_start", "units_demanded", "provenance"]:
                raise TraceMismatch("historical demand raw CSV header differs from frozen schema")
            historical_raw = [
                {
                    "weekStart": row["week_start"],
                    "unitsDemanded": int(row["units_demanded"]),
                    "provenance": row["provenance"],
                }
                for row in reader
            ]
    except (OSError, KeyError, ValueError) as exc:
        raise TraceMismatch(f"cannot reconstruct historical demand source: {exc}") from exc
    if historical_raw != manifest["historicalDemand"]["observations"]:
        raise TraceMismatch("historical raw CSV observations differ from manifest observations")

    mock_path = project_root / "demo_data" / "causora_day1_mock.json"
    mock_bytes = mock_path.read_bytes()
    mock_digest = hashlib.sha256(mock_bytes).hexdigest()
    if mock_digest != interfaces.FROZEN_MOCK_SHA256:
        _fail("frozen Day 1 mock SHA-256", interfaces.FROZEN_MOCK_SHA256, mock_digest)
    try:
        mock_contract = _json_model(wire_models.ContractConstraint, json.loads(mock_bytes.decode("utf-8"))["contract"], "frozen mock contract")
    except (KeyError, json.JSONDecodeError) as exc:
        raise TraceMismatch(f"cannot parse frozen mock contract: {exc}") from exc
    return manifest, expected_source_hashes, mock_contract, {
        "intermediateManifestSha256": manifest_digest,
        "mockSha256": mock_digest,
    }


def _check_preview_metadata(preview: dict, request: dict, policy: dict, contract: dict,
                            project_root: Path, modules: tuple[Any, Any, Any, Any, Any],
                            manifest: dict, source_hashes: dict[str, str], mock_contract: dict,
                            source_digests: dict[str, str]) -> tuple[dict, dict, dict]:
    """Validate strict DTOs and source-bound, unreviewed-preview metadata."""
    _source_models, wire_models, interfaces, day2_models, _deterministic = modules
    request_normalized = _json_model(wire_models.SimulateRequest, request, "request")
    policy_normalized = _json_model(day2_models.Day2Policy, policy, "policy")
    contract_normalized = _json_model(wire_models.ContractConstraint, contract, "contract")
    preview_normalized = _json_model(day2_models.DeterministicPreview, preview, "preview")
    try:
        interfaces.validate_request(
            request_normalized,
            contract=contract_normalized,
            allow_unfrozen_scenarios=True,
        )
    except Exception as exc:
        raise TraceMismatch(f"request/contract compatibility check failed: {exc}") from exc

    if _canonical(contract_normalized) != _canonical(mock_contract):
        raise TraceMismatch("supplied contract does not equal the frozen unreviewed Day 1 mock contract")
    if _canonical(preview_normalized["policy"]) != _canonical(policy_normalized):
        raise TraceMismatch("preview.policy differs from the supplied policy")
    if policy_normalized["horizonStartDate"] != contract_normalized["renewalDate"]:
        _fail("policy.horizonStartDate", contract_normalized["renewalDate"], policy_normalized["horizonStartDate"])

    exact_metadata = {
        "kind": "CAUSORA_DAY2_INTERNAL_DETERMINISTIC_PREVIEW_V1",
        "status": "UNREVIEWED_TEST_ONLY_NO_RECOMMENDATION",
        "decisionReady": False,
        "internalSchemaVersion": "jinzhu.deterministic-preview.v1",
        "referencedContractVersion": "causora.contract.v1",
        "formulaVersion": "tco-v1",
        "weeks": N_WEEKS,
        "deterministicRuns": 1,
        "monteCarloRuns": 0,
        "reviewStatus": "PENDING_HUMAN_REVIEW",
        "reviewSha256": None,
        "assumptionStatus": "UNAPPROVED_TEST_INPUT",
    }
    for field, expected in exact_metadata.items():
        if preview_normalized[field] != expected:
            _fail(f"preview.{field}", expected, preview_normalized[field])
    if preview_normalized["seed"] != request_normalized["seed"]:
        _fail("preview.seed", request_normalized["seed"], preview_normalized["seed"])
    if preview_normalized["sourceDataVersion"] != manifest["dataVersion"]:
        _fail("preview.sourceDataVersion", manifest["dataVersion"], preview_normalized["sourceDataVersion"])

    expected_engine_hashes = {
        name: _sha256_file(project_root / "simulation_day2" / name)
        for name in ("deterministic.py", "models.py")
    }
    if preview_normalized["engineSourceSha256"] != expected_engine_hashes:
        _fail("preview.engineSourceSha256", expected_engine_hashes, preview_normalized["engineSourceSha256"])
    if preview_normalized["intermediateManifestSha256"] != source_digests["intermediateManifestSha256"]:
        _fail(
            "preview.intermediateManifestSha256",
            source_digests["intermediateManifestSha256"],
            preview_normalized["intermediateManifestSha256"],
        )
    if preview_normalized["inputHashesSha256"] != source_hashes:
        _fail("preview.inputHashesSha256", source_hashes, preview_normalized["inputHashesSha256"])

    lead_days, prices = _lead_history(manifest["supplierDelivery"]["orders"])
    expected_prices = {supplier: Decimal(str(prices[supplier])) for supplier in ("A", "B")}
    actual_prices = {supplier: Decimal(str(preview_normalized["unitPricesUsd"][supplier])) for supplier in ("A", "B")}
    if actual_prices != expected_prices:
        _fail("preview.unitPricesUsd", {k: str(v) for k, v in expected_prices.items()}, {k: str(v) for k, v in actual_prices.items()})

    canonical_payload = {
        "request": request_normalized,
        "policy": policy_normalized,
        "sources": manifest["dataVersion"],
        "review": None,
        "contract": contract_normalized,
        "engineSourceSha256": expected_engine_hashes,
        "intermediateManifestSha256": source_digests["intermediateManifestSha256"],
        "hashes": source_hashes,
    }
    expected_id = "preview-day2-" + hashlib.sha256(_canonical(canonical_payload).encode("utf-8")).hexdigest()[:20]
    if preview_normalized["previewId"] != expected_id:
        _fail("preview.previewId", expected_id, preview_normalized["previewId"])
    return request_normalized, policy_normalized, contract_normalized


def _compare_number(where: str, expected: int, actual: Any) -> None:
    if actual != expected:
        _fail(where, expected, actual)


def _audit_cell(cell: dict, scenario: dict, option: dict, policy: dict, contract: dict,
                history: list[dict], lead_days: dict[str, list[int]], prices: dict[str, Decimal],
                seed: int) -> dict:
    """Independently replay one 104-week inventory ledger and its cost accumulation."""
    scenario_id, option_id = scenario["id"], option["id"]
    prefix = f"{scenario_id}/{option_id}"
    if cell["scenarioId"] != scenario_id or cell["optionId"] != option_id:
        raise TraceMismatch(f"{prefix}: matrix key and cell identity disagree")

    target = scenario["demandUnits24m"]
    demand = _history_distribution(history, target)
    share_a = Decimal(str(option["shareA"]))
    multiplier_a = Decimal(str(scenario["leadTimeMultiplier"]))
    multiplier_b = multiplier_a if policy["leadStressAppliesTo"] == "all_suppliers" else Decimal(1)
    mean_a = Decimal(sum(lead_days["A"])) / Decimal(len(lead_days["A"])) / Decimal(7)
    mean_b = Decimal(sum(lead_days["B"])) / Decimal(len(lead_days["B"])) / Decimal(7)
    mean_lead = share_a * mean_a * multiplier_a + (Decimal(1) - share_a) * mean_b * multiplier_b
    reorder_point = _ceil(Decimal(target) / Decimal(N_WEEKS) * mean_lead + Decimal(policy["safetyStockUnits"]))
    if policy["targetStockUnits"] <= reorder_point:
        raise TraceMismatch(f"{prefix}: supplied policy cannot support computed reorder point {reorder_point}")

    fixed_a = contract["minPurchaseUnitsA"] if option_id == "D1" else None
    fixed_b = contract["lockedForecastUnits24m"] - fixed_a if fixed_a is not None else None
    minimum_a = contract["minPurchaseUnitsA"] if contract["renewalLocked"] and not option["terminateA"] else 0
    due: dict[int, dict[str, int]] = defaultdict(lambda: {"A": 0, "B": 0})
    ordered = {"A": 0, "B": 0}
    delivered = {"A": 0, "B": 0}
    order_counts = {"A": 0, "B": 0}
    raw_costs = {name: Decimal(0) for name in COST_COMPONENTS}
    fulfilled_total = 0
    lost_total = 0
    on_hand = policy["openingInventoryUnits"]
    start_date = date.fromisoformat(policy["horizonStartDate"])
    trace = cell["weeklyTrace"]

    if len(trace) != N_WEEKS:
        _fail(f"{prefix}.weeklyTrace length", N_WEEKS, len(trace))
    for index, row in enumerate(trace):
        week = index + 1
        row_prefix = f"{prefix}/week-{week}"
        _compare_number(row_prefix + ".week", week, row["week"])
        expected_start = (start_date + timedelta(weeks=index)).isoformat()
        if row["startDate"] != expected_start:
            _fail(row_prefix + ".startDate", expected_start, row["startDate"])
        _compare_number(row_prefix + ".openingUnits", on_hand, row["openingUnits"])

        arrivals = due.pop(index, {"A": 0, "B": 0})
        _compare_number(row_prefix + ".arrivalsA", arrivals["A"], row["arrivalsA"])
        _compare_number(row_prefix + ".arrivalsB", arrivals["B"], row["arrivalsB"])
        delivered["A"] += arrivals["A"]
        delivered["B"] += arrivals["B"]
        available = on_hand + arrivals["A"] + arrivals["B"]
        filled = min(demand[index], available)
        shortage = demand[index] - filled
        ending = available - filled
        fulfilled_total += filled
        lost_total += shortage
        in_transit_before = sum(entry["A"] + entry["B"] for entry in due.values())
        position = ending + in_transit_before
        reorder = max(0, policy["targetStockUnits"] - position) if position <= reorder_point else 0

        expected_week_values = {
            "demandUnits": demand[index],
            "availableUnits": available,
            "fulfilledUnits": filled,
            "lostUnits": shortage,
            "endingUnits": ending,
            "onOrderUnitsBefore": in_transit_before,
            "inventoryPositionBefore": position,
            "reorderPointUnits": reorder_point,
        }
        for field, expected in expected_week_values.items():
            _compare_number(row_prefix + "." + field, expected, row[field])

        if fixed_a is not None:
            need_a = max(0, _ceil(Decimal(fixed_a) * Decimal(week) / Decimal(N_WEEKS)) - ordered["A"])
            need_b = max(0, _ceil(Decimal(fixed_b) * Decimal(week) / Decimal(N_WEEKS)) - ordered["B"])
            order_quantity = min(max(reorder, need_a + need_b), fixed_a + fixed_b - ordered["A"] - ordered["B"])
            expected_a, expected_b = _split_order(
                order_quantity,
                share_a,
                remaining_a=fixed_a - ordered["A"],
                remaining_b=fixed_b - ordered["B"],
            )
        else:
            commitment_due = max(0, _ceil(Decimal(minimum_a) * Decimal(week) / Decimal(N_WEEKS)) - ordered["A"])
            order_quantity = max(reorder, commitment_due)
            expected_a, expected_b = _split_order(order_quantity, share_a)
        _compare_number(row_prefix + ".orderedA", expected_a, row["orderedA"])
        _compare_number(row_prefix + ".orderedB", expected_b, row["orderedB"])

        week_purchase = Decimal(expected_a) * prices["A"] + Decimal(expected_b) * prices["B"]
        week_premium = (
            Decimal(expected_a) * prices["A"] * Decimal(str(contract["renewalPriceIncreasePct"]))
            if contract["renewalLocked"] else Decimal(0)
        )
        week_fee = Decimal(contract["terminationFeeUsd"]) if week == 1 and option["terminateA"] and contract["renewalLocked"] else Decimal(0)
        week_holding = (Decimal(available + ending) / Decimal(2)) * Decimal(str(policy["holdingCostUsdPerUnitWeek"]))
        week_lost = Decimal(shortage) * Decimal(str(policy["lostContributionMarginUsdPerUnit"]))
        expected_raw = {
            "holdingRawUsd": week_holding,
            "stockoutLossRawUsd": week_lost,
            "basePurchaseRawUsd": week_purchase,
            "renewalPremiumRawUsd": week_premium,
            "terminationFeeRawUsd": week_fee,
        }
        for field, expected in expected_raw.items():
            actual = _decimal(row[field], row_prefix + "." + field)
            if actual != expected:
                _fail(row_prefix + "." + field, str(expected), str(actual))
        raw_costs["purchase"] += week_purchase
        raw_costs["holding"] += week_holding
        raw_costs["stockoutLoss"] += week_lost
        raw_costs["renewalPremium"] += week_premium
        raw_costs["terminationFee"] += week_fee

        for supplier, quantity in (("A", expected_a), ("B", expected_b)):
            sample_field = "sampledLeadDays" + supplier
            arrival_field = "plannedArrivalWeek" + supplier
            if quantity:
                sample = lead_days[supplier][(seed + order_counts[supplier]) % len(lead_days[supplier])]
                order_counts[supplier] += 1
                factor = multiplier_a if supplier == "A" else multiplier_b
                lead_weeks = max(1, _ceil(Decimal(sample) * factor / Decimal(7)))
                planned_arrival = index + lead_weeks + 1
                _compare_number(row_prefix + "." + sample_field, sample, row[sample_field])
                _compare_number(row_prefix + "." + arrival_field, planned_arrival, row[arrival_field])
                due[index + lead_weeks][supplier] += quantity
                ordered[supplier] += quantity
            else:
                if row[sample_field] is not None:
                    _fail(row_prefix + "." + sample_field, None, row[sample_field])
                if row[arrival_field] is not None:
                    _fail(row_prefix + "." + arrival_field, None, row[arrival_field])
        on_order_after = sum(entry["A"] + entry["B"] for entry in due.values())
        _compare_number(row_prefix + ".onOrderUnitsAfter", on_order_after, row["onOrderUnitsAfter"])
        on_hand = ending

    if fixed_a is not None and (ordered["A"], ordered["B"]) != (fixed_a, fixed_b):
        raise TraceMismatch(f"{prefix}: D1 does not complete the exact 60/40 fixed procurement quotas")
    if ordered["A"] < minimum_a:
        raise TraceMismatch(f"{prefix}: A minimum commitment is not fulfilled")

    rounded_costs = {name: _usd(raw_costs[name]) for name in COST_COMPONENTS}
    tco = sum(rounded_costs.values())
    revenue = _usd(Decimal(fulfilled_total) * Decimal(str(policy["sellingPriceUsdPerUnit"])))
    gross_profit = revenue - tco
    cash = sum(rounded_costs[name] for name in ("purchase", "holding", "renewalPremium", "terminationFee"))
    expected_cell = {
        "demandUnits": target,
        "fulfilledUnits": fulfilled_total,
        "lostUnits": lost_total,
        "orderedUnitsA": ordered["A"],
        "orderedUnitsB": ordered["B"],
        "deliveredUnitsA": delivered["A"],
        "deliveredUnitsB": delivered["B"],
        "unitsInTransitAtEnd": sum(entry["A"] + entry["B"] for entry in due.values()),
        "endingInventoryUnits": on_hand,
        "stockoutOccurred": lost_total > 0,
        "feasible": ordered["A"] >= minimum_a and (fixed_a is None or (ordered["A"], ordered["B"]) == (fixed_a, fixed_b)),
        "revenueUsd": revenue,
        "grossProfitUsd": gross_profit,
        "cashOutflowUsd": cash,
        "costBreakdownUsd": rounded_costs,
        "tcoUsd": tco,
        "grossMarginStatus": "VALID" if revenue else "INVALID_REVENUE_ZERO",
    }
    for field, expected in expected_cell.items():
        if cell[field] != expected:
            _fail(prefix + "." + field, expected, cell[field])
    expected_service = fulfilled_total / target if target else 1.0
    if not math.isclose(cell["serviceLevel"], expected_service, rel_tol=0.0, abs_tol=1e-15):
        _fail(prefix + ".serviceLevel", expected_service, cell["serviceLevel"])
    expected_margin = gross_profit / revenue if revenue else None
    if expected_margin is None:
        if cell["grossMargin"] is not None:
            _fail(prefix + ".grossMargin", None, cell["grossMargin"])
    elif not math.isclose(cell["grossMargin"], expected_margin, rel_tol=0.0, abs_tol=1e-15):
        _fail(prefix + ".grossMargin", expected_margin, cell["grossMargin"])

    return {
        "scenarioId": scenario_id,
        "optionId": option_id,
        "demandUnits": target,
        "fulfilledUnits": fulfilled_total,
        "lostUnits": lost_total,
        "orderedUnitsA": ordered["A"],
        "orderedUnitsB": ordered["B"],
        "deliveredUnitsA": delivered["A"],
        "deliveredUnitsB": delivered["B"],
        "endingInventoryUnits": on_hand,
        "unitsInTransitAtEnd": expected_cell["unitsInTransitAtEnd"],
        "stockoutOccurred": lost_total > 0,
        "serviceLevel": expected_service,
        "cashOutflowUsd": cash,
        "tcoUsd": tco,
        "grossProfitUsd": gross_profit,
        "feasible": expected_cell["feasible"],
    }


def audit_deterministic_preview(preview: dict, request: dict, policy: dict, contract: dict,
                                project_root: Path) -> dict:
    """Audit all 9 × 104 development preview trace rows without engine calculation calls.

    Args:
        preview: Output of the *public* unreviewed-preview runner.
        request: The exact Day 1 simulation request used to make the preview.
        policy: The exact unapproved test policy used to make the preview.
        contract: The frozen Day 1 mock contract; reviewed contracts are rejected.
        project_root: Jinzhu's ``causora`` source root, not this delivery root.

    Returns:
        A development-only audit summary.  Its ``decisionReady`` field is always
        ``False``; it is not a recommendation or approval artifact.

    Raises:
        TraceMismatch: Any schema, source, metadata, state, accounting, or trace
            inconsistency.  No value is repaired or inferred silently.
    """
    if not all(isinstance(value, dict) for value in (preview, request, policy, contract)):
        raise TraceMismatch("preview, request, policy, and contract must all be dictionaries")
    root = Path(project_root).resolve()
    modules = _load_jinzhu_modules(root)
    manifest, source_hashes, mock_contract, source_digests = _source_context(root, modules)
    request_normalized, policy_normalized, contract_normalized = _check_preview_metadata(
        preview, request, policy, contract, root, modules, manifest, source_hashes, mock_contract, source_digests
    )

    scenarios = {scenario["id"]: scenario for scenario in request_normalized["scenarios"]}
    options = {option["id"]: option for option in request_normalized["options"]}
    if set(scenarios) != set(SCENARIOS) or set(options) != set(OPTIONS):
        raise TraceMismatch("request does not contain the complete fixed three-scenario/three-option matrix")

    lead_days, prices = _lead_history(manifest["supplierDelivery"]["orders"])
    cell_summaries: list[dict] = []
    trace_rows = 0
    for scenario_id in SCENARIOS:
        cells = preview["matrix"].get(scenario_id)
        if not isinstance(cells, list) or len(cells) != len(OPTIONS):
            raise TraceMismatch(f"{scenario_id}: matrix must contain exactly three cells")
        by_option = {cell.get("optionId"): cell for cell in cells if isinstance(cell, dict)}
        if len(by_option) != len(OPTIONS) or set(by_option) != set(OPTIONS):
            raise TraceMismatch(f"{scenario_id}: missing or duplicate option cell")
        for option_id in OPTIONS:
            cell = by_option[option_id]
            summary = _audit_cell(
                cell, scenarios[scenario_id], options[option_id], policy_normalized,
                contract_normalized, manifest["historicalDemand"]["observations"],
                lead_days, prices, request_normalized["seed"],
            )
            cell_summaries.append(summary)
            trace_rows += len(cell["weeklyTrace"])

    if len(cell_summaries) != 9 or trace_rows != 936:
        raise TraceMismatch(f"complete trace coverage failed: cells={len(cell_summaries)}, rows={trace_rows}")
    return {
        "kind": "CAUSORA_DAY3_DEV_ONLY_TRACE_AUDIT_V1",
        "devOnly": True,
        "decisionReady": False,
        "matrixCells": 9,
        "traceRows": 936,
        "checks": [
            "strict schemas and unreviewed-only status/review gate",
            "frozen manifest, raw source hashes, source version, engine hashes, and unit prices",
            "canonical preview ID bound to request, policy, frozen contract, source hashes, and engine hashes",
            "three scenarios by three options with 104 ordered weekly rows per cell",
            "largest-remainder historical seasonality, inventory flow, arrivals, and on-order ledger",
            "seed-rotated empirical lead samples, planned arrival weeks, reorder point, and D1 60/40 linear quotas",
            "Decimal half-even monetary trace, rounded five-line TCO, cash, revenue, gross profit, margin, and service identities",
            "single-path stockout boolean only; no probability, P90, selection, or recommendation semantics",
        ],
        "cells": cell_summaries,
    }
