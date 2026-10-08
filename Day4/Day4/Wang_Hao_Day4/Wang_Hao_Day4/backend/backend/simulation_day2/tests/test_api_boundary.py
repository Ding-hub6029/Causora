from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from simulation_day1.wire_models import ApiFailure
from simulation_day2.api_boundary import simulate_v1_boundary

ROOT = Path(__file__).resolve().parents[2]
REQUEST = json.loads((ROOT / "simulation_day1/examples/simulate_request.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((ROOT / "simulation_day1/schemas/api_failure_v1.schema.json").read_text(encoding="utf-8"))


class CommonContractBoundaryTests(unittest.TestCase):
    def check_error(self, status: int, payload: dict, *, code: str, reason: str, request_id: str):
        self.assertIn(status, (422, 503))
        Draft202012Validator(SCHEMA).validate(payload)
        ApiFailure.model_validate_json(json.dumps(payload, ensure_ascii=False))
        self.assertEqual(payload["schemaVersion"], "causora.contract.v1")
        self.assertEqual(payload["requestId"], request_id)
        self.assertEqual(payload["error"]["requestId"], request_id)
        self.assertEqual(payload["error"]["code"], code)
        self.assertEqual(payload["error"]["details"]["reason"], reason)
        self.assertNotIn("data", payload)
        self.assertNotIn("dataVersion", payload)
        self.assertNotIn("simulationId", json.dumps(payload))

    def test_pending_review_returns_v1_503_not_unreviewed_200(self):
        status, payload = simulate_v1_boundary(REQUEST, request_id="req-alignment-001", project_root=ROOT)
        self.assertEqual(status, 503)
        self.check_error(status, payload, code="simulation_failed",
                         reason="human_review_pending", request_id="req-alignment-001")

    def test_changed_demand_and_lead_are_accepted_but_never_return_stale_mock(self):
        request = copy.deepcopy(REQUEST)
        request["scenarios"][0].update(demandShock=-50, demandUnits24m=13000, leadTimeMultiplier=9)
        status, payload = simulate_v1_boundary(request, request_id="req-alignment-002", project_root=ROOT)
        self.check_error(status, payload, code="simulation_failed",
                         reason="human_review_pending", request_id="req-alignment-002")

    def test_fraction_units_unknown_fields_and_dataset_id_fail(self):
        cases = [
            {**REQUEST, "riskThreshold": 12},
            {**REQUEST, "budgetCeilingUsd": -1},
            {**REQUEST, "unexpected": True},
            {**REQUEST, "datasetId": "other"},
            {**REQUEST, "schemaVersion": "causora.contract.v2"},
        ]
        for n, request in enumerate(cases):
            with self.subTest(n=n):
                status, payload = simulate_v1_boundary(request, request_id=f"req-invalid-{n}", project_root=ROOT)
                self.assertEqual(status, 422)
                self.check_error(status, payload, code="validation_error",
                                 reason="invalid_input", request_id=f"req-invalid-{n}")

    def test_pending_review_folder_cannot_act_as_approved_bundle(self):
        bundle = ROOT / "evidence_day2/examples/pending_review"
        status, payload = simulate_v1_boundary(REQUEST, request_id="req-pending-bundle", project_root=ROOT,
                                               reviewed_bundle=bundle)
        self.assertEqual(status, 503)
        self.check_error(status, payload, code="simulation_failed",
                         reason="review_bundle_not_verified", request_id="req-pending-bundle")


if __name__ == "__main__":
    unittest.main()
