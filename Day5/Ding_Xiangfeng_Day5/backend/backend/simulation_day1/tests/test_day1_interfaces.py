from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import jsonschema
from openpyxl import load_workbook

from simulation_day1.interfaces import (
    ContractInputError, calculate_deltas, check_accounting,
    make_mock_request, make_mock_response, select_by_scenario,
    simulate_104_weeks, validate_request,
)
from simulation_day1.prepare_history import prepare_history

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "simulation_day1"
MOCK = json.loads((ROOT / "demo_data" / "causora_day1_mock.json").read_text(encoding="utf-8"))


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.request = make_mock_request(MOCK)
        self.sim = copy.deepcopy(MOCK["simulation"])

    def test_schema_and_examples(self):
        schema = json.loads((ART / "schemas" / "simulate_v1.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        for name, name_in_schema in (("simulate_request.json", "request"),
                                     ("simulate_request_no_feasible.json", "request"),
                                     ("simulate_response_LOCAL_MOCK.json", "response"),
                                     ("simulate_response_no_feasible_LOCAL_MOCK.json", "response")):
            payload = json.loads((ART / "examples" / name).read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator({**schema, "$ref": f"#/$defs/{name_in_schema}"}).validate(payload)
        no_option = json.loads((ART / "examples" / "simulate_request_no_feasible.json").read_text(encoding="utf-8"))
        self.assertEqual(no_option["budgetCeilingUsd"], 1)
        validate_request(no_option, contract=MOCK["contract"])

    def test_request_and_units(self):
        validate_request(self.request, contract=MOCK["contract"])
        for mutator in (
            lambda r: r.update(riskThreshold=12),
            lambda r: r["scenarios"][1].update(demandShock=-0.15),
            lambda r: r["options"][1].update(shareA=0.59),
            lambda r: r["options"][2].update(terminateA=False),
            lambda r: r["scenarios"][1].update(demandUnits24m=22000),
            lambda r: r.update(extra="x"),
            lambda r: r["options"].append(copy.deepcopy(r["options"][2])),
        ):
            bad = copy.deepcopy(self.request)
            mutator(bad)
            with self.assertRaises(ContractInputError):
                validate_request(bad, contract=MOCK["contract"])

    def test_notice_must_be_explicit(self):
        contract = copy.deepcopy(MOCK["contract"])
        contract.pop("noticeSent")
        with self.assertRaisesRegex(ContractInputError, "noticeSent"):
            validate_request(self.request, contract=contract)
        contract = copy.deepcopy(MOCK["contract"])
        contract["daysToRenewal"] = 46
        with self.assertRaisesRegex(ContractInputError, "deadline"):
            validate_request(self.request, contract=contract)
        contract = copy.deepcopy(MOCK["contract"])
        contract["noticeSent"] = True
        with self.assertRaisesRegex(ContractInputError, "renewalLocked"):
            validate_request(self.request, contract=contract)

    def test_accounting_matches_and_rejects_double_billing(self):
        check_accounting(self.sim, MOCK["contract"], self.request["options"])
        bad = copy.deepcopy(self.sim)
        bad["matrix"]["baseline"][0]["breakdown"]["purchase"] += 43680
        bad["matrix"]["baseline"][0]["expectedTco"] += 43680
        with self.assertRaisesRegex(ContractInputError, "base-price"):
            check_accounting(bad, MOCK["contract"], self.request["options"])
        bad = copy.deepcopy(self.sim)
        bad["matrix"]["baseline"][2]["breakdown"]["terminationFee"] = 50000
        with self.assertRaisesRegex(ContractInputError, "termination"):
            check_accounting(bad, MOCK["contract"], self.request["options"])
        unlocked = copy.deepcopy(MOCK["contract"])
        unlocked["noticeSent"], unlocked["renewalLocked"] = True, False
        no_renewal = copy.deepcopy(self.sim)
        for cells in no_renewal["matrix"].values():
            for cell in cells:
                fee = cell["breakdown"]["renewalPremium"] + cell["breakdown"]["terminationFee"]
                cell["breakdown"]["renewalPremium"] = 0
                cell["breakdown"]["terminationFee"] = 0
                cell["expectedTco"] -= fee
        check_accounting(no_renewal, unlocked, self.request["options"])

    def test_selection_by_scenario_and_inclusive_thresholds(self):
        choices = select_by_scenario(self.sim, self.request)
        self.assertEqual({v["recommendedOptionId"] for v in choices.values()}, {"D1"})
        self.assertEqual(choices["demand-drop"]["constraintViolations"], [
            {"optionId": "D0", "code": "stockout_threshold"},
            {"optionId": "D2", "code": "cash_ceiling"}])
        req = make_mock_request(MOCK, risk_threshold=0.05, budget_usd=430000)
        self.assertEqual(select_by_scenario(self.sim, req)["baseline"]["recommendedOptionId"], "D1")
        req = make_mock_request(MOCK, budget_usd=1)
        result = select_by_scenario(self.sim, req)
        self.assertTrue(all(s["status"] == "no_feasible_option" and s["recommendedOptionId"] is None for s in result.values()))
        self.assertEqual(result["lead-stress"]["constraintViolations"], [
            {"optionId": "D0", "code": "stockout_threshold"}, {"optionId": "D0", "code": "cash_ceiling"},
            {"optionId": "D1", "code": "cash_ceiling"}, {"optionId": "D2", "code": "cash_ceiling"}])

    def test_deltas_option_minus_d0_and_probability_points(self):
        d = calculate_deltas(self.sim, self.request["scenarios"])
        self.assertEqual(len(d), 9)
        self.assertEqual(next(x for x in d if x["scenarioId"] == "baseline" and x["optionId"] == "D1"), {
            "scenarioId": "baseline", "optionId": "D1", "baselineOptionId": "D0",
            "deltaTco": -9000, "deltaStockoutPp": -4.0, "deltaServicePp": 1.3, "deltaCashP90": -21000})

    def test_mock_not_real_engine_and_metadata(self):
        resp = make_mock_response(MOCK, self.request, request_id="req-day1-mock-001")
        self.assertEqual(resp["data"]["simulation"]["monteCarloRuns"], 0)
        self.assertEqual(resp["data"]["simulation"]["weeks"], 104)
        self.assertIn("mock", resp["data"]["simulation"]["simulationId"])
        with self.assertRaises(NotImplementedError):
            simulate_104_weeks(self.request, {"datasetId": "ds-001", "contract": MOCK["contract"]})

    def test_static_mock_rejects_changed_scenarios_but_reselects_thresholds(self):
        changed = copy.deepcopy(self.request)
        changed["scenarios"][0].update(demandShock=-50, demandUnits24m=13000)
        with self.assertRaisesRegex(ContractInputError, "baseline:.*frozen scenario mismatch.*demandShock"):
            validate_request(changed, contract=MOCK["contract"])
        with self.assertRaisesRegex(ContractInputError, "frozen scenario mismatch"):
            make_mock_response(MOCK, changed, request_id="req-changed-demand")
        with self.assertRaises(NotImplementedError):
            simulate_104_weeks(changed, {"datasetId": "ds-001", "contract": MOCK["contract"]})

        changed = copy.deepcopy(self.request)
        changed["scenarios"][0]["leadTimeMultiplier"] = 9
        with self.assertRaisesRegex(ContractInputError, "baseline:.*leadTimeMultiplier"):
            make_mock_response(MOCK, changed, request_id="req-changed-lead")

        changed = copy.deepcopy(self.request)
        changed["scenarios"][1]["label"] = "New external case"
        with self.assertRaisesRegex(ContractInputError, "demand-drop:.*label"):
            validate_request(changed, contract=MOCK["contract"])

        changed = copy.deepcopy(self.request)
        changed["options"][1]["label"] = "Different D1"
        with self.assertRaisesRegex(ContractInputError, "D1:.*frozen option mismatch.*label"):
            make_mock_response(MOCK, changed, request_id="req-changed-option")

        reordered = copy.deepcopy(self.request)
        reordered["scenarios"].reverse()  # array order is not a new scenario assumption
        reordered["options"].reverse()
        validate_request(reordered, contract=MOCK["contract"])

        default = make_mock_response(MOCK, self.request, request_id="req-default")
        narrow = make_mock_request(MOCK, risk_threshold=0.01, budget_usd=1)
        filtered = make_mock_response(MOCK, narrow, request_id="req-new-limits")
        self.assertEqual(default["data"]["simulation"], filtered["data"]["simulation"])
        self.assertEqual(default["data"]["selections"]["baseline"]["status"], "selected")
        self.assertEqual(filtered["data"]["selections"]["baseline"]["status"], "no_feasible_option")

        altered_mock = copy.deepcopy(MOCK)
        altered_mock["simulation"]["matrix"]["baseline"][0]["breakdown"]["holding"] += 1
        with self.assertRaisesRegex(ContractInputError, "input snapshot changed"):
            make_mock_response(altered_mock, self.request, request_id="req-altered-mock")

    def test_history_exact_snapshot(self):
        payload = prepare_history()
        self.assertEqual((payload["weekCount"], payload["totalUnits"], payload["lockedForecastUnits24m"]), (104, 25936, 26000))
        self.assertNotEqual(payload["totalUnits"], payload["lockedForecastUnits24m"])
        schema = json.loads((ART / "schemas" / "historical_weekly_v1.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(payload)
        self.assertEqual(payload, json.loads((ART / "historical_weekly_v1.json").read_text(encoding="utf-8")))

    def test_independent_spreadsheet_oracle(self):
        oracle = load_workbook(ART / "oracle_day1_independent.xlsx", data_only=True)
        sheet = oracle["Accounting oracle"]
        for row in range(4, 9):
            self.assertEqual(sheet[f"N{row}"].value, sheet[f"O{row}"].value)
            self.assertEqual(sheet[f"P{row}"].value, 0)
        self.assertEqual((sheet["C10"].value, sheet["G10"].value, sheet["C11"].value, sheet["G11"].value),
                         (26000, 3900, 15600, 2340))
        rows = [list(sheet.values)[i - 1] for i in (4, 5, 6)]
        risks = {"D0": (0.09, 3600), "D1": (0.05, 3500), "D2": (0.03, 29000)}
        cells = []
        for r in rows:
            oid, a, b = r[1], r[2], r[3]
            cells.append({"optionId": oid, "feasible": True, "expectedTco": r[14],
                          "stockoutProbability": risks[oid][0], "serviceLevel": 0.95,
                          "cashOutflowP90": risks[oid][1],
                          "breakdown": {"purchase": r[10], "holding": r[7], "stockoutLoss": r[8],
                                        "renewalPremium": r[11], "terminationFee": r[12]},
                          "unitsFromA": a, "unitsFromB": b, "tone": "neutral"})
        sim = {"unitPricesUsd": {"A": 12, "B": 12.6}, "matrix": {"baseline": cells}}
        contract = {"renewalLocked": True, "minPurchaseUnitsA": 150,
                    "renewalPriceIncreasePct": 0.14, "terminationFeeUsd": 25000}
        check_accounting(sim, contract, self.request["options"])
        small_request = {"scenarios": [{"id": "baseline"}], "riskThreshold": 0.12, "budgetCeilingUsd": 4000}
        self.assertEqual(select_by_scenario(sim, small_request)["baseline"]["recommendedOptionId"], "D1")
        small_request["riskThreshold"] = 0.01
        self.assertEqual(select_by_scenario(sim, small_request)["baseline"]["status"], "no_feasible_option")
        q = oracle["Selection oracle"]
        self.assertEqual([q[f"I{i}"].value for i in range(3, 9)], [True, True, False, False, False, False])


if __name__ == "__main__":
    unittest.main()
