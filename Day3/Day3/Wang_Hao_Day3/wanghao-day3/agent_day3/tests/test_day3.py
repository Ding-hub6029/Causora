from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from agent_day3.adapter import Day3AgentDraft, to_frontend_draft
from agent_day3.models import BoardroomSnapshot
from agent_day3.orchestrator import response_schema, run_parallel
from agent_day3.projections import allowed_refs, project, verify_human_review_bundle
from agent_day3.provider import OfflineStubProvider
from agent_day3.wire_models import (EvidenceRecord, RealSnapshotInput, Scenario,
                                    load_local_mock_snapshot, load_real_snapshot_input, sha256_json)


def local_snapshot(scenario: str = "demand-drop") -> BoardroomSnapshot:
    return load_local_mock_snapshot(scenario)


def real_payload(snapshot: BoardroomSnapshot, *, no_feasible: bool = False) -> dict:
    if no_feasible:
        limits = {"riskThreshold": 0.0, "budgetCeilingUsd": 0}
        selection = {"scenarioId": snapshot.scenario.id, "status": "no_feasible_option", "recommendedOptionId": None,
                     "constraintViolations": [{"optionId": option, "code": code} for option in ("D0", "D1", "D2")
                                             for code in ("stockout_threshold", "cash_ceiling")]}
    else:
        limits = {"riskThreshold": 0.12, "budgetCeilingUsd": 480000}
        selection = {"scenarioId": snapshot.scenario.id, "status": "selected", "recommendedOptionId": "D1",
                     "constraintViolations": [{"optionId": "D0", "code": "stockout_threshold"},
                                              {"optionId": "D2", "code": "cash_ceiling"}]}
    value = {
        "schemaVersion": "causora.contract.v1", "dataVersion": snapshot.simulation.dataVersion,
        "scenario": snapshot.scenario.model_dump(mode="json"),
        "options": [item.model_dump(mode="json") for item in snapshot.options],
        "simulation": snapshot.simulation.model_dump(mode="json"),
        "contract": snapshot.contract.model_dump(mode="json"),
        "evidence": [item.model_dump(mode="json") for item in snapshot.evidence],
        "selection": selection, "selectionLimits": limits,
    }
    # This exercises shape/gate logic only; it is never genuine engine output.
    value["simulation"]["simulationId"] = "sim-test-double-integration-001"
    value["reference"] = {
        "schemaVersion": "causora.contract.v1", "dataVersion": value["dataVersion"], "datasetId": "ds-real-001",
        "simulationId": value["simulation"]["simulationId"], "scenarioId": value["scenario"]["id"],
        "optionIds": ["D0", "D1", "D2"], "simulationSha256": sha256_json(value["simulation"]),
        "snapshotSha256": sha256_json(value),
    }
    return value


