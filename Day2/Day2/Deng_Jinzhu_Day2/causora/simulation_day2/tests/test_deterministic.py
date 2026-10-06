from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from simulation_day1.interfaces import make_mock_request
from simulation_day2.deterministic import (
    FROZEN_INTERMEDIATE_SHA256, InputNotApproved, _distribute_history, _one_run, require_reviewed_bundle,
    read_source_manifest, run_reviewed_internal, run_unreviewed_preview,
)
from simulation_day2.models import Day2Policy, DeterministicPreview

ROOT = Path(__file__).resolve().parents[2]
MOCK = json.loads((ROOT / "demo_data/causora_day1_mock.json").read_text(encoding="utf-8"))


def make_test_policy(*, opening: int = 1840, target: int = 1800, safety: int = 100,
                holding: str = "0.05") -> dict:
    return {"assumptionStatus": "UNAPPROVED_TEST_INPUT",
            "horizonStartDate": "2026-11-18", "openingInventoryEffectiveDate": "2026-11-18",
            "openingInventoryUnits": opening,
            "openingInventorySource": "UNAPPROVED_TEST_BRIDGE_INVENTORY_NOT_FROM_2026-10-04_CSV",
            "sellingPriceUsdPerUnit": "20", "lostContributionMarginUsdPerUnit": "5",
            "holdingCostUsdPerUnitWeek": holding, "safetyStockUnits": safety,
            "targetStockUnits": target, "cashTiming": "at_order", "roundingMode": "half_even",
            "demandMode": "history_rescaled_to_scenario_units",
            "leadTimeMode": "seed_rotated_empirical_cycle", "leadStressAppliesTo": "A_only",
            "commitmentSchedule": "linear_weekly", "purchaseRecognition": "at_order",
            "holdingBasis": "available_ending_average"}


class DeterministicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.request = make_mock_request(MOCK)
        cls.policy = make_test_policy()
        cls.result = run_unreviewed_preview(cls.request, cls.policy)

    def test_real_104_week_matrix_with_intact_weekly_conservation(self):
        result = self.result
        DeterministicPreview.model_validate_json(json.dumps(result, ensure_ascii=False))
        self.assertNotIn("schemaVersion", result)
        self.assertEqual(result["internalSchemaVersion"], "jinzhu.deterministic-preview.v1")
        self.assertEqual(result["referencedContractVersion"], "causora.contract.v1")
        self.assertEqual(result["weeks"], 104)
        self.assertEqual({s: len(v) for s, v in result["matrix"].items()},
                         {"baseline": 3, "demand-drop": 3, "lead-stress": 3})
        self.assertFalse(result["decisionReady"])
        self.assertEqual((result["deterministicRuns"], result["monteCarloRuns"]), (1, 0))
        self.assertEqual(result["intermediateManifestSha256"], FROZEN_INTERMEDIATE_SHA256)
        for file, digest in result["engineSourceSha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / "simulation_day2" / file).read_bytes()).hexdigest(), digest)
        self.assertEqual(result["unitPricesUsd"], {"A": 12.0, "B": 12.6})
        self.assertFalse(any("recommendedOptionId" in cell or "stockoutProbability" in cell or "cashOutflowP90" in cell
                             for cells in result["matrix"].values() for cell in cells))
        for sid, cells in result["matrix"].items():
            self.assertEqual({c["optionId"] for c in cells}, {"D0", "D1", "D2"})
            for cell in cells:
                weeks = cell["weeklyTrace"]
                self.assertEqual(len(weeks), 104)
                self.assertEqual(sum(w["demandUnits"] for w in weeks), cell["demandUnits"])
                self.assertEqual(sum(w["fulfilledUnits"] for w in weeks), cell["fulfilledUnits"])
                self.assertEqual(sum(w["lostUnits"] for w in weeks), cell["lostUnits"])
                self.assertEqual(sum(cell["costBreakdownUsd"].values()), cell["tcoUsd"])
                self.assertTrue(all(w["availableUnits"] == w["openingUnits"] + w["arrivalsA"] + w["arrivalsB"] and
                                    w["fulfilledUnits"] + w["endingUnits"] == w["availableUnits"] and
                                    w["fulfilledUnits"] + w["lostUnits"] == w["demandUnits"] for w in weeks))
                for w in weeks:
                    for supplier in ("A", "B"):
                        if w["ordered" + supplier]:
                            self.assertGreater(w["sampledLeadDays" + supplier], 0)
                            self.assertGreater(w["plannedArrivalWeek" + supplier], w["week"])
                        else:
                            self.assertIsNone(w["sampledLeadDays" + supplier])
                            self.assertIsNone(w["plannedArrivalWeek" + supplier])
                self.assertEqual(cell["orderedUnitsA"], sum(w["orderedA"] for w in weeks))
                self.assertEqual(cell["orderedUnitsB"], sum(w["orderedB"] for w in weeks))
                self.assertEqual(cell["unitsInTransitAtEnd"], cell["orderedUnitsA"] + cell["orderedUnitsB"] - cell["deliveredUnitsA"] - cell["deliveredUnitsB"])

    def test_contract_minimum_fixed_split_single_premium_and_exit_fee(self):
        for cells in self.result["matrix"].values():
            d0, d1, d2 = cells
            self.assertEqual(d0["orderedUnitsB"], 0)
            self.assertGreaterEqual(d0["orderedUnitsA"], 15600)
            self.assertEqual((d1["orderedUnitsA"], d1["orderedUnitsB"]), (15600, 10400))
            self.assertEqual((d2["orderedUnitsA"], d2["costBreakdownUsd"]["renewalPremium"]), (0, 0))
            self.assertEqual(d1["costBreakdownUsd"]["renewalPremium"], 26208)
            self.assertEqual(d1["costBreakdownUsd"]["purchase"], 318240)
            self.assertEqual([d["costBreakdownUsd"]["terminationFee"] for d in cells], [0, 0, 25000])
            self.assertEqual(sum(Decimal(w["terminationFeeRawUsd"]) for w in d2["weeklyTrace"]), Decimal(25000))
            for c in cells:
                self.assertEqual(c["costBreakdownUsd"]["purchase"],
                                 round(c["orderedUnitsA"] * 12 + c["orderedUnitsB"] * 12.6))
                self.assertEqual(c["cashOutflowUsd"], c["tcoUsd"] - c["costBreakdownUsd"]["stockoutLoss"])

    def test_history_rescaling_exact_scenario_total(self):
        history = read_source_manifest()["historicalDemand"]["observations"]
        self.assertEqual([sum(_distribute_history(history, n)) for n in (0, 13000, 22100, 26000)],
                         [0, 13000, 22100, 26000])
        self.assertEqual(_distribute_history(history, 26000), _distribute_history(history, 26000))

    def test_source_data_version_rejects_changed_history_bytes(self):
        manifest = read_source_manifest()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for field in ("historicalDemand", "supplierDelivery", "openingInventory", "noticeRegister", "contractAssumptions"):
                name = manifest[field]["sourceFile"]
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, root / name)
            path = root / "simulation_day1/demo_inputs_v1.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / "simulation_day1/demo_inputs_v1.json", path)
            with (root / manifest["historicalDemand"]["sourceFile"]).open("a", encoding="utf-8") as stream:
                stream.write("\n")
            with self.assertRaisesRegex(ValueError, "source file changed"):
                read_source_manifest(root)

    def test_stress_supplier_scope_requires_explicit_choice(self):
        self.assertEqual(self.result["matrix"]["baseline"][2]["tcoUsd"],
                         self.result["matrix"]["lead-stress"][2]["tcoUsd"])
        both = run_unreviewed_preview(self.request, make_test_policy() | {"leadStressAppliesTo": "all_suppliers"})
        self.assertNotEqual(both["matrix"]["baseline"][2]["weeklyTrace"],
                            both["matrix"]["lead-stress"][2]["weeklyTrace"])

    def test_timely_notice_turns_off_renewal_premium_and_exit_fee(self):
        contract = copy.deepcopy(MOCK["contract"])
        contract["noticeSent"] = True
        contract["renewalLocked"] = False
        source = read_source_manifest()
        history = source["historicalDemand"]["observations"]
        from simulation_day2.deterministic import _lead_days
        leads, prices = _lead_days(source["supplierDelivery"]["orders"])
        for option in MOCK["options"]:
            cell = _one_run(scenario=MOCK["scenarios"][0], option=option, contract=contract,
                            policy=Day2Policy.model_validate_json(json.dumps(self.policy)),
                            historical=history, lead_days=leads, prices=prices, seed=self.request["seed"])
            self.assertEqual(cell["costBreakdownUsd"]["renewalPremium"], 0)
            self.assertEqual(cell["costBreakdownUsd"]["terminationFee"], 0)

    def test_seed_repeat_and_changed_external_inputs_recalculate(self):
        second = run_unreviewed_preview(copy.deepcopy(self.request), self.policy)
        self.assertEqual(second, self.result)
        changed = copy.deepcopy(self.request)
        changed["scenarios"][0].update(demandShock=-50, demandUnits24m=13000)
        after = run_unreviewed_preview(changed, self.policy)
        self.assertNotEqual(after["previewId"], self.result["previewId"])
        self.assertEqual(after["matrix"]["baseline"][0]["demandUnits"], 13000)
        self.assertNotEqual(after["matrix"]["baseline"][0]["tcoUsd"], self.result["matrix"]["baseline"][0]["tcoUsd"])
        changed = copy.deepcopy(self.request)
        changed["scenarios"][0]["leadTimeMultiplier"] = 9
        roomy = make_test_policy(target=10000)
        stress = run_unreviewed_preview(changed, roomy)
        before = run_unreviewed_preview(self.request, roomy)
        self.assertNotEqual(stress["matrix"]["baseline"][0]["weeklyTrace"],
                            before["matrix"]["baseline"][0]["weeklyTrace"])

    def test_missing_or_misdated_inputs_and_pending_review_fail_closed(self):
        with self.assertRaises(InputNotApproved):
            require_reviewed_bundle(ROOT, None)
        with self.assertRaises(InputNotApproved):
            require_reviewed_bundle(ROOT, ROOT / "evidence_day2/examples/pending_review")
        with self.assertRaises(InputNotApproved):
            run_reviewed_internal(self.request, self.policy, project_root=ROOT,
                                  reviewed_bundle=ROOT / "evidence_day2/examples/pending_review")
        policy = make_test_policy()
        policy["openingInventorySource"] = "public/demo/opening_inventory.csv"
        with self.assertRaisesRegex(ValidationError, "not inventory at renewal"):
            run_unreviewed_preview(self.request, policy)
        policy = make_test_policy(); del policy["lostContributionMarginUsdPerUnit"]
        with self.assertRaises(ValidationError):
            run_unreviewed_preview(self.request, policy)
        with self.assertRaisesRegex(ValueError, "exceed computed reorder point"):
            run_unreviewed_preview(self.request, make_test_policy(target=1))
        with self.assertRaises(ValueError):
            run_unreviewed_preview(self.request, make_test_policy() | {"horizonStartDate": "2026-10-04", "openingInventoryEffectiveDate": "2026-10-04"})

    def test_independent_104_week_zero_demand_cost_oracle_and_invalid_margin(self):
        # Literal expected totals from arithmetic independent of the engine:
        # D0: 15,600 × 12 + 15,600 × 12 × 0.14 = 213,408;
        # D1: 15,600 × 12 + 10,400 × 12.6 + 26,208 = 344,448;
        # D2: one B unit at $12.60 rounded $13 + one $25,000 exit = 25,013.
        policy = Day2Policy.model_validate_json(json.dumps(make_test_policy(opening=0, target=1, safety=0, holding="0")))
        zero = [{"unitsDemanded": 0} for _ in range(104)]
        cells = [_one_run(scenario={"id": "baseline", "demandUnits24m": 0, "leadTimeMultiplier": 1},
                          option=option, contract=MOCK["contract"], policy=policy,
                          historical=zero, lead_days={"A": [7], "B": [7]},
                          prices={"A": Decimal(12), "B": Decimal("12.6")}, seed=1)
                 for option in MOCK["options"]]
        self.assertEqual([c["tcoUsd"] for c in cells], [213408, 344448, 25013])
        self.assertTrue(all(c["grossMargin"] is None and c["grossMarginStatus"] == "INVALID_REVENUE_ZERO" for c in cells))
        self.assertEqual([c["stockoutOccurred"] for c in cells], [False, False, False])


if __name__ == "__main__":
    unittest.main()
