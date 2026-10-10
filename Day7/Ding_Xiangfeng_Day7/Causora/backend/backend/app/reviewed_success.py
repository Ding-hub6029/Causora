"""Build the real, release-gated Matrix + Formula Trace v2 response."""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT, TRACE_SCHEMA_VERSION, trace_artifact_dir
from app.contracts_v2 import ApiSuccessV2, REVIEWED_EXECUTION_MODE
from app.gates import GateResult, TraceContractReleaseResult
from app.portable_io import write_json_utf8_lf
from simulation_day1.interfaces import check_accounting, select_by_scenario
from simulation_day3.monte_carlo import run_reviewed_monte_carlo


def _decimal_text(value: Decimal | str | int) -> str:
    return format(Decimal(str(value)), "f")


def _provenance(kind: str, status: str, source_id: str, note: str, *, source_file: str | None = None,
                source_sha256: str | None = None, evidence_ids: list[str] | None = None,
                review_record_id: str | None = None, review_record_sha256: str | None = None) -> dict[str, Any]:
    return {
        "kind": kind, "status": status, "sourceId": source_id, "sourceFile": source_file,
        "sourceSha256": source_sha256, "evidenceIds": evidence_ids or [],
        "reviewRecordId": review_record_id, "reviewRecordSha256": review_record_sha256, "note": note,
    }


def _reviewed_field_provenance(gate: GateResult, field: str) -> dict[str, Any]:
    entry = gate.field_provenance[field]
    return _provenance(
        "reviewed_contract", "reviewed", str(entry["evidenceId"]),
        f"Reviewed contract field '{field}' bound to evidence {entry['evidenceId']} and review item {entry['reviewItemId']}.",
        source_file=str(entry["sourceFile"]), source_sha256=str(entry["sourceSha256"]), evidence_ids=[str(entry["evidenceId"])],
        review_record_id=gate.review_reference, review_record_sha256=gate.review_record_sha256,
    )


def _rounding_audit(raw_mean: str, displayed_value: int, method: str) -> dict[str, Any]:
    raw = Decimal(raw_mean)
    return {
        "rawMeanUsd": _decimal_text(raw),
        "displayedValueUsd": displayed_value,
        "displayedMinusRawMeanUsd": _decimal_text(Decimal(displayed_value) - raw),
        "method": method,
    }


