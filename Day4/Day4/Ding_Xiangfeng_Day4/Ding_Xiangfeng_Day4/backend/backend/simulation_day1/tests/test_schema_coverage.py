from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import jsonschema
from pydantic import ValidationError

from simulation_day1.build_day1_schemas import FROZEN_SOURCE_HASHES, build_manifest, source_hash
from simulation_day1.source_models import DemoInputs
from simulation_day1.wire_models import (
    ApiFailure, BoardroomRequest, BoardroomSuccess, DatasetSuccess,
    EvidenceSuccess, GoldenRun, GoldenSuccess, HealthSuccess,
    MockData, SimulateRequest, SimulateSuccess,
)

ROOT = Path(__file__).resolve().parents[2]
DAY1 = ROOT / "simulation_day1"
SCHEMAS = DAY1 / "schemas"
MOCK = json.loads((ROOT / "demo_data" / "causora_day1_mock.json").read_text(encoding="utf-8"))


def check_schema(name: str, payload: dict) -> None:
    schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(payload)


class CoverageTests(unittest.TestCase):
    def test_unmodified_static_mock_and_golden_snapshot(self):
        MockData.model_validate_json(json.dumps(MOCK))
        check_schema("mock_data_v1.schema.json", MOCK)
        golden = json.loads((ROOT / "golden" / "golden_run.json").read_text(encoding="utf-8"))
        GoldenRun.model_validate_json(json.dumps(golden))
        check_schema("golden_success_v1.schema.json", {"schemaVersion": "causora.contract.v1",
            "dataVersion": MOCK["meta"]["dataVersion"], "requestId": "req-local-mock", "data": golden})
        self.assertEqual(golden["request"]["riskThreshold"], 12)  # local slider %, NOT API's 0.12

    def test_all_synthetic_inputs_and_hashes(self):
        manifest = build_manifest()
        self.assertEqual(manifest, json.loads((DAY1 / "demo_inputs_v1.json").read_text(encoding="utf-8")))
        DemoInputs.model_validate_json(json.dumps(manifest))
        check_schema("demo_inputs_v1.schema.json", manifest)
        self.assertEqual((manifest["historicalDemand"]["totalUnits"], manifest["contractAssumptions"]["lockedForecastUnits24m"]), (25936, 26000))
        self.assertEqual((manifest["supplierDelivery"]["orderCount"], manifest["openingInventory"]["unitsOnHand"]), (48, 1840))
        self.assertEqual({s:sum(o["supplier"] == s for o in manifest["supplierDelivery"]["orders"]) for s in ("A","B")}, {"A":36,"B":12})
        self.assertFalse(manifest["noticeRegister"]["noticeSent"])
        self.assertFalse(manifest["contractAssumptions"]["humanReviewed"])
        for section in ("historicalDemand", "supplierDelivery", "openingInventory", "noticeRegister", "contractAssumptions"):
            entry = manifest[section]
            self.assertEqual(entry["sourceSha256"], hashlib.sha256((ROOT / entry["sourceFile"]).read_bytes()).hexdigest())

    def test_changed_source_requires_data_version_review(self):
        source = "public/demo/opening_inventory.csv"
        with patch.dict(FROZEN_SOURCE_HASHES, {source: "0" * 64}):
            with self.assertRaisesRegex(ValueError, "increment dataVersion"):
                source_hash(source)

    def test_simulate_request_success_no_feasible_and_failure(self):
        for stem in ("simulate_request", "simulate_request_no_feasible"):
            raw = json.loads((DAY1 / "examples" / f"{stem}.json").read_text(encoding="utf-8"))
            SimulateRequest.model_validate_json(json.dumps(raw))
            check_schema("simulate_request_v1.schema.json", raw)
        for stem in ("simulate_response_LOCAL_MOCK", "simulate_response_no_feasible_LOCAL_MOCK"):
            raw = json.loads((DAY1 / "examples" / f"{stem}.json").read_text(encoding="utf-8"))
            SimulateSuccess.model_validate_json(json.dumps(raw))
            check_schema("simulate_success_v1.schema.json", raw)
            self.assertEqual(raw["data"]["simulation"]["monteCarloRuns"], 0)
        failure = json.loads((DAY1 / "examples" / "simulate_error_not_computed.json").read_text(encoding="utf-8"))
        ApiFailure.model_validate_json(json.dumps(failure))
        check_schema("api_failure_v1.schema.json", failure)

    def test_other_contract_envelopes_are_typed_without_live_endpoints(self):
        version = MOCK["meta"]["dataVersion"]
        def wrap(data):
            return {"schemaVersion": "causora.contract.v1", "dataVersion": version,
                    "requestId": "req-static-shape-test", "data": data}
        dataset = wrap({"datasetId": "ds-001", "preprocessStatus": "ready", "dataVersion": version,
                        "intake": MOCK["intake"], "evidence": MOCK["evidence"],
                        "contract": MOCK["contract"], "variables": MOCK["variables"]})
        DatasetSuccess.model_validate_json(json.dumps(dataset))
        check_schema("dataset_success_v1.schema.json", dataset)
        evidence = wrap({"evidence": MOCK["evidence"][0]})
        EvidenceSuccess.model_validate_json(json.dumps(evidence))
        check_schema("evidence_success_v1.schema.json", evidence)
        board_request = {"schemaVersion": "causora.contract.v1", "simulationId": "sim-day1-mock-0001",
                         "dataVersion": version, "scenarioId": "baseline"}
        BoardroomRequest.model_validate_json(json.dumps(board_request))
        check_schema("boardroom_request_v1.schema.json", board_request)
        selected_brief = {**MOCK["brief"], "scenarioId": "baseline", "status": "selected"}
        boardroom = wrap({"scenarioId": "baseline", "agentOutputs": MOCK["boardroom"],
                          "criticIssues": [MOCK["critic"]], "brief": selected_brief,
                          "numericGuardrail": {"passed": True, "rejectedClaims": []}})
        BoardroomSuccess.model_validate_json(json.dumps(boardroom))
        check_schema("boardroom_success_v1.schema.json", boardroom)
        no_feasible = copy.deepcopy(boardroom)
        no_feasible["data"] = {"scenarioId": "baseline", "agentOutputs": [], "criticIssues": [],
            "brief": {"scenarioId": "baseline", "status": "no_feasible_option",
                      "recommendedOptionId": None, "constraintViolations": [],
                      "message": "No option satisfies all constraints."},
            "numericGuardrail": {"passed": True, "rejectedClaims": []}}
        BoardroomSuccess.model_validate_json(json.dumps(no_feasible))
        check_schema("boardroom_success_v1.schema.json", no_feasible)
        health = wrap({"service": "unavailable", "simulation": "unavailable",
                       "evidence": "unavailable", "provider": "unavailable"})
        HealthSuccess.model_validate_json(json.dumps(health))
        check_schema("health_success_v1.schema.json", health)

    def test_reject_fabricated_or_malformed_wire_values(self):
        raw = json.loads((DAY1 / "examples" / "simulate_request.json").read_text(encoding="utf-8"))
        bad = copy.deepcopy(raw); bad["riskThreshold"] = 12
        with self.assertRaises(ValidationError): SimulateRequest.model_validate_json(json.dumps(bad))
        with self.assertRaises(jsonschema.ValidationError): check_schema("simulate_request_v1.schema.json", bad)
        bad = copy.deepcopy(raw); bad["options"][1]["shareA"] = 0.61
        with self.assertRaises(ValidationError): SimulateRequest.model_validate_json(json.dumps(bad))
        bad = copy.deepcopy(raw); bad["newWireField"] = True
        with self.assertRaises(ValidationError): SimulateRequest.model_validate_json(json.dumps(bad))
        with self.assertRaises(jsonschema.ValidationError): check_schema("simulate_request_v1.schema.json", bad)
        bad = copy.deepcopy(MOCK); bad["evidence"][0]["quoteMatched"] = True; bad["evidence"][0]["extractedValue"] = "999 days"
        with self.assertRaises(ValidationError): MockData.model_validate_json(json.dumps(bad))
        bad = build_manifest(); bad["contractAssumptions"]["humanReviewed"] = True
        with self.assertRaises(ValidationError): DemoInputs.model_validate_json(json.dumps(bad))
        with self.assertRaises(jsonschema.ValidationError): check_schema("demo_inputs_v1.schema.json", bad)


if __name__ == "__main__":
    unittest.main()
