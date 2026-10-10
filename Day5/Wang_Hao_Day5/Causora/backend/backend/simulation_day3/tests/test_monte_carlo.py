"""Day 3 independent numeric oracles and fail-closed contract tests."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator
from openpyxl import load_workbook
from pydantic import ValidationError

from simulation_day1.interfaces import check_accounting, calculate_deltas, select_by_scenario
from simulation_day1.wire_models import ApiFailure, SimulateResponse, SimulateSuccess
from simulation_day3.api_boundary import simulate_v1_boundary
from simulation_day3.models import MonteCarloPreview
from simulation_day3.monte_carlo import (
    _nearest_rank_p90, _round_micro, _simulate_cell, run_unapproved_monte_carlo,
)
from simulation_day3.policy import Day3Policy

ROOT = Path(__file__).resolve().parents[2]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class StochasticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.request = load("simulation_day1/examples/simulate_request.json")
        cls.policy = load("simulation_day3/examples/UNAPPROVED_MC_POLICY.json")
        cls.mock = load("demo_data/causora_day1_mock.json")
        cls.preview = run_unapproved_monte_carlo(cls.request, cls.policy, project_root=ROOT)

    def test_01_typed_matrix_and_nonpublic_boundary(self):
        value = self.preview
        MonteCarloPreview.model_validate_json(json.dumps(value, ensure_ascii=False))
        self.assertFalse(value["decisionReady"])
        self.assertEqual(value["reviewStatus"], "PENDING_11_HUMAN_REVIEW_ROWS")
        self.assertNotIn("schemaVersion", value)
        self.assertNotIn("data", value)
        self.assertNotIn("testOnlyData", value)
        self.assertNotIn("simulation", value)
        self.assertNotIn("recommendedOptionId", json.dumps(value))
        self.assertNotIn("simulationId", json.dumps(value))
        self.assertEqual(value["monteCarloRuns"], 1000)
        self.assertEqual(value["formulaVersion"], "tco-v1")
        self.assertEqual(set(value["computedMatrix"]), {"baseline", "demand-drop", "lead-stress"})
        # The frozen v1 DTO has no approval invariant; structural separation
        # prevents a single accidental ApiSuccess(data=preview) wrapper.
        envelope = {"schemaVersion": "causora.contract.v1", "dataVersion": value["sourceDataVersion"],
                    "requestId": "req-must-reject", "data": value}
        with self.assertRaises(ValidationError):
            SimulateSuccess.model_validate_json(json.dumps(envelope))

    def test_02_fixed_seed_reproduces_every_integer_percentile_and_trace(self):
        again = run_unapproved_monte_carlo(self.request, self.policy, project_root=ROOT)
        self.assertEqual(again, self.preview)
        changed = copy.deepcopy(self.request)
        changed["seed"] += 1
        different = run_unapproved_monte_carlo(changed, self.policy, project_root=ROOT)
        self.assertNotEqual(different["distributionProvenance"]["drawsSha256"], self.preview["distributionProvenance"]["drawsSha256"])
        self.assertNotEqual(different["previewId"], self.preview["previewId"])

    def test_03_real_104_week_mass_balance_and_actual_lead_samples(self):
        for sid, by_option in self.preview["formulaTraces"].items():
            for oid, trace in by_option.items():
                with self.subTest(sid=sid, oid=oid):
                    rows = trace["weeks"]
                    self.assertEqual(len(rows), 104)
                    for i, row in enumerate(rows):
                        self.assertEqual(row["week"], i + 1)
                        self.assertEqual(row["openingUnits"] + row["arrivalsA"] + row["arrivalsB"], row["availableUnits"])
                        self.assertEqual(row["availableUnits"] - row["fulfilledUnits"], row["endingUnits"])
                        self.assertEqual(row["demandUnits"] - row["fulfilledUnits"], row["lostUnits"])
                        self.assertEqual(row["onOrderUnitsBefore"] + row["orderedA"] + row["orderedB"], row["onOrderUnitsAfter"])
                        if row["orderedA"]:
                            self.assertIsNotNone(row["sampledLeadDaysA"])
                            self.assertGreater(row["plannedArrivalWeekA"], i + 1)
                        if row["orderedB"]:
                            self.assertIsNotNone(row["sampledLeadDaysB"])
                    if oid == "D1":
                        self.assertEqual(sum(r["orderedA"] for r in rows), 15600)
                        self.assertEqual(sum(r["orderedB"] for r in rows), 10400)
                    if oid == "D2":
                        self.assertEqual(sum(int(Decimal(r["terminationFeeRawUsd"])) for r in rows), 25000)
                    else:
                        self.assertEqual(sum(Decimal(r["terminationFeeRawUsd"]) for r in rows), 0)
                    self.assertEqual(trace["p90CashRankOneBased"], 900)
                    self.assertEqual(trace["cashOutflowP90Usd"], next(c for c in self.preview["computedMatrix"][sid] if c["optionId"] == oid)["cashOutflowP90"])
                    self.assertEqual(trace["expectedGrossProfitUsd"],
                                     trace["expectedRevenueUsd"] - sum(trace["displayedWholeUsdBreakdown"].values()))
                    if trace["expectedRevenueUsd"]:
                        self.assertEqual(trace["grossMarginStatus"], "VALID")

    def test_04_common_wire_accounting_deltas_screening_without_recommendation(self):
        simulation = {"matrix": self.preview["computedMatrix"], "unitPricesUsd": self.preview["unitPricesUsd"]}
        check_accounting(simulation, self.mock["contract"], self.request["options"])
        self.assertEqual(self.preview["decisionDeltas"], calculate_deltas(simulation, self.request["scenarios"]))
        selected_only_in_memory = select_by_scenario(simulation, self.request)
        for sid, screening in self.preview["constraintScreening"].items():
            self.assertEqual(screening["status"], "screening_only_unapproved")
            self.assertEqual(screening["constraintViolations"], selected_only_in_memory[sid]["constraintViolations"])
            failed = {v["optionId"] for v in screening["constraintViolations"]}
            self.assertEqual(screening["eligibleOptionIds"], [oid for oid in ("D0", "D1", "D2") if oid not in failed])
        # A typed numeric shape can be assembled in test memory only; there is
        # no returned/serialized public response or selected winner in preview.
        check_shape = {"simulation": {**simulation, "simulationId": "sim-in-memory-only",
            "seed": self.request["seed"], "dataVersion": self.preview["sourceDataVersion"],
            "formulaVersion": "tco-v1", "weeks": 104, "monteCarloRuns": 1000},
            "deltas": self.preview["decisionDeltas"], "selections": selected_only_in_memory}
        SimulateResponse.model_validate_json(json.dumps(check_shape))
        # No-feasible and inclusive threshold filtering are independent per scenario.
        strict = {**self.request, "riskThreshold": 0.0, "budgetCeilingUsd": 1}
        rejected = select_by_scenario(simulation, strict)
        for sid, selection in rejected.items():
            self.assertEqual(selection["status"], "no_feasible_option")
            self.assertIsNone(selection["recommendedOptionId"])
            self.assertEqual(selection["scenarioId"], sid)
            self.assertTrue(all(v["code"] == "cash_ceiling" or v["code"] == "stockout_threshold" for v in selection["constraintViolations"]))
        self.assertTrue(all(cell["tone"] != "recommended" for cells in simulation["matrix"].values() for cell in cells))

    def test_05_independent_manual_zero_demand_oracle_not_engine_generated_expected(self):
        """Manual expected dollars: D0=15600*12*1.14; D1 adds 10400*12.6; D2 buys B=1 and pays 25k once."""
        policy = copy.deepcopy(self.policy)
        policy["operatingPolicy"].update(openingInventoryUnits=0, targetStockUnits=1, safetyStockUnits=0, holdingCostUsdPerUnitWeek="0")
        operating = Day3Policy.model_validate_json(json.dumps(policy)).operatingPolicy
        demand = np.zeros((4, 104), dtype=np.int64)
        lead = np.full_like(demand, 7)
        scenario = {**self.mock["scenarios"][0], "demandUnits24m": 0}
        manual = {"D0": (213408, 213408, 15600, 0),
                  "D1": (344448, 344448, 15600, 10400),
                  "D2": (25013, 25013, 0, 1)}
        for option in self.mock["options"]:
            cell, trace = _simulate_cell(scenario=scenario, option=option, contract=self.mock["contract"],
                policy=operating, demands=demand, leads_a=lead, leads_b=lead,
                prices={"A": Decimal(12), "B": Decimal("12.6")}, runs=4,
                expected_lead_days_a=Decimal(7), expected_lead_days_b=Decimal(7))
            with self.subTest(option=option["id"]):
                self.assertEqual((cell["expectedTco"], cell["cashOutflowP90"], cell["unitsFromA"], cell["unitsFromB"]), manual[option["id"]])
                self.assertEqual((cell["stockoutProbability"], cell["serviceLevel"]), (0.0, 1.0))
                self.assertEqual(trace["p90CashRankOneBased"], 4)
                self.assertEqual((trace["expectedRevenueUsd"], trace["grossMarginStatus"], trace["grossMargin"]),
                                 (0, "INVALID_REVENUE_ZERO", None))
                self.assertEqual(cell["breakdown"]["renewalPremium"], 26208 if option["id"] != "D2" else 0)

    def test_06_independent_one_in_four_stockout_and_nearest_rank_oracle(self):
        """One of four runs loses 10 units: 1/4, loss $50/4=$12.5 -> $12 half-even."""
        policy = copy.deepcopy(self.policy)
        policy["operatingPolicy"].update(openingInventoryUnits=0, targetStockUnits=2, safetyStockUnits=0, holdingCostUsdPerUnitWeek="0")
        operating = Day3Policy.model_validate_json(json.dumps(policy)).operatingPolicy
        demand = np.zeros((4, 104), dtype=np.int64)
        demand[0, 0] = 10
        lead = np.full_like(demand, 7)
        cell, trace = _simulate_cell(scenario={**self.mock["scenarios"][0], "demandUnits24m": 10},
            option=self.mock["options"][2], contract=self.mock["contract"], policy=operating,
            demands=demand, leads_a=lead, leads_b=lead,
            prices={"A": Decimal(12), "B": Decimal("12.6")}, runs=4,
            expected_lead_days_a=Decimal(7), expected_lead_days_b=Decimal(7))
        self.assertEqual((cell["stockoutProbability"], cell["cashOutflowP90"], cell["expectedTco"]), (0.25, 25025, 25037))
        self.assertEqual(cell["breakdown"]["stockoutLoss"], 12)
        self.assertEqual(trace["p90CashRankOneBased"], 4)
        self.assertEqual(_nearest_rank_p90(np.array([100, 400, 200, 300])), (400, 4))
        self.assertEqual(_round_micro(12_500_000), 12)
        self.assertEqual(_round_micro(13_500_000), 14)

    def test_07_unfrozen_scenario_is_actually_recomputed_not_day1_mock(self):
        changed = copy.deepcopy(self.request)
        scenario = next(x for x in changed["scenarios"] if x["id"] == "baseline")
        scenario["demandShock"] = -50
        scenario["demandUnits24m"] = 13000
        fresh = run_unapproved_monte_carlo(changed, self.policy, project_root=ROOT)
        self.assertNotEqual(fresh["computedMatrix"]["baseline"], self.preview["computedMatrix"]["baseline"])
        self.assertEqual(fresh["sourceDataVersion"], self.preview["sourceDataVersion"])
        self.assertNotEqual(fresh["previewId"], self.preview["previewId"])
        invalid = copy.deepcopy(changed)
        scenario_bad = next(x for x in invalid["scenarios"] if x["id"] == "baseline")
        scenario_bad["demandUnits24m"] = 26000
        with self.assertRaises(ValueError):
            run_unapproved_monte_carlo(invalid, self.policy, project_root=ROOT)

    def test_08_source_manifest_tampering_does_not_retain_old_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "simulation_day1", root / "simulation_day1", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            shutil.copytree(ROOT / "public/demo", root / "public/demo")
            shutil.copytree(ROOT / "demo_data", root / "demo_data")
            path = root / "simulation_day1/demo_inputs_v1.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            first = data["historicalDemand"]["observations"]
            first[0]["unitsDemanded"], first[1]["unitsDemanded"] = first[1]["unitsDemanded"], first[0]["unitsDemanded"]
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manifest changed"):
                run_unapproved_monte_carlo(self.request, self.policy, project_root=root)
            shutil.copy2(ROOT / "simulation_day1/demo_inputs_v1.json", path)
            historical = root / "public/demo/historical_demand.csv"
            historical.write_bytes(historical.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "source file changed"):
                run_unapproved_monte_carlo(self.request, self.policy, project_root=root)

    def test_09_explicit_unapproved_B_fallback_and_no_fake_review(self):
        self.assertIn("12 synthetic POs below", self.preview["distributionProvenance"]["supplierB"])
        wrong = copy.deepcopy(self.policy)
        del wrong["supplierBLeadFallback"]
        with self.assertRaises(ValidationError):
            run_unapproved_monte_carlo(self.request, wrong, project_root=ROOT)
        wrong = copy.deepcopy(self.policy)
        wrong["policyStatus"] = "APPROVED"
        with self.assertRaises(ValidationError):
            run_unapproved_monte_carlo(self.request, wrong, project_root=ROOT)
        wrong = copy.deepcopy(self.policy)
        wrong["operatingPolicy"]["openingInventorySource"] = "public/demo/opening_inventory.csv"
        with self.assertRaises(ValidationError):
            run_unapproved_monte_carlo(self.request, wrong, project_root=ROOT)
        wrong = copy.deepcopy(self.policy)
        wrong["supplierBLeadFallback"]["maxDays"] = 9
        with self.assertRaises(ValidationError):
            run_unapproved_monte_carlo(self.request, wrong, project_root=ROOT)

    def test_10_version_source_hash_and_schema(self):
        value = self.preview
        self.assertEqual(value["intermediateManifestSha256"], hashlib.sha256((ROOT / "simulation_day1/demo_inputs_v1.json").read_bytes()).hexdigest())
        for file, sha in value["engineSourceSha256"].items():
            self.assertEqual(sha, hashlib.sha256((ROOT / "simulation_day3" / file).read_bytes()).hexdigest())
        for name, instance in (
            ("unapproved_mc_policy.schema.json", self.policy),
            ("internal_mc_preview.schema.json", value),
        ):
            schema = load("simulation_day3/schemas/" + name)
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(instance)

    def test_11_v1_failure_is_typed_and_missing_approval_does_not_serve_preview(self):
        status, body = simulate_v1_boundary(self.request, request_id="req-day3-pending",
            project_root=ROOT, policy_data=self.policy)
        self.assertEqual((status, body["error"]["code"], body["error"]["details"]["reason"]),
                         (503, "simulation_failed", "human_review_pending"))
        ApiFailure.model_validate_json(json.dumps(body))
        wrong = copy.deepcopy(self.request)
        wrong["scenarios"][0]["demandUnits24m"] += 3
        status, body = simulate_v1_boundary(wrong, request_id="req-day3-invalid", project_root=ROOT, policy_data=self.policy)
        self.assertEqual((status, body["error"]["code"]), (422, "validation_error"))
        with tempfile.TemporaryDirectory() as temp:
            status, body = simulate_v1_boundary(self.request, request_id="req-day3-fake-review",
                project_root=ROOT, reviewed_bundle=Path(temp), policy_data=self.policy)
            self.assertEqual((status, body["error"]["details"]["reason"]), (503, "review_bundle_not_verified"))
            (Path(temp) / "bundle_manifest.json").write_text("{}", encoding="utf-8")
            status, body = simulate_v1_boundary(self.request, request_id="req-day3-no-review-module",
                project_root=ROOT, reviewed_bundle=Path(temp), policy_data=self.policy)
            self.assertEqual((status, body["error"]["details"]["reason"]), (503, "review_bundle_not_verified"))
        self.assertNotIn("data", body)

    def test_12_independent_spreadsheet_has_cached_hand_entered_oracles(self):
        from simulation_day3 import build_oracle
        # An oracle that imports an engine result to set expected values is invalid.
        script = Path(build_oracle.__file__).read_text(encoding="utf-8")
        self.assertNotIn("from simulation_day3.monte_carlo import", script)
        self.assertNotIn("run_unapproved_monte_carlo", script)
        book = load_workbook(ROOT / "simulation_day3/examples/day3_independent_oracle.xlsx", data_only=True, read_only=True)
        try:
            zero, four = book["ZERO_DEMAND_104_WEEKS"], book["FOUR_TRIALS_INDEPENDENT"]
            for row, expected in ((5, 213408), (6, 344448), (7, 25013)):
                self.assertEqual((zero[f"J{row}"].value, zero[f"K{row}"].value, zero[f"L{row}"].value),
                                 (expected, expected, "PASS"))
            for row, expected in ((10, 0.25), (11, 25025), (12, 12), (13, 25), (14, 25000), (15, 25037)):
                self.assertEqual((four[f"B{row}"].value, four[f"C{row}"].value, four[f"D{row}"].value),
                                 (expected, expected, "PASS"))
        finally:
            book.close()

    def test_13_reorder_policy_cannot_drift_with_seed_or_trial_count(self):
        changed = copy.deepcopy(self.request)
        changed["seed"] += 99
        policy = copy.deepcopy(self.policy)
        policy["monteCarloRuns"] = 37
        other = run_unapproved_monte_carlo(changed, policy, project_root=ROOT)
        for sid in ("baseline", "demand-drop", "lead-stress"):
            for oid in ("D0", "D1", "D2"):
                self.assertEqual(self.preview["formulaTraces"][sid][oid]["reorderPointUnits"],
                                 other["formulaTraces"][sid][oid]["reorderPointUnits"])

    def test_14_no_feasible_screening_never_returns_an_unapproved_winner(self):
        strict = {**self.request, "riskThreshold": 0.0, "budgetCeilingUsd": 1}
        preview = run_unapproved_monte_carlo(strict, self.policy, project_root=ROOT)
        self.assertEqual(preview["computedMatrix"], self.preview["computedMatrix"])
        self.assertNotEqual(preview["previewId"], self.preview["previewId"])
        for sid, row in preview["constraintScreening"].items():
            self.assertEqual(row["scenarioId"], sid)
            self.assertEqual(row["eligibleOptionIds"], [])
            self.assertEqual([v["optionId"] for v in row["constraintViolations"] if v["code"] == "cash_ceiling"],
                             ["D0", "D1", "D2"])
        self.assertNotIn("recommendedOptionId", json.dumps(preview))


if __name__ == "__main__":
    unittest.main()
