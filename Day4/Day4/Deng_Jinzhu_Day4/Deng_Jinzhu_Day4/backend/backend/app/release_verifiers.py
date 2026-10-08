"""Small, file-backed verifiers for three independently owned release inputs.

These verifiers validate integrity, schema and recorded confirmations. They do
not authenticate humans or create approvals: Wang/the three owners must supply
the separate reviewed bundle and confirmation records. A policy's own
`TEAM_APPROVED` string is deliberately insufficient.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from app import config
from simulation_day1.interfaces import validate_reviewed_contract
from simulation_day3.policy import Day3Policy

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
REQUIRED_CONFIRMATION_ROLES = {"simulation_owner", "frontend_owner", "review_owner"}
REQUIRED_POLICY_TOPICS = {
    "renewal_date_opening_inventory_bridge",
    "demand_bootstrap",
    "selling_price",
    "lost_contribution_margin",
    "holding_cost",
    "safety_stock",
    "target_stock",
    "replenishment_and_minimum_purchase_schedule",
    "purchase_and_cash_recognition_timing",
    "supplier_b_lead_distribution",
    "lead_stress_scope",
    "stockout_probability_definition",
    "service_level_definition",
    "cash_p90_method_and_lines",
    "money_and_mean_purchase_rounding",
}
FIELD_PLAN = {'decisionDate': ('ASSUMPTION:decisionDate', 'demo_data/causora_day1_mock.json', ['decisionDate']), 'renewalDate': ('ASSUMPTION:renewalDate', 'demo_data/causora_day1_mock.json', ['renewalDate']), 'daysToRenewal': ('ASSUMPTION:decisionDate', 'demo_data/causora_day1_mock.json', ['decisionDate', 'renewalDate']), 'renewalNoticeDays': ('EV-014', 'public/demo/supplier_a_agreement.pdf', ['EV-014']), 'noticeDeadline': ('EV-014', 'public/demo/supplier_a_agreement.pdf', ['EV-014', 'renewalDate']), 'noticeSent': ('ASSUMPTION:noticeSent', 'public/demo/supplier_correspondence_log.csv', ['noticeSent']), 'noticeRecordSource': ('ASSUMPTION:noticeSent', 'public/demo/supplier_correspondence_log.csv', ['noticeSent']), 'renewalLocked': ('EV-020', 'public/demo/supplier_a_agreement.pdf', ['EV-020', 'EV-014', 'decisionDate', 'renewalDate', 'noticeSent']), 'renewalTermMonths': ('EV-019', 'public/demo/supplier_a_agreement.pdf', ['EV-019']), 'renewalPriceIncreasePct': ('EV-021', 'public/demo/supplier_a_agreement.pdf', ['EV-021']), 'minPurchaseShareA': ('EV-024', 'public/demo/supplier_a_agreement.pdf', ['EV-024']), 'forecastBasis': ('ASSUMPTION:forecastBasis', 'demo_data/causora_day1_mock.json', ['forecastBasis']), 'lockedForecastUnits24m': ('ASSUMPTION:lockedForecastUnits24m', 'demo_data/causora_day1_mock.json', ['lockedForecastUnits24m']), 'minPurchaseUnitsA': ('EV-024', 'public/demo/supplier_a_agreement.pdf', ['EV-024', 'forecastBasis', 'lockedForecastUnits24m']), 'terminationFeeUsd': ('EV-027', 'public/demo/supplier_a_agreement.pdf', ['EV-027']), 'evidenceIds': ('EV-020', 'public/demo/supplier_a_agreement.pdf', ['EV-014', 'EV-019', 'EV-021', 'EV-024', 'EV-027', 'EV-020'])}
REQUIRED_REVIEW_ITEMS = ['EV-014', 'EV-019', 'EV-020', 'EV-021', 'EV-024', 'EV-027', 'decisionDate', 'forecastBasis', 'lockedForecastUnits24m', 'noticeSent', 'renewalDate']
REQUIRED_CONTRACT_FIELDS = {
    "decisionDate", "renewalDate", "daysToRenewal", "renewalNoticeDays", "noticeDeadline", "noticeSent",
    "noticeRecordSource", "renewalLocked", "renewalTermMonths", "renewalPriceIncreasePct", "minPurchaseShareA",
    "forecastBasis", "lockedForecastUnits24m", "minPurchaseUnitsA", "terminationFeeUsd", "evidenceIds",
}


class VerificationError(ValueError):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _json(path: Path, reason: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(reason, f"Cannot read required verification file: {path.name}.") from exc
    if not isinstance(raw, dict):
        raise VerificationError(reason, f"Verification file must contain one JSON object: {path.name}.")
    return raw


def _text(value: Any, label: str, reason: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VerificationError(reason, f"{label} must be a non-empty string.")
    return value


def _sha(value: Any, label: str, reason: str) -> str:
    value = _text(value, label, reason)
    if not SHA256_RE.fullmatch(value):
        raise VerificationError(reason, f"{label} must be a lowercase SHA-256.")
    return value


def _approvals(record: Mapping[str, Any], *, reason: str, required_topics: bool = False) -> None:
    approvals = record.get("approvals")
    if not isinstance(approvals, list):
        raise VerificationError(reason, "Approval record must include an approvals list.")
    roles: set[str] = set()
    for item in approvals:
        if not isinstance(item, dict):
            raise VerificationError(reason, "Every approval must be an object.")
        role = _text(item.get("role"), "approval.role", reason)
        _text(item.get("actorId"), "approval.actorId", reason)
        _text(item.get("recordedAtUtc"), "approval.recordedAtUtc", reason)
        if item.get("decision") != "approved":
            raise VerificationError(reason, "Every required approval decision must be approved.")
        roles.add(role)
    if roles != REQUIRED_CONFIRMATION_ROLES or len(approvals) != 3:
        raise VerificationError(reason, "Approval record must contain exactly simulation_owner, frontend_owner and review_owner confirmations.")
    if required_topics:
        topics = record.get("confirmedTopics")
        if not isinstance(topics, list) or set(topics) != REQUIRED_POLICY_TOPICS or len(topics) != len(REQUIRED_POLICY_TOPICS):
            raise VerificationError(reason, "Policy record must confirm every required modelling topic exactly once.")


def verify_reviewed_bundle_record(*, project_root: Path, bundle_path: Path) -> Mapping[str, Any]:
    """Read Wang's reviewed bundle without treating a policy or a boolean as review evidence."""
    if not bundle_path.is_dir():
        raise VerificationError("review_bundle_not_verified", "Configured reviewed bundle directory is unavailable.")
    bundle_file = bundle_path / "reviewed_contract.json"
    record_file = bundle_path / "review_record.json"
    if not bundle_file.is_file() or not record_file.is_file():
        raise VerificationError("review_bundle_not_verified", "Wang's reviewed bundle requires reviewed_contract.json and review_record.json.")
    bundle = _json(bundle_file, "review_bundle_not_verified")
    record = _json(record_file, "review_bundle_not_verified")
    if bundle.get("kind") != "causora.wang.reviewed-contract-bundle.v1" or bundle.get("datasetId") != config.DEFAULT_DATASET_ID:
        raise VerificationError("review_bundle_not_verified", "Reviewed bundle kind or datasetId is invalid.")
    data_version = _text(bundle.get("dataVersion"), "bundle.dataVersion", "review_bundle_not_verified")
    contract = bundle.get("contract")
    if not isinstance(contract, dict) or set(contract) != REQUIRED_CONTRACT_FIELDS:
        raise VerificationError("review_bundle_not_verified", "Reviewed contract fields are incomplete or unexpected.")
    try:
        validate_reviewed_contract(contract)
    except ValueError as exc:
        raise VerificationError("review_bundle_not_verified", "Reviewed contract fields fail Causora consistency checks.") from exc

    field_provenance = bundle.get("fieldProvenance")
    if not isinstance(field_provenance, dict) or set(field_provenance) != REQUIRED_CONTRACT_FIELDS:
        raise VerificationError("review_bundle_not_verified", "Every reviewed contract field needs its own fieldProvenance entry.")
    for field, provenance in field_provenance.items():
        if not isinstance(provenance, dict):
            raise VerificationError("review_bundle_not_verified", f"fieldProvenance.{field} must be an object.")
        _text(provenance.get("evidenceId"), f"fieldProvenance.{field}.evidenceId", "review_bundle_not_verified")
        _text(provenance.get("sourceFile"), f"fieldProvenance.{field}.sourceFile", "review_bundle_not_verified")
        _sha(provenance.get("sourceSha256"), f"fieldProvenance.{field}.sourceSha256", "review_bundle_not_verified")
        _text(provenance.get("reviewItemId"), f"fieldProvenance.{field}.reviewItemId", "review_bundle_not_verified")

    def verify_source(entry: Mapping[str, Any]) -> None:
        relative = entry.get("sourceFile")
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise VerificationError("review_bundle_not_verified", "Review source must be relative to the project root.")
        path = (project_root / relative).resolve()
        if not path.is_relative_to(project_root.resolve()) or not path.is_file() or _file_sha256(path) != entry.get("sourceSha256"):
            raise VerificationError("review_bundle_not_verified", "Review source is missing, outside the project or has changed bytes.")

    contract_source = bundle.get("contractSource")
    if not isinstance(contract_source, dict):
        raise VerificationError("review_bundle_not_verified", "Reviewed bundle requires a distinct contractSource summary.")
    _text(contract_source.get("sourceFile"), "contractSource.sourceFile", "review_bundle_not_verified")
    _sha(contract_source.get("sourceSha256"), "contractSource.sourceSha256", "review_bundle_not_verified")

    if contract_source.get("sourceFile") != "public/demo/supplier_a_agreement.pdf":
        raise VerificationError("review_bundle_not_verified", "Contract source must identify the shared agreement PDF.")
    verify_source(contract_source)

    if record.get("kind") != "causora.wang.review-record.v1" or record.get("status") != "reviewed" or record.get("reviewerRole") != "contract_reviewer":
        raise VerificationError("review_bundle_not_verified", "Review record must identify a completed Wang contract review.")
    review_id = _text(record.get("reviewId"), "reviewRecord.reviewId", "review_bundle_not_verified")
    _text(record.get("reviewerId"), "reviewRecord.reviewerId", "review_bundle_not_verified")
    _text(record.get("recordedAtUtc"), "reviewRecord.recordedAtUtc", "review_bundle_not_verified")
    if record.get("contractPayloadSha256") != _canonical_sha256(contract):
        raise VerificationError("review_bundle_not_verified", "Review record does not bind this contract payload.")
    if record.get("fieldProvenanceSha256") != _canonical_sha256(field_provenance):
        raise VerificationError("review_bundle_not_verified", "Review record does not bind field-level provenance.")
    reviewed_items = record.get("reviewedItems")
    if not isinstance(reviewed_items, list) or len(reviewed_items) != 11:
        raise VerificationError("review_bundle_not_verified", "Review record must retain all 11 completed review items.")
    item_ids = []
    for item in reviewed_items:
        if not isinstance(item, dict) or item.get("status") != "reviewed":
            raise VerificationError("review_bundle_not_verified", "Every review item must be recorded as reviewed.")
        item_ids.append(_text(item.get("id"), "reviewItem.id", "review_bundle_not_verified"))
    if len(set(item_ids)) != len(item_ids):
        raise VerificationError("review_bundle_not_verified", "Review item identifiers must be unique.")

    if set(item_ids) != set(REQUIRED_REVIEW_ITEMS):
        raise VerificationError("review_bundle_not_verified", "Review must contain the six exact evidence IDs and five exact assumptions.")
    for field, (evidence, file, dependencies) in FIELD_PLAN.items():
        provenance = field_provenance[field]
        if (provenance.get("evidenceId") != evidence or provenance.get("sourceFile") != file or
                provenance.get("reviewItemId") != dependencies[0] or provenance.get("status") != "reviewed" or
                provenance.get("derivedFromReviewItemIds") != dependencies):
            raise VerificationError("review_bundle_not_verified", f"Invalid reviewed source/dependency mapping for {field}.")
        verify_source(provenance)
    confirmed = {item["id"]: item.get("confirmedValue") for item in reviewed_items}
    expected = {"EV-014": contract["renewalNoticeDays"], "EV-019": contract["renewalTermMonths"],
                "EV-021": contract["renewalPriceIncreasePct"], "EV-024": contract["minPurchaseShareA"],
                "EV-027": contract["terminationFeeUsd"], "EV-020": True,
                **{key: contract[key] for key in REQUIRED_REVIEW_ITEMS if not key.startswith("EV-")}}
    if _canonical_sha256(confirmed) != _canonical_sha256(expected):
        raise VerificationError("review_bundle_not_verified", "Confirmed review values do not match this contract; EV-020 confirms the conditional clause exists.")
    if "humanConfirmationSource" in record:
        confirmation = record["humanConfirmationSource"]
        if not isinstance(confirmation, dict):
            raise VerificationError("review_bundle_not_verified", "Human confirmation source must be an object.")
        verify_source(confirmation)

    return {
        "contract": contract,
        "dataVersion": data_version,
        "reviewReference": review_id,
        "reviewRecordSha256": _file_sha256(record_file),
        "contractPayloadSha256": _canonical_sha256(contract),
        "contractSource": dict(contract_source),
        "fieldProvenance": field_provenance,
    }