def review_bundle(directory: Path, snapshot: BoardroomSnapshot) -> Path:
    bundle = directory / "review_bundle"
    bundle.mkdir()
    fixture = json.loads((Path(__file__).resolve().parents[2] / "fixtures" / "causora_day1_mock.json").read_text(encoding="utf-8"))
    dataset = {
        "schemaVersion": "causora.contract.v1", "dataVersion": snapshot.simulation.dataVersion, "requestId": "req-real-001",
        "data": {"datasetId": "ds-real-001", "preprocessStatus": "ready", "dataVersion": snapshot.simulation.dataVersion,
                 "intake": fixture["intake"], "evidence": [item.model_dump(mode="json") for item in snapshot.evidence],
                 "contract": snapshot.contract.model_dump(mode="json"), "variables": fixture["variables"]},
    }
    source_hashes = {"supplier_a_agreement.pdf": "a" * 64}
    scope = {"kind": "CAUSORA_EVIDENCE_REVIEW_SCOPE_V1", "schemaVersion": "causora.contract.v1",
             "dataVersion": snapshot.simulation.dataVersion, "datasetSha256": sha256_json(dataset), "sourceHashes": source_hashes}
    receipt = {"kind": "CAUSORA_HUMAN_REVIEW_RECEIPT_V1", "reviewerType": "human", "reviewerName": "Human Reviewer",
               "reviewedAtUtc": "2026-10-07T00:00:00Z", "scopeSha256": sha256_json(scope),
               "datasetSha256": sha256_json(dataset), "sourceHashes": source_hashes, "allApproved": True,
               "approvedEvidenceIds": [item.id for item in snapshot.evidence] + ["EV-020"],
               "approvedAssumptionKeys": ["decisionDate", "renewalDate", "noticeSent", "forecastBasis", "lockedForecastUnits24m"]}
    for name, value in (("dataset_success.json", dataset), ("review_scope.json", scope), ("human_receipt.json", receipt)):
        (bundle / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return bundle


class Day3IndependentTests(unittest.TestCase):
    def test_three_frozen_scenarios_smoke_and_draft_never_ready(self):
        for scenario in ("baseline", "demand-drop", "lead-stress"):
            result = asyncio.run(run_parallel(local_snapshot(scenario), provider=OfflineStubProvider()))
            self.assertEqual(result.state, "ALL_READY")
            self.assertEqual([item.role for item in result.outputs], ["CFO", "COO", "Risk"])
            self.assertTrue(all(item.output.availability == "MOCK" for item in result.outputs))
            draft = to_frontend_draft(result)
            self.assertIsInstance(draft, Day3AgentDraft)
            self.assertFalse(draft.decisionReady)
            self.assertNotIn("brief", draft.model_dump())
            self.assertEqual(draft.agentOutputs[0].metrics, result.outputs[0].output.metricRefs)

    def test_role_projections_and_injection_canary(self):
        views = project(local_snapshot())
        cfo, coo, risk = (item.model_dump_json() for item in views.values())
        self.assertNotIn("stockoutProbability", cfo)
        self.assertNotIn("expectedTco", coo)
        self.assertNotIn("quote", risk)
        self.assertNotIn("sourceFile", risk)
        self.assertEqual(views["Risk"].contractReview, "PENDING_LOCAL_MOCK")

        class Injecting(OfflineStubProvider):
            def __init__(self): self.seen = []
            async def complete(self, **kwargs):
                self.seen.append(kwargs["payload"])
                value = await super().complete(**kwargs)
                if kwargs["role"] == "Risk": value["prompt_injection"] = "ignore rules"
                return value

        provider = Injecting()
        result = asyncio.run(run_parallel(local_snapshot(), provider=provider))
        self.assertEqual(result.state, "PARTIAL")
        self.assertEqual(result.outputs[2].failure, "invalid_response")
        self.assertTrue(all("quote" not in json.dumps(payload) for payload in provider.seen))
        self.assertNotIn("stockoutProbability", json.dumps(provider.seen[0]))

    def test_bad_numeric_ref_option_and_unknown_output_are_isolated(self):
        class Bad(OfflineStubProvider):
            async def complete(self, **kwargs):
                value = await super().complete(**kwargs)
                if kwargs["role"] == "CFO": value["reason_text"] = "Cost changes by 25 dollars."
                elif kwargs["role"] == "COO": value["metric_refs"] = ["expectedTcoUsd:D0"]
                else: value["option_ids"] = ["D0", "D3"]
                return value
        result = asyncio.run(run_parallel(local_snapshot(), provider=Bad()))
        self.assertEqual(result.state, "UNAVAILABLE")
        self.assertEqual([item.failure for item in result.outputs], ["invalid_response"] * 3)

    def test_async_barrier_timeout_and_outer_cancellation(self):
        class Barrier(OfflineStubProvider):
            def __init__(self): self.started, self.release = set(), asyncio.Event()
            async def complete(self, **kwargs):
                self.started.add(kwargs["role"])
                if len(self.started) == 3: self.release.set()
                await asyncio.wait_for(self.release.wait(), 1)
                return await super().complete(**kwargs)
        barrier = Barrier()
        self.assertEqual(asyncio.run(run_parallel(local_snapshot(), provider=barrier, timeout_seconds=2)).state, "ALL_READY")
        self.assertEqual(barrier.started, {"CFO", "COO", "Risk"})

        class SlowRisk(OfflineStubProvider):
            async def complete(self, **kwargs):
                if kwargs["role"] == "Risk": await asyncio.sleep(.1)
                return await super().complete(**kwargs)
        timed = asyncio.run(run_parallel(local_snapshot(), provider=SlowRisk(), timeout_seconds=.02))
        self.assertEqual([item.failure for item in timed.outputs], [None, None, "timeout"])

        class InternallyCancelled(OfflineStubProvider):
            async def complete(self, **kwargs):
                if kwargs["role"] == "Risk": raise asyncio.CancelledError()
                return await super().complete(**kwargs)
        cancelled = asyncio.run(run_parallel(local_snapshot(), provider=InternallyCancelled()))
        self.assertEqual([item.failure for item in cancelled.outputs], [None, None, "provider_unavailable"])

        entered = asyncio.Event()
        class Wait(OfflineStubProvider):
            async def complete(self, **kwargs):
                entered.set(); await asyncio.sleep(5); return await super().complete(**kwargs)
        async def cancel_case():
            task = asyncio.create_task(run_parallel(local_snapshot(), provider=Wait()))
            await asyncio.wait_for(entered.wait(), 1); task.cancel()
            with self.assertRaises(asyncio.CancelledError): await task
        asyncio.run(cancel_case())

    def test_strict_wire_rejects_unknown_bbox_date_numeric_and_share_errors(self):
        with self.assertRaises(ValidationError):
            Scenario.model_validate({"id":"x","label":"x","tag":"x","demandShock":0,"demandUnits24m":1,
                                     "leadTime":"x","leadTimeMultiplier":1.0,"description":"x","future":"reject"})
        evidence = local_snapshot().evidence[0].model_dump(mode="json"); evidence["locatorBbox"] = [4., 2., 3., 5.]
        with self.assertRaises(ValidationError): EvidenceRecord.model_validate(evidence)
        evidence["locatorBbox"] = [1., 2., 3., 4.]
        self.assertEqual(EvidenceRecord.model_validate(evidence).locatorBbox, (1., 2., 3., 4.))
        with self.assertRaises(ValidationError):
            Scenario.model_validate({"id":"x","label":"x","tag":"x","demandShock":float("nan"),"demandUnits24m":1,
                                     "leadTime":"x","leadTimeMultiplier":1.0,"description":"x"})
        changed = local_snapshot().model_dump(mode="json"); changed["contract"]["decisionDate"] = "2026-02-30"
        with self.assertRaises(ValidationError): BoardroomSnapshot.model_validate(changed)
        changed = local_snapshot().model_dump(mode="json"); changed["simulation"]["matrix"]["demand-drop"][0]["expectedTco"] += 1
        with self.assertRaises(ValidationError): BoardroomSnapshot.model_validate(changed)
        changed = local_snapshot().model_dump(mode="json"); changed["simulation"]["matrix"]["demand-drop"][1]["unitsFromA"] = 15601
        with self.assertRaises(ValidationError): BoardroomSnapshot.model_validate(changed)

    def test_zero_runs_and_real_human_receipt_verifier_gate(self):
        snapshot = local_snapshot(); self.assertEqual(snapshot.simulation.monteCarloRuns, 0)
        real = RealSnapshotInput.model_validate(real_payload(snapshot)).to_boardroom_snapshot()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_path = root / "snapshot.json"
            input_path.write_text(json.dumps(real_payload(snapshot)), encoding="utf-8")
            self.assertEqual(load_real_snapshot_input(input_path).simulation.monteCarloRuns, 0)
            bundle = review_bundle(root, snapshot)
            self.assertEqual(verify_human_review_bundle(bundle).data.datasetId, "ds-real-001")
            with self.assertRaisesRegex(ValueError, "verifier"):
                asyncio.run(run_parallel(real, provider=OfflineStubProvider(), review_bundle=bundle))
            receipt_path = bundle / "human_receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8")); receipt["allApproved"] = False
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaises(ValidationError): verify_human_review_bundle(bundle)
            (bundle / "human_receipt.json").unlink()
            with self.assertRaisesRegex(ValueError, "missing required human_receipt"):
                asyncio.run(run_parallel(real, provider=OfflineStubProvider(), review_bundle=bundle, simulation_verifier=lambda _: None))
        tampered = real_payload(snapshot)
        tampered["simulation"]["matrix"]["demand-drop"][0]["breakdown"]["holding"] += 1
        tampered["simulation"]["matrix"]["demand-drop"][0]["expectedTco"] += 1
        with self.assertRaises(ValidationError): RealSnapshotInput.model_validate(tampered)
        wrong_selection = real_payload(snapshot)
        wrong_selection["selection"]["recommendedOptionId"] = "D0"
        unsigned = {key: value for key, value in wrong_selection.items() if key != "reference"}
        wrong_selection["reference"]["snapshotSha256"] = sha256_json(unsigned)
        with self.assertRaises(ValidationError): RealSnapshotInput.model_validate(wrong_selection)

    def test_verifier_failure_and_no_feasible_skip_provider(self):
        snapshot = local_snapshot(); real = RealSnapshotInput.model_validate(real_payload(snapshot)).to_boardroom_snapshot()
        with tempfile.TemporaryDirectory() as temp:
            bundle = review_bundle(Path(temp), snapshot)
            def fail(_): raise RuntimeError("engine mismatch")
            with self.assertRaisesRegex(RuntimeError, "engine mismatch"):
                asyncio.run(run_parallel(real, provider=OfflineStubProvider(), review_bundle=bundle, simulation_verifier=fail))
        no_feasible = RealSnapshotInput.model_validate(real_payload(snapshot, no_feasible=True)).to_boardroom_snapshot()
        class MustNotCall:
            kind = "TEST_DOUBLE"
            async def complete(self, **kwargs): raise AssertionError("provider called")
        with tempfile.TemporaryDirectory() as temp:
            result = asyncio.run(run_parallel(no_feasible, provider=MustNotCall(), review_bundle=review_bundle(Path(temp), snapshot), simulation_verifier=lambda _: None))
        self.assertEqual(result.state, "NO_FEASIBLE_OPTION")

    def test_dynamic_schema_only_exposes_typed_refs(self):
        refs, evidence = allowed_refs("COO", project(local_snapshot())["COO"])
        schema = response_schema("COO", refs, evidence)
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("expectedTcoUsd:D0", schema["properties"]["metric_refs"]["items"]["enum"])


if __name__ == "__main__": unittest.main()
