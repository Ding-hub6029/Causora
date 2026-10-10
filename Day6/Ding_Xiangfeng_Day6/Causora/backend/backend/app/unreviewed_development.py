"""Explicitly opt-in, unreviewed local-development Matrix + Trace v2 response.

This module is deliberately separate from reviewed_success: it never reads or
creates human-review, policy-approval, or contract-release records. It exists
only for integration testing before those records are supplied.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT, TRACE_SCHEMA_VERSION, trace_artifact_dir
from app.contracts_v2 import ApiSuccessV2, UNREVIEWED_DEVELOPMENT_MODE
from app.portable_io import write_json_utf8_lf
from app.reviewed_success import _provenance, _rounding_audit
from simulation_day1.interfaces import check_accounting, select_by_scenario
from simulation_day3.monte_carlo import run_unapproved_monte_carlo

DEV_BANNER = "UNREVIEWED — DEVELOPMENT ONLY. NOT HUMAN-REVIEWED, NOT POLICY-APPROVED, NOT CONTRACT-RELEASED, NOT DECISION-READY."
DEV_DATA_VERSION_SUFFIX = "UNREVIEWED_DEV_ONLY"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _dev_contract_provenance(field: str, contract_sha256: str) -> dict[str, Any]:
    return _provenance(
        "unreviewed_development_contract", "unreviewed_development_only", f"UNREVIEWED_DEV_ONLY:contract.{field}",
        f"{DEV_BANNER} Frozen synthetic contract field '{field}' is used only to exercise the integration path.",
        source_file="demo_data/causora_day1_mock.json", source_sha256=contract_sha256,
    )


def _dev_policy_provenance(policy_sha256: str) -> dict[str, Any]:
    return _provenance(
        "unreviewed_development_assumption", "unreviewed_development_only", "UNREVIEWED_DEV_ONLY:policy",
        f"{DEV_BANNER} This operating-policy value is from the packaged UNAPPROVED test policy.",
        source_file="simulation_day3/examples/UNAPPROVED_MC_POLICY.json", source_sha256=policy_sha256,
    )


def _trace_for_development_cell(*, scenario: dict[str, Any], option: dict[str, Any], cell: dict[str, Any],
                                internal_trace: dict[str, Any], artifacts: dict[str, Any], simulation_id: str,
                                data_version: str, contract: dict[str, Any], contract_sha256: str,
                                policy_sha256: str, contract_payload_sha256: str, release_placeholder_sha256: str) -> dict[str, Any]:
    policy = artifacts["developmentPolicy"]
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
    dev_policy = _dev_policy_provenance(policy_sha256)
    derived = _provenance("derived_formula", "derived", "tco-v1", "Calculated from named inputs and all Monte Carlo trials in explicit unreviewed development mode.")
    parameters = [
        {"key": "scenario.demandShock", "value": scenario["demandShock"], "unit": "percent", "provenance": derived},
        {"key": "scenario.demandUnits24m", "value": scenario["demandUnits24m"], "unit": "units/24m", "provenance": derived},
        {"key": "scenario.leadTimeMultiplier", "value": scenario["leadTimeMultiplier"], "unit": "multiplier", "provenance": derived},
        {"key": "option.shareA", "value": option["shareA"], "unit": "fraction", "provenance": derived},
        {"key": "option.terminateA", "value": option["terminateA"], "unit": "boolean", "provenance": derived},
        {"key": "matrix.unitsFromA", "value": cell["unitsFromA"], "unit": "units/24m", "provenance": derived},
        {"key": "matrix.unitsFromB", "value": cell["unitsFromB"], "unit": "units/24m", "provenance": derived},
        {"key": "contract.renewalLocked", "value": contract["renewalLocked"], "unit": "boolean", "provenance": _dev_contract_provenance("renewalLocked", contract_sha256)},
        {"key": "contract.renewalPriceIncreasePct", "value": contract["renewalPriceIncreasePct"], "unit": "fraction", "provenance": _dev_contract_provenance("renewalPriceIncreasePct", contract_sha256)},
        {"key": "contract.minPurchaseUnitsA", "value": contract["minPurchaseUnitsA"], "unit": "units/24m", "provenance": _dev_contract_provenance("minPurchaseUnitsA", contract_sha256)},
        {"key": "contract.terminationFeeUsd", "value": contract["terminationFeeUsd"], "unit": "USD", "provenance": _dev_contract_provenance("terminationFeeUsd", contract_sha256)},
        {"key": "unitPricesUsd.A", "value": artifacts["unitPricesUsd"]["A"], "unit": "USD/unit", "provenance": observed_supply},
        {"key": "unitPricesUsd.B", "value": artifacts["unitPricesUsd"]["B"], "unit": "USD/unit", "provenance": observed_supply},
        {"key": "operatingPolicy.openingInventoryUnits", "value": op["openingInventoryUnits"], "unit": "units", "provenance": dev_policy},
        {"key": "operatingPolicy.safetyStockUnits", "value": op["safetyStockUnits"], "unit": "units", "provenance": dev_policy},
        {"key": "operatingPolicy.targetStockUnits", "value": op["targetStockUnits"], "unit": "units", "provenance": dev_policy},
        {"key": "operatingPolicy.holdingCostUsdPerUnitWeek", "value": op["holdingCostUsdPerUnitWeek"], "unit": "USD/unit/week", "provenance": dev_policy},
        {"key": "operatingPolicy.lostContributionMarginUsdPerUnit", "value": op["lostContributionMarginUsdPerUnit"], "unit": "USD/unit", "provenance": dev_policy},
        {"key": "reorderPointUnits", "value": internal_trace["reorderPointUnits"], "unit": "units", "provenance": derived},
        {"key": "distribution.demand", "value": artifacts["distributionProvenance"]["demand"], "unit": "method", "provenance": observed_demand},
        {"key": "distribution.supplierB", "value": artifacts["distributionProvenance"]["supplierB"], "unit": "method", "provenance": dev_policy},
        {"key": "configuration.executionMode", "value": UNREVIEWED_DEVELOPMENT_MODE, "unit": "identifier", "provenance": derived},
    ]
    raw, breakdown = internal_trace["rawMeanCostsUsd"], cell["breakdown"]
    components = [
        {"key": "purchase", "formula": "round(displayed unitsFromA × basePriceA + displayed unitsFromB × basePriceB)", "inputKeys": ["matrix.unitsFromA", "matrix.unitsFromB", "unitPricesUsd.A", "unitPricesUsd.B"], "valueUsd": breakdown["purchase"], "roundingAudit": _rounding_audit(raw["purchase"], breakdown["purchase"], "Displayed purchase recomputes from integer half-even mean purchase units for v1 accounting reconciliation.")},
        {"key": "holding", "formula": "round_half_even(mean over trials of available/ending inventory holding cost)", "inputKeys": ["operatingPolicy.holdingCostUsdPerUnitWeek", "reorderPointUnits"], "valueUsd": breakdown["holding"], "roundingAudit": _rounding_audit(raw["holding"], breakdown["holding"], "Raw Monte Carlo mean rounded half-even to whole USD.")},
        {"key": "stockoutLoss", "formula": "round_half_even(mean over trials of lost units × lost contribution margin)", "inputKeys": ["operatingPolicy.lostContributionMarginUsdPerUnit"], "valueUsd": breakdown["stockoutLoss"], "roundingAudit": _rounding_audit(raw["stockoutLoss"], breakdown["stockoutLoss"], "Raw Monte Carlo mean rounded half-even to whole USD.")},
        {"key": "renewalPremium", "formula": "round(displayed unitsFromA × basePriceA × unreviewed development renewal uplift)", "inputKeys": ["matrix.unitsFromA", "unitPricesUsd.A", "contract.renewalPriceIncreasePct"], "valueUsd": breakdown["renewalPremium"], "roundingAudit": _rounding_audit(raw["renewalPremium"], breakdown["renewalPremium"], "Displayed premium recomputes from integer half-even mean A units for v1 accounting reconciliation.")},
        {"key": "terminationFee", "formula": "synthetic exit fee if terminateA and renewalLocked, otherwise 0", "inputKeys": ["option.terminateA", "contract.renewalLocked", "contract.terminationFeeUsd"], "valueUsd": breakdown["terminationFee"], "roundingAudit": _rounding_audit(raw["terminationFee"], breakdown["terminationFee"], "Fixed synthetic fee; raw mean and displayed whole USD are retained separately.")},
    ]
    return {
        "traceSchemaVersion": TRACE_SCHEMA_VERSION, "simulationId": simulation_id, "dataVersion": data_version,
        "formulaVersion": artifacts["formulaVersion"], "scenarioId": scenario["id"], "optionId": option["id"],
        "runIdentity": {"executionMode": UNREVIEWED_DEVELOPMENT_MODE, "reviewRecordId": None, "reviewRecordSha256": None,
                        "contractPayloadSha256": contract_payload_sha256, "policyApprovalReference": "UNREVIEWED_DEV_ONLY_NO_POLICY_APPROVAL",
                        "policyConfigurationId": "UNREVIEWED_DEV_ONLY_PACKAGED_POLICY", "policySha256": policy_sha256,
                        "contractApprovalReference": "UNREVIEWED_DEV_ONLY_NO_CONTRACT_RELEASE", "contractReleaseRecordSha256": release_placeholder_sha256},
        "parameters": parameters, "components": components, "expectedTcoUsd": cell["expectedTco"],
        "stockoutProbability": {"value": cell["stockoutProbability"], "numeratorStockoutRuns": internal_trace["stockoutRuns"], "denominatorRuns": artifacts["monteCarloRuns"], "definition": "trials_with_at_least_one_lost_unit / monteCarloRuns"},
        "serviceLevel": {"value": cell["serviceLevel"], "fulfilledUnitsAllRuns": internal_trace["fulfilledUnitsAllRuns"], "demandUnitsAllRuns": internal_trace["demandUnitsAllRuns"], "definition": "fulfilled_units_all_runs / demand_units_all_runs"},
        "cashOutflowP90": {"valueUsd": cell["cashOutflowP90"], "method": "nearest_rank_ceil_0.90N", "percentile": 0.9, "rankOneBased": internal_trace["p90CashRankOneBased"], "denominatorRuns": artifacts["monteCarloRuns"], "includedCashComponents": ["purchase", "holding", "renewalPremium", "terminationFee"], "excludedNonCashComponents": ["stockoutLoss"], "perRunRounding": "whole_usd_half_even"},
        "summaryRoundingRule": internal_trace["summaryRoundingRule"] + " " + DEV_BANNER + " Raw means, displayed whole-USD values and displayed-minus-raw differences are exposed per component.",
        "samplePath": {"sampleRunIndex": internal_trace["sampleRunIndex"], "classification": "single_realised_trial_not_aggregate", "note": "One realised stochastic trial only; it is not an average, expectation or aggregate path. Matrix statistics use all Monte Carlo runs.", "weeks": internal_trace["weeks"]},
    }


def build_unreviewed_development_success_v2(request: dict[str, Any], *, request_id: str,
                                             project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Run packaged synthetic inputs for UI/API testing with irreversible labels."""
    policy_path = project_root / "simulation_day3/examples/UNAPPROVED_MC_POLICY.json"
    contract_path = project_root / "demo_data/causora_day1_mock.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    contract_payload = json.loads(contract_path.read_text(encoding="utf-8"))
    contract = contract_payload["contract"]
    artifacts = run_unapproved_monte_carlo(request, policy, project_root=project_root)
    artifacts["developmentPolicy"] = policy
    contract_sha256, policy_sha256 = _sha256(contract_path), _sha256(policy_path)
    contract_payload_sha256 = _canonical_sha(contract)
    release_placeholder_sha256 = hashlib.sha256(b"UNREVIEWED_DEV_ONLY_NO_CONTRACT_RELEASE_RECORD").hexdigest()
    data_version = f"{artifacts['sourceDataVersion']}--{DEV_DATA_VERSION_SUFFIX}"
    canonical = json.dumps({"request": request, "mode": UNREVIEWED_DEVELOPMENT_MODE, "dataVersion": data_version,
                            "contractSha256": contract_sha256, "policySha256": policy_sha256,
                            "engine": artifacts["engineSourceSha256"], "draws": artifacts["distributionProvenance"]["drawsSha256"]},
                           ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    simulation_id = "sim-dev-unreviewed-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    simulation = {"simulationId": simulation_id, "seed": artifacts["seed"], "dataVersion": data_version,
                  "formulaVersion": artifacts["formulaVersion"], "weeks": artifacts["weeks"], "monteCarloRuns": artifacts["monteCarloRuns"],
                  "unitPricesUsd": artifacts["unitPricesUsd"], "matrix": artifacts["computedMatrix"]}
    check_accounting(simulation, contract, request["options"])
    selections = select_by_scenario({"matrix": artifacts["computedMatrix"]}, request)
    by_scenario = {row["id"]: row for row in request["scenarios"]}
    by_option = {row["id"]: row for row in request["options"]}
    traces = {scenario_id: {
        cell["optionId"]: _trace_for_development_cell(
            scenario=by_scenario[scenario_id], option=by_option[cell["optionId"]], cell=cell,
            internal_trace=artifacts["formulaTraces"][scenario_id][cell["optionId"]], artifacts=artifacts,
            simulation_id=simulation_id, data_version=data_version, contract=contract, contract_sha256=contract_sha256,
            policy_sha256=policy_sha256, contract_payload_sha256=contract_payload_sha256,
            release_placeholder_sha256=release_placeholder_sha256,
        ) for cell in rows
    } for scenario_id, rows in artifacts["computedMatrix"].items()}
    envelope = {"schemaVersion": "causora.contract.v2", "dataVersion": data_version, "requestId": request_id,
                "data": {"simulation": simulation, "deltas": artifacts["decisionDeltas"], "selections": selections, "traces": traces,
                         "executionContext": {"mode": UNREVIEWED_DEVELOPMENT_MODE, "banner": DEV_BANNER,
                                              "humanReviewStatus": "not_reviewed_development_only", "policyStatus": "unapproved_development_only",
                                              "contractReleaseStatus": "not_released_development_only", "decisionReady": False}}}
    validated = ApiSuccessV2.model_validate(envelope).model_dump(mode="json")
    artifact = {"kind": "CAUSORA_UNREVIEWED_DEVELOPMENT_TRACE_ARTIFACT_V2", "executionContext": validated["data"]["executionContext"],
                "contractSource": {"file": str(contract_path.relative_to(project_root)), "sha256": contract_sha256},
                "policySource": {"file": str(policy_path.relative_to(project_root)), "sha256": policy_sha256},
                "response": validated, "engineSourceSha256": artifacts["engineSourceSha256"], "inputHashesSha256": artifacts["inputHashesSha256"]}
    write_json_utf8_lf(trace_artifact_dir() / f"{simulation_id}.json", artifact)
    return validated
