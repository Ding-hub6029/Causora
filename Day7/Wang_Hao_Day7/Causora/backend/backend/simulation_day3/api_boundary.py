"""Future POST /api/simulate Python boundary; NOT an HTTP server or 200 route.

The internal stochastic engine computes actual seeded statistics, but only on
pending synthetic evidence and an explicitly unapproved operating policy.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from simulation_day1.interfaces import ContractInputError, validate_request
from simulation_day2.api_boundary import _failure
from simulation_day2.deterministic import InputNotApproved, read_source_manifest, require_reviewed_bundle
from simulation_day3.policy import Day3Policy


def simulate_v1_boundary(request: Any, *, request_id: str,
                         project_root: Path, policy_data: dict | None = None,
                         reviewed_bundle: Path | None = None) -> tuple[int, dict]:
    """Only v1 ApiFailure is authorized; no public success until both gates pass."""
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("the HTTP adapter must supply a nonempty requestId")
    try:
        read_source_manifest(project_root)
        from hashlib import sha256
        from simulation_day1.interfaces import FROZEN_MOCK_SHA256
        raw = (project_root / "demo_data/causora_day1_mock.json").read_bytes()
        if sha256(raw).hexdigest() != FROZEN_MOCK_SHA256:
            raise ValueError("unreviewed mock was modified")
        contract = json.loads(raw.decode("utf-8"))["contract"]
    except (OSError, ValueError, TypeError, KeyError):
        return _failure(request_id=request_id, http_status=503, code="simulation_failed",
                        message="The frozen synthetic dataset is unavailable or has changed.",
                        reason="dataset_unavailable")
    try:
        if not isinstance(request, dict):
            raise ValueError("JSON object required")
        validate_request(request, dataset_id="ds-001", contract=contract,
                         allow_unfrozen_scenarios=True)
        if policy_data is not None:
            Day3Policy.model_validate_json(json.dumps(policy_data, ensure_ascii=False, allow_nan=False))
    except (ContractInputError, ValidationError, ValueError, KeyError, TypeError):
        return _failure(request_id=request_id, http_status=422, code="validation_error",
                        message="Invalid simulation request or stochastic input policy.",
                        reason="invalid_input")
    if reviewed_bundle is None:
        return _failure(request_id=request_id, http_status=503, code="simulation_failed",
                        message="Contract evidence and demo assumptions await human review.",
                        reason="human_review_pending")
    try:
        reviewed = require_reviewed_bundle(project_root, reviewed_bundle)
        validate_request(request, dataset_id="ds-001", contract=reviewed.model_dump(mode="json"),
                         allow_unfrozen_scenarios=True)
    except (InputNotApproved, ContractInputError, ValidationError, ValueError, OSError, ImportError):
        return _failure(request_id=request_id, http_status=503, code="simulation_failed",
                        message="Reviewed synthetic contract bundle is absent, stale or invalid.",
                        reason="review_bundle_not_verified")
    if policy_data is None:
        return _failure(request_id=request_id, http_status=503, code="simulation_failed",
                        message="A team-approved physical and financial simulation policy is required.",
                        reason="missing_policy")
    # Every policy accepted by the current model is explicitly UNAPPROVED;
    # even a reviewed synthetic contract cannot make its output decision-ready.
    return _failure(request_id=request_id, http_status=503, code="simulation_failed",
                    message="Physical, financial and short-history distribution inputs need team approval.",
                    reason="simulation_policy_unapproved")