def verify_team_policy_record(*, project_root: Path, policy_path: Path) -> Mapping[str, Any]:
    """Require a separately recorded three-owner policy confirmation for a policy file."""
    record_path = config.policy_approval_record_path()
    if record_path is None:
        raise VerificationError("simulation_policy_unapproved", "CAUSORA_POLICY_APPROVAL_RECORD_PATH is not configured.")
    if not policy_path.is_file() or not record_path.is_file():
        raise VerificationError("simulation_policy_unapproved", "Approved policy file or its approval record is unavailable.")
    try:
        policy = Day3Policy.model_validate_json(policy_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise VerificationError("simulation_policy_unapproved", "Approved policy file is invalid.") from exc
    if policy.policyStatus != "TEAM_APPROVED":
        raise VerificationError("simulation_policy_unapproved", "Policy file is not in TEAM_APPROVED state.")
    record = _json(record_path, "simulation_policy_unapproved")
    if record.get("kind") != "causora.day3.policy-approval-record.v1" or record.get("status") != "approved":
        raise VerificationError("simulation_policy_unapproved", "Policy approval record kind or status is invalid.")
    if record.get("policySha256") != _file_sha256(policy_path):
        raise VerificationError("simulation_policy_unapproved", "Policy approval record does not bind the configured policy file.")
    _approvals(record, reason="simulation_policy_unapproved", required_topics=True)
    approval_id = _text(record.get("approvalRecordId"), "policyApprovalRecord.approvalRecordId", "simulation_policy_unapproved")
    config_id = _text(record.get("policyConfigurationId"), "policyApprovalRecord.policyConfigurationId", "simulation_policy_unapproved")
    return {
        "policy": policy.model_dump(mode="json"),
        "policyApprovalReference": approval_id,
        "policyConfigurationId": config_id,
        "policySha256": _file_sha256(policy_path),
        "policyApprovalRecordSha256": _file_sha256(record_path),
    }


def verify_trace_contract_release(*, project_root: Path) -> Mapping[str, Any]:
    """Release v2 only when backend/schema/common contract/frontend files are all hash-bound."""
    record_path = config.trace_contract_v2_release_record_path()
    common_path = config.common_api_contract_path()
    ts_path = config.typescript_v2_types_path()
    validator_path = config.frontend_v2_validator_path()
    if record_path is None or common_path is None or ts_path is None or validator_path is None:
        raise VerificationError("trace_contract_unconfirmed", "Trace release needs release record plus common API, TypeScript DTO and frontend validator paths.")
    required_paths = {
        "backendJsonSchema": project_root / "contracts" / "causora.contract.v2.schema.json",
        "pythonPydanticModel": project_root / "app" / "contracts_v2.py",
        "commonApiContract": common_path,
        "typescriptTypes": ts_path,
        "frontendValidator": validator_path,
    }
    if not record_path.is_file() or any(not path.is_file() for path in required_paths.values()):
        raise VerificationError("trace_contract_unconfirmed", "Trace release record or one of its declared contract artifacts is unavailable.")
    record = _json(record_path, "trace_contract_unconfirmed")
    if (record.get("kind") != "causora.trace-contract-release-record.v1" or record.get("status") != "released" or
            record.get("schemaVersion") != config.SCHEMA_VERSION_V2 or record.get("traceSchemaVersion") != config.TRACE_SCHEMA_VERSION):
        raise VerificationError("trace_contract_unconfirmed", "Trace release record does not release the expected v2 schema.")
    _approvals(record, reason="trace_contract_unconfirmed", required_topics=False)
    artifacts = record.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(required_paths):
        raise VerificationError("trace_contract_unconfirmed", "Trace release record must bind every backend and frontend contract artifact.")
    actual_hashes: dict[str, str] = {}
    for name, path in required_paths.items():
        actual_hashes[name] = _file_sha256(path)
        if artifacts.get(name) != actual_hashes[name]:
            raise VerificationError("trace_contract_unconfirmed", f"Trace release hash mismatch for {name}.")
    reference = _text(record.get("contractApprovalReference"), "traceRelease.contractApprovalReference", "trace_contract_unconfirmed")
    return {
        "schemaVersion": config.SCHEMA_VERSION_V2,
        "traceSchemaVersion": config.TRACE_SCHEMA_VERSION,
        "contractApprovalReference": reference,
        "releaseRecordSha256": _file_sha256(record_path),
        "artifactHashes": actual_hashes,
    }
