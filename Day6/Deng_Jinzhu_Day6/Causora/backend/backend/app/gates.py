"""Fail-closed resolution of Wang review, model-policy and v2 release inputs."""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Mapping

from app.config import (
    approved_policy_path,
    policy_verifier_spec,
    review_bundle_path,
    review_verifier_spec,
    trace_contract_v2_verifier_spec,
)
from app.release_verifiers import VerificationError


@dataclass(frozen=True)
class GateResult:
    ready: bool
    reason: str
    message: str
    missing_reasons: tuple[str, ...] = ()
    contract: dict[str, Any] | None = None
    data_version: str | None = None
    review_reference: str | None = None
    review_record_sha256: str | None = None
    contract_payload_sha256: str | None = None
    contract_source: dict[str, Any] | None = None
    field_provenance: dict[str, dict[str, Any]] = field(default_factory=dict)
    policy: dict[str, Any] | None = None
    policy_reference: str | None = None
    policy_configuration_id: str | None = None
    policy_sha256: str | None = None
    policy_approval_record_sha256: str | None = None


@dataclass(frozen=True)
class TraceContractReleaseResult:
    ready: bool
    reason: str
    message: str
    approval_reference: str | None = None
    release_record_sha256: str | None = None
    artifact_hashes: dict[str, str] = field(default_factory=dict)


def _load_callable(spec: str, *, label: str) -> Callable[..., Mapping[str, Any]]:
    if not spec or ":" not in spec:
        raise VerificationError("verification_configuration_invalid", f"{label} verifier must use module:function syntax.")
    module_name, function_name = spec.split(":", 1)
    module = import_module(module_name)
    candidate = getattr(module, function_name)
    if not callable(candidate):
        raise TypeError(f"{label} verifier is not callable")
    return candidate


def _review_result(project_root: Path) -> tuple[dict[str, Any] | None, str | None, str, str]:
    bundle = review_bundle_path()
    if bundle is None:
        return None, "human_review_pending", "Contract evidence review bundle is not configured.", "human_review_pending"
    if not bundle.is_dir():
        return None, "review_bundle_not_verified", "Configured reviewed bundle directory is unavailable.", "review_bundle_not_verified"
    try:
        checked = _load_callable(review_verifier_spec(), label="review")(project_root=project_root, bundle_path=bundle)
        required = ("contract", "dataVersion", "reviewReference", "reviewRecordSha256", "contractPayloadSha256", "contractSource", "fieldProvenance")
        if not isinstance(checked, Mapping) or any(key not in checked for key in required) or not isinstance(checked["contract"], Mapping):
            raise ValueError("review verifier result is incomplete")
        return dict(checked), None, "", ""
    except VerificationError as exc:
        return None, exc.reason, exc.message, exc.reason
    except (OSError, ValueError, TypeError, ImportError, AttributeError):
        return None, "review_bundle_not_verified", "Contract review bundle cannot be verified by the configured review verifier.", "review_bundle_not_verified"


def _policy_result(project_root: Path) -> tuple[dict[str, Any] | None, str | None, str, str]:
    policy_path = approved_policy_path()
    if policy_path is None:
        return None, "simulation_policy_unapproved", "Approved simulation policy file is not configured.", "simulation_policy_unapproved"
    if not policy_path.is_file():
        return None, "simulation_policy_unapproved", "Configured approved simulation policy file is unavailable.", "simulation_policy_unapproved"
    try:
        checked = _load_callable(policy_verifier_spec(), label="policy")(project_root=project_root, policy_path=policy_path)
        required = ("policy", "policyApprovalReference", "policyConfigurationId", "policySha256", "policyApprovalRecordSha256")
        if not isinstance(checked, Mapping) or any(key not in checked for key in required) or not isinstance(checked["policy"], Mapping):
            raise ValueError("policy verifier result is incomplete")
        return dict(checked), None, "", ""
    except VerificationError as exc:
        return None, exc.reason, exc.message, exc.reason
    except (OSError, ValueError, TypeError, ImportError, AttributeError):
        return None, "simulation_policy_unapproved", "Team policy cannot be verified by the configured policy verifier.", "simulation_policy_unapproved"


def resolve_verified_inputs(project_root: Path) -> GateResult:
    """Resolve both input gates so 503 responses name every missing dependency."""
    review, review_reason, review_message, review_missing = _review_result(project_root)
    policy, policy_reason, policy_message, policy_missing = _policy_result(project_root)
    missing = tuple(reason for reason in (review_missing, policy_missing) if reason)
    if missing:
        primary_reason = review_reason or policy_reason or missing[0]
        return GateResult(False, primary_reason, " ".join(message for message in (review_message, policy_message) if message), missing_reasons=missing)
    assert review is not None and policy is not None
    return GateResult(
        True, "ready", "Verified contract and approved model policy are available.",
        contract=dict(review["contract"]), data_version=str(review["dataVersion"]), review_reference=str(review["reviewReference"]),
        review_record_sha256=str(review["reviewRecordSha256"]), contract_payload_sha256=str(review["contractPayloadSha256"]),
        contract_source=dict(review["contractSource"]), field_provenance={key: dict(value) for key, value in dict(review["fieldProvenance"]).items()},
        policy=dict(policy["policy"]), policy_reference=str(policy["policyApprovalReference"]),
        policy_configuration_id=str(policy["policyConfigurationId"]), policy_sha256=str(policy["policySha256"]),
        policy_approval_record_sha256=str(policy["policyApprovalRecordSha256"]),
    )


def resolve_trace_contract_v2_release(project_root: Path) -> TraceContractReleaseResult:
    """Require a recorded three-owner release that hashes backend and frontend contract artifacts."""
    try:
        checked = _load_callable(trace_contract_v2_verifier_spec(), label="trace contract")(project_root=project_root)
        if not isinstance(checked, Mapping):
            raise TypeError("trace contract verifier must return a mapping")
        if checked.get("schemaVersion") != "causora.contract.v2" or checked.get("traceSchemaVersion") != "causora.formula-trace.v1":
            raise ValueError("trace contract verifier released a different schema")
        reference, release_sha, artifact_hashes = checked.get("contractApprovalReference"), checked.get("releaseRecordSha256"), checked.get("artifactHashes")
        if not isinstance(reference, str) or not reference.strip() or not isinstance(release_sha, str) or not isinstance(artifact_hashes, Mapping):
            raise ValueError("trace contract verifier result is incomplete")
    except VerificationError as exc:
        return TraceContractReleaseResult(False, exc.reason, exc.message)
    except (OSError, ValueError, TypeError, ImportError, AttributeError):
        return TraceContractReleaseResult(False, "trace_contract_unconfirmed", "Matrix + Trace contract v2 release cannot be verified.")
    return TraceContractReleaseResult(True, "ready", "Matrix + Trace v2 release is verified.", approval_reference=reference,
                                      release_record_sha256=release_sha, artifact_hashes={str(key): str(value) for key, value in artifact_hashes.items()})