def _trace_for_cell(*, scenario: dict[str, Any], option: dict[str, Any], cell: dict[str, Any],
                    internal_trace: dict[str, Any], artifacts: dict[str, Any], simulation_id: str,
                    gate: GateResult, release: TraceContractReleaseResult) -> dict[str, Any]:
    """Bind one real aggregate and one explicitly non-aggregate trial path."""
    assert gate.contract and gate.policy and gate.contract_source and gate.review_reference and gate.review_record_sha256
    assert gate.policy_reference and gate.policy_configuration_id and gate.policy_sha256 and gate.contract_payload_sha256
    assert release.approval_reference and release.release_record_sha256
    reviewed_contract = gate.contract
    policy = gate.policy
    op = policy["operatingPolicy"]
    observed_demand = _provenance(
        "observed_synthetic_dataset", "observed", "historicalDemand",
        "Frozen synthetic weekly demand used for the empirical bootstrap.",
        source_file="public/demo/historical_demand.csv", source_sha256=artifacts["inputHashesSha256"]["historicalDemand"],
    )
    observed_supply = _provenance(
        "observed_synthetic_dataset", "observed", "supplierDelivery",
        "Frozen synthetic supplier delivery history supplies base prices and Supplier A lead observations.",
        source_file="public/demo/supplier_delivery_history.xlsx", source_sha256=artifacts["inputHashesSha256"]["supplierDelivery"],
    )
    approved = _provenance(
        "approved_operating_assumption", "approved", gate.policy_reference,
        f"Team-recorded policy configuration {gate.policy_configuration_id}; policy source hash is retained separately.",
        source_sha256=gate.policy_sha256,
    )
    derived = _provenance("derived_formula", "derived", "tco-v1", "Calculated from the named inputs and all Monte Carlo trials.")
    parameters = [
        {"key": "scenario.demandShock", "value": scenario["demandShock"], "unit": "percent", "provenance": derived},
        {"key": "scenario.demandUnits24m", "value": scenario["demandUnits24m"], "unit": "units/24m", "provenance": derived},
        {"key": "scenario.leadTimeMultiplier", "value": scenario["leadTimeMultiplier"], "unit": "multiplier", "provenance": derived},
        {"key": "option.shareA", "value": option["shareA"], "unit": "fraction", "provenance": derived},
        {"key": "option.terminateA", "value": option["terminateA"], "unit": "boolean", "provenance": derived},
        {"key": "matrix.unitsFromA", "value": cell["unitsFromA"], "unit": "units/24m", "provenance": derived},
        {"key": "matrix.unitsFromB", "value": cell["unitsFromB"], "unit": "units/24m", "provenance": derived},
        {"key": "contract.renewalLocked", "value": reviewed_contract["renewalLocked"], "unit": "boolean", "provenance": _reviewed_field_provenance(gate, "renewalLocked")},
        {"key": "contract.renewalPriceIncreasePct", "value": reviewed_contract["renewalPriceIncreasePct"], "unit": "fraction", "provenance": _reviewed_field_provenance(gate, "renewalPriceIncreasePct")},
        {"key": "contract.minPurchaseUnitsA", "value": reviewed_contract["minPurchaseUnitsA"], "unit": "units/24m", "provenance": _reviewed_field_provenance(gate, "minPurchaseUnitsA")},
        {"key": "contract.terminationFeeUsd", "value": reviewed_contract["terminationFeeUsd"], "unit": "USD", "provenance": _reviewed_field_provenance(gate, "terminationFeeUsd")},
        {"key": "unitPricesUsd.A", "value": artifacts["unitPricesUsd"]["A"], "unit": "USD/unit", "provenance": observed_supply},
        {"key": "unitPricesUsd.B", "value": artifacts["unitPricesUsd"]["B"], "unit": "USD/unit", "provenance": observed_supply},
        {"key": "operatingPolicy.openingInventoryUnits", "value": op["openingInventoryUnits"], "unit": "units", "provenance": approved},
        {"key": "operatingPolicy.safetyStockUnits", "value": op["safetyStockUnits"], "unit": "units", "provenance": approved},
        {"key": "operatingPolicy.targetStockUnits", "value": op["targetStockUnits"], "unit": "units", "provenance": approved},
        {"key": "operatingPolicy.holdingCostUsdPerUnitWeek", "value": op["holdingCostUsdPerUnitWeek"], "unit": "USD/unit/week", "provenance": approved},
        {"key": "operatingPolicy.lostContributionMarginUsdPerUnit", "value": op["lostContributionMarginUsdPerUnit"], "unit": "USD/unit", "provenance": approved},
        {"key": "reorderPointUnits", "value": internal_trace["reorderPointUnits"], "unit": "units", "provenance": derived},
        {"key": "distribution.demand", "value": artifacts["distributionProvenance"]["demand"], "unit": "method", "provenance": observed_demand},
        {"key": "distribution.supplierB", "value": artifacts["distributionProvenance"]["supplierB"], "unit": "method", "provenance": approved},
        {"key": "configuration.policyConfigurationId", "value": gate.policy_configuration_id, "unit": "identifier", "provenance": approved},
    ]
    raw = internal_trace["rawMeanCostsUsd"]
    breakdown = cell["breakdown"]
    components = [
        {"key": "purchase", "formula": "round(displayed unitsFromA × basePriceA + displayed unitsFromB × basePriceB)", "inputKeys": ["matrix.unitsFromA", "matrix.unitsFromB", "unitPricesUsd.A", "unitPricesUsd.B"], "valueUsd": breakdown["purchase"], "roundingAudit": _rounding_audit(raw["purchase"], breakdown["purchase"], "Displayed purchase recomputes from integer half-even mean purchase units for v1 accounting reconciliation.")},
        {"key": "holding", "formula": "round_half_even(mean over trials of available/ending inventory holding cost)", "inputKeys": ["operatingPolicy.holdingCostUsdPerUnitWeek", "reorderPointUnits"], "valueUsd": breakdown["holding"], "roundingAudit": _rounding_audit(raw["holding"], breakdown["holding"], "Raw Monte Carlo mean rounded half-even to whole USD.")},
        {"key": "stockoutLoss", "formula": "round_half_even(mean over trials of lost units × lost contribution margin)", "inputKeys": ["operatingPolicy.lostContributionMarginUsdPerUnit"], "valueUsd": breakdown["stockoutLoss"], "roundingAudit": _rounding_audit(raw["stockoutLoss"], breakdown["stockoutLoss"], "Raw Monte Carlo mean rounded half-even to whole USD.")},
        {"key": "renewalPremium", "formula": "round(displayed unitsFromA × basePriceA × reviewed renewal uplift)", "inputKeys": ["matrix.unitsFromA", "unitPricesUsd.A", "contract.renewalPriceIncreasePct"], "valueUsd": breakdown["renewalPremium"], "roundingAudit": _rounding_audit(raw["renewalPremium"], breakdown["renewalPremium"], "Displayed premium recomputes from integer half-even mean A units for v1 accounting reconciliation.")},
        {"key": "terminationFee", "formula": "reviewed one-time exit fee if terminateA and renewalLocked, otherwise 0", "inputKeys": ["option.terminateA", "contract.renewalLocked", "contract.terminationFeeUsd"], "valueUsd": breakdown["terminationFee"], "roundingAudit": _rounding_audit(raw["terminationFee"], breakdown["terminationFee"], "Fixed contractual fee; raw mean and displayed whole USD are retained separately.")},
    ]
    return {
        "traceSchemaVersion": TRACE_SCHEMA_VERSION, "simulationId": simulation_id, "dataVersion": artifacts["dataVersion"],
        "formulaVersion": artifacts["formulaVersion"], "scenarioId": scenario["id"], "optionId": option["id"],
        "runIdentity": {"executionMode": REVIEWED_EXECUTION_MODE,
                        "reviewRecordId": gate.review_reference, "reviewRecordSha256": gate.review_record_sha256,
                        "contractPayloadSha256": gate.contract_payload_sha256, "policyApprovalReference": gate.policy_reference,
                        "policyConfigurationId": gate.policy_configuration_id, "policySha256": gate.policy_sha256,
                        "contractApprovalReference": release.approval_reference, "contractReleaseRecordSha256": release.release_record_sha256},
        "parameters": parameters, "components": components, "expectedTcoUsd": cell["expectedTco"],
        "stockoutProbability": {"value": cell["stockoutProbability"], "numeratorStockoutRuns": internal_trace["stockoutRuns"], "denominatorRuns": artifacts["monteCarloRuns"], "definition": "trials_with_at_least_one_lost_unit / monteCarloRuns"},
        "serviceLevel": {"value": cell["serviceLevel"], "fulfilledUnitsAllRuns": internal_trace["fulfilledUnitsAllRuns"], "demandUnitsAllRuns": internal_trace["demandUnitsAllRuns"], "definition": "fulfilled_units_all_runs / demand_units_all_runs"},
        "cashOutflowP90": {"valueUsd": cell["cashOutflowP90"], "method": "nearest_rank_ceil_0.90N", "percentile": 0.9, "rankOneBased": internal_trace["p90CashRankOneBased"], "denominatorRuns": artifacts["monteCarloRuns"], "includedCashComponents": ["purchase", "holding", "renewalPremium", "terminationFee"], "excludedNonCashComponents": ["stockoutLoss"], "perRunRounding": "whole_usd_half_even"},
        "summaryRoundingRule": internal_trace["summaryRoundingRule"] + " Raw means, displayed whole-USD values and displayed-minus-raw differences are exposed per component; they are not asserted equal.",
        "samplePath": {"sampleRunIndex": internal_trace["sampleRunIndex"], "classification": "single_realised_trial_not_aggregate", "note": "One realised stochastic trial only; it is not an average, expectation or aggregate path. Matrix statistics use all Monte Carlo runs.", "weeks": internal_trace["weeks"]},
    }


