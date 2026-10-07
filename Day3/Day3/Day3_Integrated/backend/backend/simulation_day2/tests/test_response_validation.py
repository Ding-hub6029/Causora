from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from simulation_day2.response_validation import NumericMismatch, validate_simulation_response

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "simulation_day1/examples"
MOCK = json.loads((ROOT / "demo_data/causora_day1_mock.json").read_text(encoding="utf-8"))


class ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.request = json.loads((EXAMPLES / "simulate_request.json").read_text(encoding="utf-8"))
        cls.response = json.loads((EXAMPLES / "simulate_response_LOCAL_MOCK.json").read_text(encoding="utf-8"))

    def checked(self, result, request=None):
        return validate_simulation_response(result, request or self.request, MOCK["contract"],
                expected_data_version=MOCK["meta"]["dataVersion"], allow_legacy_mock_for_tests=True)

    def test_static_known_vector_requires_explicit_test_only_flag(self):
        self.checked(self.response)
        with self.assertRaisesRegex(NumericMismatch, "zero-draw"):
            validate_simulation_response(self.response, self.request, MOCK["contract"],
                expected_data_version=MOCK["meta"]["dataVersion"])

    def test_delta_forgery_and_wrong_baseline_fail(self):
        for field, value in (("deltaTco", -8999), ("deltaStockoutPp", 4.0),
                             ("deltaServicePp", 13.0), ("deltaCashP90", -20000),
                             ("baselineOptionId", "D1")):
            changed = copy.deepcopy(self.response)
            changed["data"]["deltas"][1][field] = value
            with self.subTest(field=field), self.assertRaises(NumericMismatch):
                self.checked(changed)

    def test_winner_violations_and_request_limits_must_match(self):
        changed = copy.deepcopy(self.response)
        changed["data"]["selections"]["baseline"]["recommendedOptionId"] = "D0"
        with self.assertRaisesRegex(NumericMismatch, "recommendation"):
            self.checked(changed)
        changed = copy.deepcopy(self.response)
        changed["data"]["selections"]["demand-drop"]["constraintViolations"] = []
        with self.assertRaisesRegex(NumericMismatch, "recommendation"):
            self.checked(changed)
        changed = copy.deepcopy(self.request)
        changed["budgetCeilingUsd"] = 1  # old selected response must not be reused
        with self.assertRaisesRegex(NumericMismatch, "recommendation"):
            self.checked(self.response, changed)

    def test_metadata_and_accounting_reject_stale_or_duplicated_cost(self):
        changed = copy.deepcopy(self.response)
        changed["data"]["simulation"]["seed"] += 1
        with self.assertRaisesRegex(NumericMismatch, "metadata"):
            self.checked(changed)
        changed = copy.deepcopy(self.response)
        cell = changed["data"]["simulation"]["matrix"]["baseline"][0]
        cell["breakdown"]["purchase"] += 43680
        cell["expectedTco"] += 43680
        with self.assertRaisesRegex(NumericMismatch, "base-price"):
            self.checked(changed)


if __name__ == "__main__":
    unittest.main()
