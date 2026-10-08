from __future__ import annotations

import copy
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from pydantic import ValidationError

import app.service as service
from app.contracts_v2 import ApiSuccessV2
from app.release_verifiers import REQUIRED_POLICY_TOPICS, FIELD_PLAN, verify_reviewed_bundle_record, VerificationError
from simulation_day3.monte_carlo import run_reviewed_monte_carlo
from simulation_day3.policy import Day3Policy

ROOT = Path(__file__).resolve().parents[1]
REQUEST = json.loads((ROOT / "examples/simulate_request_v1.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "simulation_day3/examples/UNAPPROVED_MC_POLICY.json").read_text(encoding="utf-8"))
CONTRACT = json.loads((ROOT / "demo_data/causora_day1_mock.json").read_text(encoding="utf-8"))["contract"]


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha_canonical(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _approvals() -> list[dict]:
    return [{"role": role, "actorId": f"fixture-{role}", "decision": "approved", "recordedAtUtc": "2026-10-07T00:00:00Z"}
            for role in ("simulation_owner", "frontend_owner", "review_owner")]


def _configure_verified_fixture(monkeypatch: pytest.MonkeyPatch, base: Path, *, contract: dict | None = None,
                                data_version: str = "TEST_FIXTURE_ONLY-reviewed-v1") -> dict:
    """File-backed test stand-in. It is never a human review or production approval."""
    base.mkdir(parents=True, exist_ok=True)
    contract = copy.deepcopy(contract or CONTRACT)
    review_dir = base / "review"; review_dir.mkdir()
    provenance = {key: {"evidenceId": evidence, "sourceFile": file, "sourceSha256": _sha_file(ROOT / file),
                        "reviewItemId": deps[0], "derivedFromReviewItemIds": deps, "status": "reviewed"}
                  for key, (evidence, file, deps) in FIELD_PLAN.items()}
    confirmed = {"EV-014": contract["renewalNoticeDays"], "EV-019": contract["renewalTermMonths"],
                 "EV-021": contract["renewalPriceIncreasePct"], "EV-024": contract["minPurchaseShareA"],
                 "EV-027": contract["terminationFeeUsd"], "EV-020": True,
                 **{key: contract[key] for key in ("decisionDate", "renewalDate", "noticeSent", "forecastBasis", "lockedForecastUnits24m")}}
    _write_json(review_dir / "reviewed_contract.json", {
        "kind": "causora.wang.reviewed-contract-bundle.v1", "datasetId": "ds-001", "dataVersion": data_version,
        "contract": contract, "contractSource": {"sourceFile": "public/demo/supplier_a_agreement.pdf", "sourceSha256": _sha_file(ROOT / "public/demo/supplier_a_agreement.pdf")},
        "fieldProvenance": provenance,
    })
    _write_json(review_dir / "review_record.json", {
        "kind": "causora.wang.review-record.v1", "status": "reviewed", "reviewId": f"fixture-review-{data_version}",
        "reviewerRole": "contract_reviewer", "reviewerId": "fixture-wang", "recordedAtUtc": "2026-10-07T00:00:00Z",
        "contractPayloadSha256": _sha_canonical(contract), "fieldProvenanceSha256": _sha_canonical(provenance),
        "reviewedItems": [{"id": key, "status": "reviewed", "confirmedValue": value} for key, value in confirmed.items()],
    })
    policy = copy.deepcopy(POLICY)
    policy["policyStatus"] = "TEAM_APPROVED"
    policy["operatingPolicy"]["assumptionStatus"] = "TEAM_APPROVED"
    policy["supplierBLeadFallback"]["provenance"] = "TEAM_APPROVED_ASSUMPTION"
    policy_file = base / "team_policy_TEST_FIXTURE_ONLY.json"; _write_json(policy_file, policy)
    policy_record = base / "policy_approval_TEST_FIXTURE_ONLY.json"
    _write_json(policy_record, {"kind": "causora.day3.policy-approval-record.v1", "status": "approved",
                                "approvalRecordId": "fixture-policy-approval", "policyConfigurationId": "fixture-policy-config-v1",
                                "policySha256": _sha_file(policy_file), "confirmedTopics": sorted(REQUIRED_POLICY_TOPICS), "approvals": _approvals()})
    common, types, validator = (base / "API_CONTRACT_TEST_FIXTURE_ONLY.md", base / "types_TEST_FIXTURE_ONLY.ts", base / "validator_TEST_FIXTURE_ONLY.ts")
    common.write_text("fixture common v2", encoding="utf-8"); types.write_text("fixture types v2", encoding="utf-8"); validator.write_text("fixture validator v2", encoding="utf-8")
    artifacts = {"backendJsonSchema": _sha_file(ROOT / "contracts/causora.contract.v2.schema.json"),
                 "pythonPydanticModel": _sha_file(ROOT / "app/contracts_v2.py"), "commonApiContract": _sha_file(common),
                 "typescriptTypes": _sha_file(types), "frontendValidator": _sha_file(validator)}
    release = base / "trace_release_TEST_FIXTURE_ONLY.json"
    _write_json(release, {"kind": "causora.trace-contract-release-record.v1", "status": "released",
                          "schemaVersion": "causora.contract.v2", "traceSchemaVersion": "causora.formula-trace.v1",
                          "contractApprovalReference": "fixture-trace-release", "artifacts": artifacts, "approvals": _approvals()})
    for name, value in {
        "CAUSORA_REVIEW_BUNDLE_DIR": review_dir, "CAUSORA_APPROVED_POLICY_PATH": policy_file,
        "CAUSORA_POLICY_APPROVAL_RECORD_PATH": policy_record, "CAUSORA_TRACE_CONTRACT_V2_RELEASE_RECORD": release,
        "CAUSORA_COMMON_API_CONTRACT_PATH": common, "CAUSORA_TYPESCRIPT_V2_TYPES_PATH": types,
        "CAUSORA_FRONTEND_V2_VALIDATOR_PATH": validator, "CAUSORA_TRACE_ARTIFACT_DIR": base / "audit",
    }.items(): monkeypatch.setenv(name, str(value))
    return {"contract": contract, "policy": policy}


def test_invalid_request_is_v1_422_before_any_gate():
    request = copy.deepcopy(REQUEST); request["riskThreshold"] = 2
    response = TestClient(service.app).post("/api/simulate", json=request).json()
    assert response["schemaVersion"] == "causora.contract.v1" and response["error"]["details"]["reason"] == "invalid_input"


def test_default_gate_lists_review_and_policy_missing(monkeypatch):
    monkeypatch.delenv("CAUSORA_DEV_UNREVIEWED_MODE", raising=False)
    for name in ("CAUSORA_REVIEW_BUNDLE_DIR", "CAUSORA_APPROVED_POLICY_PATH", "CAUSORA_POLICY_APPROVAL_RECORD_PATH", "CAUSORA_TRACE_CONTRACT_V2_RELEASE_RECORD", "CAUSORA_COMMON_API_CONTRACT_PATH", "CAUSORA_TYPESCRIPT_V2_TYPES_PATH", "CAUSORA_FRONTEND_V2_VALIDATOR_PATH"):
        monkeypatch.delenv(name, raising=False)
    response = TestClient(service.app).post("/api/simulate", json=REQUEST, headers={"Origin": "http://localhost:3000"})
    body = response.json()
    assert response.status_code == 503 and body["schemaVersion"] == "causora.contract.v1"
    assert body["error"]["details"]["reason"] == "human_review_pending"
    assert {"human_review_pending", "simulation_policy_unapproved"} <= set(body["error"]["details"]["missingReasons"])
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_health_reports_real_pending_status_without_fake_readiness(monkeypatch):
    monkeypatch.delenv("CAUSORA_DEV_UNREVIEWED_MODE", raising=False)
    for name in ("CAUSORA_REVIEW_BUNDLE_DIR", "CAUSORA_APPROVED_POLICY_PATH", "CAUSORA_POLICY_APPROVAL_RECORD_PATH"):
        monkeypatch.delenv(name, raising=False)
    response = TestClient(service.app).get("/health")
    assert response.status_code == 200
    assert response.json()["data"]["simulation"] == "review_pending"


def test_policy_model_rejects_mismatched_self_declared_approval():
    invalid = copy.deepcopy(POLICY); invalid["policyStatus"] = "TEAM_APPROVED"
    with pytest.raises(Exception): Day3Policy.model_validate(invalid)


def test_policy_flag_without_separate_record_is_rejected(monkeypatch, tmp_path):
    policy = copy.deepcopy(POLICY); policy["policyStatus"] = "TEAM_APPROVED"; policy["operatingPolicy"]["assumptionStatus"] = "TEAM_APPROVED"; policy["supplierBLeadFallback"]["provenance"] = "TEAM_APPROVED_ASSUMPTION"
    policy_file = tmp_path / "policy.json"; _write_json(policy_file, policy)
    monkeypatch.setenv("CAUSORA_APPROVED_POLICY_PATH", str(policy_file)); monkeypatch.delenv("CAUSORA_POLICY_APPROVAL_RECORD_PATH", raising=False)
    assert "simulation_policy_unapproved" in service._gate_status().missing_reasons


def test_only_exact_dev_literal_bypasses_gates_for_unreviewed_integration(monkeypatch):
    monkeypatch.setenv("CAUSORA_DEV_UNREVIEWED_MODE", "true")
    rejected = TestClient(service.app).post("/api/simulate", json=REQUEST)
    assert rejected.status_code == 503
    monkeypatch.setenv("CAUSORA_DEV_UNREVIEWED_MODE", "UNREVIEWED_DEV_ONLY")
    response = TestClient(service.app).post("/api/simulate", json=REQUEST, headers={"X-Request-Id": "req-unreviewed-dev"})
    body = response.json()
    assert response.status_code == 200 and body["schemaVersion"] == "causora.contract.v2"
    assert body["requestId"] == "req-unreviewed-dev"
    context = body["data"]["executionContext"]
    assert context == {
        "mode": "unreviewed_development_only", "banner": __import__("app.unreviewed_development", fromlist=["DEV_BANNER"]).DEV_BANNER,
        "humanReviewStatus": "not_reviewed_development_only", "policyStatus": "unapproved_development_only",
        "contractReleaseStatus": "not_released_development_only", "decisionReady": False,
    }
    assert "UNREVIEWED_DEV_ONLY" in body["data"]["simulation"]["dataVersion"]
    trace = body["data"]["traces"]["baseline"]["D1"]
    assert trace["runIdentity"]["executionMode"] == "unreviewed_development_only"
    assert trace["runIdentity"]["reviewRecordId"] is None
    assert next(p for p in trace["parameters"] if p["key"] == "contract.terminationFeeUsd")["provenance"]["kind"] == "unreviewed_development_contract"
    assert response.headers["x-causora-review-status"] == "unreviewed-development-only"
    assert response.headers["x-causora-execution-mode"] == "unreviewed-development-only"
    health = TestClient(service.app).get("/health")
    assert health.json()["data"]["simulation"] == "unreviewed_development_only"


def test_real_file_backed_gates_return_schema_valid_v2_and_nine_traces(monkeypatch, tmp_path):
    _configure_verified_fixture(monkeypatch, tmp_path)
    response = TestClient(service.app).post("/api/simulate", json=REQUEST, headers={"X-Request-Id": "req-test-fixture"})
    body = response.json()
    assert response.status_code == 200 and body["schemaVersion"] == "causora.contract.v2" and body["requestId"] == "req-test-fixture"
    assert len(body["data"]["deltas"]) == 9 and sum(len(v) for v in body["data"]["traces"].values()) == 9
    Draft202012Validator(json.loads((ROOT / "contracts/causora.contract.v2.schema.json").read_text(encoding="utf-8"))).validate(body)
    assert list((tmp_path / "audit").glob("sim-*.json"))


def test_reviewed_contract_change_and_demand_change_trigger_real_recalculation(monkeypatch, tmp_path):
    _configure_verified_fixture(monkeypatch, tmp_path / "one")
    first = TestClient(service.app).post("/api/simulate", json=REQUEST).json()
    # The five commercial terms are freshly checked against the packaged source
    # PDF at registration time, so changing the termination fee alone would be
    # rightly rejected as unsupported source evidence. Change the reviewed
    # notice state instead: it is a separately reviewed operational field and
    # legitimately changes the renewal/termination calculation.
    changed_contract = copy.deepcopy(CONTRACT)
    changed_contract["noticeSent"] = True
    changed_contract["renewalLocked"] = False
    _configure_verified_fixture(monkeypatch, tmp_path / "two", contract=changed_contract, data_version="TEST_FIXTURE_ONLY-reviewed-v2")
    second = TestClient(service.app).post("/api/simulate", json=REQUEST).json()
    d2 = lambda result: next(cell for cell in result["data"]["simulation"]["matrix"]["baseline"] if cell["optionId"] == "D2")
    assert d2(first)["breakdown"]["terminationFee"] == CONTRACT["terminationFeeUsd"]
    assert d2(second)["breakdown"]["terminationFee"] == 0
    assert second["data"]["simulation"]["simulationId"] != first["data"]["simulation"]["simulationId"]
    changed_request = copy.deepcopy(REQUEST)
    for scenario, shock in zip(changed_request["scenarios"], (10, -20, 15), strict=True):
        scenario["demandShock"] = shock; scenario["demandUnits24m"] = round(CONTRACT["lockedForecastUnits24m"] * (1 + shock / 100))
    rerun = TestClient(service.app).post("/api/simulate", json=changed_request).json()
    assert rerun["data"]["simulation"]["simulationId"] != second["data"]["simulation"]["simulationId"]
    assert rerun["data"]["simulation"]["matrix"]["baseline"] != second["data"]["simulation"]["matrix"]["baseline"]


def test_all_trace_statistics_components_references_and_rounding_audits_reconcile(monkeypatch, tmp_path):
    _configure_verified_fixture(monkeypatch, tmp_path)
    body = TestClient(service.app).post("/api/simulate", json=REQUEST).json()
    for scenario_id, options in body["data"]["traces"].items():
        matrix = {cell["optionId"]: cell for cell in body["data"]["simulation"]["matrix"][scenario_id]}
        for option_id, trace in options.items():
            cell = matrix[option_id]; keys = {parameter["key"] for parameter in trace["parameters"]}
            assert (trace["simulationId"], trace["dataVersion"], trace["formulaVersion"], trace["scenarioId"], trace["optionId"]) == (body["data"]["simulation"]["simulationId"], body["data"]["simulation"]["dataVersion"], "tco-v1", scenario_id, option_id)
            assert {part["key"]: part["valueUsd"] for part in trace["components"]} == cell["breakdown"]
            assert all(set(part["inputKeys"]) <= keys for part in trace["components"])
            assert trace["stockoutProbability"]["value"] == cell["stockoutProbability"] and trace["serviceLevel"]["value"] == cell["serviceLevel"] and trace["cashOutflowP90"]["valueUsd"] == cell["cashOutflowP90"]
            assert len(trace["samplePath"]["weeks"]) == 104 and trace["samplePath"]["classification"] == "single_realised_trial_not_aggregate"
            for part in trace["components"]:
                audit = part["roundingAudit"]
                assert Decimal(audit["displayedMinusRawMeanUsd"]) == Decimal(part["valueUsd"]) - Decimal(audit["rawMeanUsd"])
            contract_parameter = next(x for x in trace["parameters"] if x["key"] == "contract.terminationFeeUsd")
            assert contract_parameter["provenance"]["sourceSha256"] != contract_parameter["provenance"]["reviewRecordSha256"]
    tampered = copy.deepcopy(body); tampered["data"]["traces"]["baseline"]["D1"]["components"][0]["valueUsd"] += 1
    with pytest.raises(ValidationError): ApiSuccessV2.model_validate(tampered)


def test_zero_revenue_no_feasible_and_execution_failure_have_explicit_handling(monkeypatch, tmp_path):
    fixture = _configure_verified_fixture(monkeypatch, tmp_path)
    zero = copy.deepcopy(REQUEST); zero["riskThreshold"] = 0; zero["budgetCeilingUsd"] = 0
    for scenario in zero["scenarios"]: scenario["demandShock"] = -100; scenario["demandUnits24m"] = 0
    raw = run_reviewed_monte_carlo(zero, fixture["policy"], reviewed_contract=fixture["contract"], reviewed_data_version="TEST_FIXTURE_ONLY-zero", project_root=ROOT)
    assert all(t["grossMarginStatus"] == "INVALID_REVENUE_ZERO" for traces in raw["formulaTraces"].values() for t in traces.values())
    body = TestClient(service.app).post("/api/simulate", json=zero).json()
    assert all(x["status"] == "no_feasible_option" for x in body["data"]["selections"].values())
    monkeypatch.setattr(service, "build_reviewed_success_v2", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("fixture")))
    failed = TestClient(service.app).post("/api/simulate", json=REQUEST).json()
    assert failed["schemaVersion"] == "causora.contract.v1" and failed["error"]["details"]["reason"] == "reviewed_simulation_execution_failed"


@pytest.mark.parametrize("mutation", ["source", "ids", "dependencies", "value", "confirmation", "path"])
def test_review_rejects_source_dependency_and_confirmation_tampering(monkeypatch, tmp_path, mutation):
    _configure_verified_fixture(monkeypatch, tmp_path)
    folder = tmp_path / "review"
    bundle = json.loads((folder / "reviewed_contract.json").read_text(encoding="utf-8"))
    record = json.loads((folder / "review_record.json").read_text(encoding="utf-8"))
    if mutation == "source": bundle["fieldProvenance"]["decisionDate"]["sourceSha256"] = "0" * 64
    if mutation == "ids": record["reviewedItems"][0]["id"] = "arbitrary-id"
    if mutation == "dependencies": bundle["fieldProvenance"]["renewalLocked"]["derivedFromReviewItemIds"] = ["EV-020"]
    if mutation == "value": record["reviewedItems"][0]["confirmedValue"] = 123456
    if mutation == "confirmation": record["humanConfirmationSource"] = {"sourceFile": "missing.docx", "sourceSha256": "0" * 64}
    if mutation == "path": bundle["contractSource"]["sourceFile"] = "../outside.pdf"
    record["fieldProvenanceSha256"] = _sha_canonical(bundle["fieldProvenance"])
    _write_json(folder / "reviewed_contract.json", bundle); _write_json(folder / "review_record.json", record)
    with pytest.raises(VerificationError): verify_reviewed_bundle_record(project_root=ROOT, bundle_path=folder)


def test_demand_bootstrap_is_a_required_policy_confirmation():
    assert len(REQUIRED_POLICY_TOPICS) == 15 and "demand_bootstrap" in REQUIRED_POLICY_TOPICS