def build_reviewed_success_v2(request: dict[str, Any], gate: GateResult, release: TraceContractReleaseResult, *, request_id: str,
                              project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Run the engine on verified fields and bind every output to review/policy/release identities."""
    required_gate_values = (gate.contract, gate.data_version, gate.review_reference, gate.review_record_sha256, gate.contract_payload_sha256,
                            gate.contract_source, gate.policy, gate.policy_reference, gate.policy_configuration_id, gate.policy_sha256,
                            gate.policy_approval_record_sha256)
    if not gate.ready or not all(required_gate_values) or not release.ready or not release.approval_reference or not release.release_record_sha256:
        raise ValueError("reviewed v2 success requires all verified review, policy and contract-release inputs")
    artifacts = run_reviewed_monte_carlo(request, gate.policy, reviewed_contract=gate.contract, reviewed_data_version=gate.data_version, project_root=project_root)
    canonical = json.dumps({
        "request": request, "dataVersion": gate.data_version, "reviewRecord": gate.review_reference,
        "reviewRecordSha256": gate.review_record_sha256, "contractPayloadSha256": gate.contract_payload_sha256,
        "policyApproval": gate.policy_reference, "policyConfigurationId": gate.policy_configuration_id, "policySha256": gate.policy_sha256,
        "contractApproval": release.approval_reference, "contractReleaseRecordSha256": release.release_record_sha256,
        "engine": artifacts["engineSourceSha256"], "draws": artifacts["distributionProvenance"]["drawsSha256"],
    }, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    simulation_id = "sim-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    simulation = {"simulationId": simulation_id, "seed": artifacts["seed"], "dataVersion": artifacts["dataVersion"],
                  "formulaVersion": artifacts["formulaVersion"], "weeks": artifacts["weeks"], "monteCarloRuns": artifacts["monteCarloRuns"],
                  "unitPricesUsd": artifacts["unitPricesUsd"], "matrix": artifacts["matrix"]}
    check_accounting(simulation, gate.contract, request["options"])
    selections = select_by_scenario({"matrix": artifacts["matrix"]}, request)
    by_scenario, by_option = ({row["id"]: row for row in request["scenarios"]}, {row["id"]: row for row in request["options"]})
    traces = {scenario_id: {cell["optionId"]: _trace_for_cell(scenario=by_scenario[scenario_id], option=by_option[cell["optionId"]], cell=cell,
              internal_trace=artifacts["formulaTraces"][scenario_id][cell["optionId"]], artifacts=artifacts, simulation_id=simulation_id, gate=gate, release=release)
              for cell in rows} for scenario_id, rows in artifacts["matrix"].items()}
    envelope = {"schemaVersion": "causora.contract.v2", "dataVersion": artifacts["dataVersion"], "requestId": request_id,
                "data": {"simulation": simulation, "deltas": artifacts["deltas"], "selections": selections, "traces": traces,
                         "executionContext": {"mode": REVIEWED_EXECUTION_MODE,
                                              "banner": "REVIEWED + POLICY-APPROVED + CONTRACT-RELEASED CALCULATION.",
                                              "humanReviewStatus": "reviewed", "policyStatus": "approved",
                                              "contractReleaseStatus": "released", "decisionReady": True}}}
    validated = ApiSuccessV2.model_validate(envelope).model_dump(mode="json")
    artifact = {"kind": "CAUSORA_REVIEWED_TRACE_ARTIFACT_V2", "reviewRecord": {"id": gate.review_reference, "sha256": gate.review_record_sha256},
                "contractSource": gate.contract_source, "contractPayloadSha256": gate.contract_payload_sha256,
                "policy": {"approvalReference": gate.policy_reference, "configurationId": gate.policy_configuration_id, "sha256": gate.policy_sha256, "approvalRecordSha256": gate.policy_approval_record_sha256},
                "contractRelease": {"approvalReference": release.approval_reference, "recordSha256": release.release_record_sha256, "artifactHashes": release.artifact_hashes},
                "response": validated, "engineSourceSha256": artifacts["engineSourceSha256"], "inputHashesSha256": artifacts["inputHashesSha256"]}
    write_json_utf8_lf(trace_artifact_dir() / f"{simulation_id}.json", artifact)
    return validated
