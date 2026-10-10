"""A contract-shaped, fail-closed POST /api/simulate integration boundary.

This is NOT an HTTP server. The Day 2 engine computes an internal deterministic
preview, but the shared v1 success DTO requires measured stockoutProbability and
cashOutflowP90 from positive Monte Carlo runs. Do not forge them from one path.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from simulation_day1.interfaces import ContractInputError, SCHEMA_VERSION, validate_request
from simulation_day1.wire_models import ApiFailure
from simulation_day2.deterministic import ROOT, InputNotApproved, read_source_manifest, require_reviewed_bundle
from simulation_day2.models import Day2Policy


def _failure(*, request_id: str, http_status: int, code: str, message: str,
             reason: str) -> tuple[int, dict[str, Any]]:
    envelope = {"schemaVersion": SCHEMA_VERSION, "requestId": request_id,
                "error": {"code": code, "message": message,
                          "details": {"reason": reason}, "requestId": request_id}}
    # Reuse the actual Day 1 mirrored TypeScript DTO (strict unknown-field check).
    validated = ApiFailure.model_validate_json(json.dumps(envelope, ensure_ascii=False))
    return http_status, validated.model_dump(mode="json")


def simulate_v1_boundary(request: Any, *, request_id: str, project_root: Path = ROOT,
                         reviewed_bundle: Path | None = None,
                         policy_data: dict | None = None) -> tuple[int, dict[str, Any]]:
    """Return only honest v1 errors until review, policy, AND MC statistics exist.

    No static Day 1 metrics and no internal deterministic preview are serialized
    into a public v1 success. Future real MC results must pass the separate
    numeric validator before adding a 200 branch.
    """
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("the HTTP adapter must supply a nonempty requestId")
    try:
        # Validate actual frozen source bytes before trusting even demo assumptions.
        read_source_manifest(project_root)
        from simulation_day1.interfaces import FROZEN_MOCK_SHA256
        from hashlib import sha256
        raw = (project_root / "demo_data/causora_day1_mock.json").read_bytes()
        if sha256(raw).hexdigest() != FROZEN_MOCK_SHA256:
            raise ValueError("frozen dataset changed without a new reviewed dataVersion")
        contract = json.loads(raw.decode("utf-8"))["contract"]
    except (OSError, ValueError, KeyError, TypeError):
        return _failure(request_id=request_id, http_status=503, code="simulation_failed",
                        message="The frozen synthetic dataset is missing or has changed.",
                        reason="dataset_unavailable")
    try:
        if not isinstance(request, dict):
            raise ValueError("JSON object required")
        validate_request(request, dataset_id="ds-001", contract=contract,
                         allow_unfrozen_scenarios=True)
        if policy_data is not None:
            Day2Policy.model_validate_json(json.dumps(policy_data, ensure_ascii=False))
    except (ContractInputError, ValidationError, ValueError, TypeError, KeyError):
        # No private source data or raw exception text travels over HTTP.
        return _failure(request_id=request_id, http_status=422, code="validation_error",
                        message="Invalid simulation request or input policy.", reason="invalid_input")

    if reviewed_bundle is None:
        return _failure(request_id=request_id, http_status=503, code="simulation_failed",
                        message="Contract evidence and demo assumptions await human review.",
                        reason="human_review_pending")
    try:
        reviewed = require_reviewed_bundle(project_root, reviewed_bundle)
        validate_request(request, dataset_id="ds-001", contract=reviewed.model_dump(mode="json"),
                         allow_unfrozen_scenarios=True)
    except (InputNotApproved, ContractInputError, ValidationError, ValueError, OSError):
        return _failure(request_id=request_id, http_status=503, code="simulation_failed",
                        message="Reviewed synthetic contract bundle is absent, stale or invalid.",
                        reason="review_bundle_not_verified")
    if policy_data is None:
        return _failure(request_id=request_id, http_status=503, code="simulation_failed",
                        message="A team-approved physical and financial simulation policy is required.",
                        reason="missing_policy")
    # An unapproved test policy, even paired with a reviewed synthetic bundle,
    # cannot produce a v1 probability/P90 or an approval-ready selection.
    return _failure(request_id=request_id, http_status=503, code="simulation_failed",
                    message="The deterministic run has no Monte Carlo probability or cash P90.",
                    reason="monte_carlo_statistics_unavailable")
