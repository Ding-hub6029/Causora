"""Runnable local HTTP boundary for Causora Day 3.

Active behavior is intentionally fail-closed:
- malformed v1 requests return a typed 422 envelope;
- valid requests return a typed 503 until Wang's verified bundle and a team
  policy verifier are configured;
- a v2 Matrix + Trace 200 is reachable only after three external verifiers
  confirm the reviewed contract, team policy and jointly frozen v2 contract.

An exact, explicitly named local-development override may return an unreviewed
v2 integration response. It is never the default and labels every response and
trace as unreviewed/non-decision output.
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4
from typing import Any

from fastapi import Body, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.boardroom_adapter import BoardroomAdapterError, install_boardroom_routes, register_simulation
from app.config import DEFAULT_DATASET_ID, PROJECT_ROOT, SCHEMA_VERSION_V1, cors_origins, unreviewed_development_mode_enabled
from app.gates import (
    GateResult,
    TraceContractReleaseResult,
    resolve_trace_contract_v2_release,
    resolve_verified_inputs,
)
from app.reviewed_success import build_reviewed_success_v2
from app.review_admission import ReviewAdmissionMiddleware
from app.unreviewed_development import build_unreviewed_development_success_v2
from simulation_day1.interfaces import ContractInputError, validate_request

app = FastAPI(title="Causora Day 3 Gated Simulation API", version="0.5.0-reviewed-and-dev")
app.add_middleware(ReviewAdmissionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-Request-Id"],
    expose_headers=["X-Causora-Review-Status", "X-Causora-Trace-Contract", "X-Causora-Execution-Mode", "X-Request-Id",
                    "X-Causora-Provider-Mode", "X-Causora-Critic-Status", "X-Causora-Current-Simulation"],
)


def _request_id(request: Request | None = None) -> str:
    provided = request.headers.get("X-Request-Id", "").strip() if request else ""
    return provided[:128] if provided else f"req-{uuid4().hex}"


def _headers(request_id: str, *, review_status: str, trace_contract: str = "release-gated-v2-pending",
             execution_mode: str = "review-gated") -> dict[str, str]:
    return {
        "Cache-Control": "no-store",
        "X-Request-Id": request_id,
        "X-Causora-Review-Status": review_status,
        "X-Causora-Trace-Contract": trace_contract,
        "X-Causora-Execution-Mode": execution_mode,
    }


def _failure(status: int, request_id: str, *, code: str, message: str, reason: str,
             review_status: str = "pending", trace_contract: str = "release-gated-v2-pending",
             missing_reasons: tuple[str, ...] = ()) -> JSONResponse:
    body = {
        "schemaVersion": SCHEMA_VERSION_V1,
        "requestId": request_id,
        "error": {
            "code": code,
            "message": message,
            "details": {
                "reason": reason,
                "missingReasons": list(missing_reasons),
                "requestSchemaVersion": "causora.contract.v1",
                "successSchemaVersion": "causora.contract.v2",
                "traceContract": "causora.contract.v2 (release-gated)",
            },
            "requestId": request_id,
        },
    }
    return JSONResponse(status_code=status, content=body, headers=_headers(
        request_id, review_status=review_status, trace_contract=trace_contract))


def _load_frozen_contract(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    payload = json.loads((project_root / "demo_data" / "causora_day1_mock.json").read_text(encoding="utf-8"))
    contract = payload.get("contract")
    if not isinstance(contract, dict):
        raise ContractInputError("frozen dataset contract is unavailable")
    return contract


def _load_boardroom_source_evidence(project_root: Path = PROJECT_ROOT) -> list[dict[str, Any]]:
    """Read the existing public source registry; do not fabricate evidence IDs."""
    payload = json.loads((project_root / "demo_data" / "causora_day1_mock.json").read_text(encoding="utf-8"))
    evidence = payload.get("evidence")
    if not isinstance(evidence, list) or any(not isinstance(item, dict) for item in evidence):
        raise ContractInputError("frozen evidence registry is unavailable")
    return [dict(item) for item in evidence]


def _register_boardroom_simulation(request_dict: dict[str, Any], success: dict[str, Any], contract: dict[str, Any],
                                   simulation_request_id: str) -> None:
    """Retain the exact completed run only after source-backed evidence checks.

    A Matrix + Trace response must not appear Boardroom-eligible if its physical
    evidence cannot be verified or its immutable identity cannot be retained.
    This performs no second Monte Carlo calculation and never invokes an AI
    provider.  AI later failing or timing out leaves the retained simulation
    untouched.
    """
    register_simulation(request_dict, success, contract, _load_boardroom_source_evidence(), PROJECT_ROOT,
                        simulation_request_id)


def _gate_status() -> GateResult:
    return resolve_verified_inputs(PROJECT_ROOT)


def _trace_contract_status() -> TraceContractReleaseResult:
    return resolve_trace_contract_v2_release(PROJECT_ROOT)


@app.exception_handler(RequestValidationError)
async def request_validation_error(request: Request, _exc: RequestValidationError) -> JSONResponse:
    request_id = _request_id(request)
    return _failure(422, request_id, code="validation_error", message="Invalid JSON request body.",
                    reason="invalid_json")


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    request_id = _request_id(request)
    dev_mode = unreviewed_development_mode_enabled()
    if dev_mode:
        body = {
            "schemaVersion": SCHEMA_VERSION_V1,
            "dataVersion": "UNREVIEWED_DEV_ONLY",
            "requestId": request_id,
            "data": {
                "service": "ready",
                "simulation": "unreviewed_development_only",
                "evidence": "not_reviewed_development_only",
                "missingReasons": ["human_review_pending", "simulation_policy_unapproved", "trace_contract_unconfirmed"],
                "traceContract": "causora.contract.v2 development shape only",
                "provider": "not_required",
                "banner": "UNREVIEWED — DEVELOPMENT ONLY. NOT DECISION-READY.",
            },
        }
        return JSONResponse(status_code=200, content=body, headers=_headers(
            request_id, review_status="unreviewed-development-only", trace_contract="causora.contract.v2-dev-unreviewed",
            execution_mode="unreviewed-development-only"))
    gate = _gate_status()
    trace_contract = _trace_contract_status()
    sources_ready = all((PROJECT_ROOT / relative).is_file() for relative in (
        "demo_data/causora_day1_mock.json", "simulation_day1/demo_inputs_v1.json",
        "simulation_day3/monte_carlo.py", "simulation_day3/examples/UNAPPROVED_MC_POLICY.json",
    ))
    if not gate.ready:
        simulation_status = "review_pending"
        evidence_status = gate.reason
    elif not trace_contract.ready:
        simulation_status = "contract_release_pending"
        evidence_status = "verified"
    else:
        simulation_status = "ready"
        evidence_status = "verified"
    body = {
        "schemaVersion": SCHEMA_VERSION_V1,
        "dataVersion": "pending-review" if not gate.ready else gate.data_version,
        "requestId": request_id,
        "data": {
            "service": "ready" if sources_ready else "source_files_unavailable",
            "simulation": simulation_status,
            "evidence": evidence_status,
            "missingReasons": list(gate.missing_reasons) + ([] if trace_contract.ready else [trace_contract.reason]),
            "traceContract": "causora.contract.v2" if trace_contract.ready else "release-gated",
            "provider": "not_required",
        },
    }
    return JSONResponse(
        status_code=200 if sources_ready else 503,
        content=body,
        headers=_headers(
            request_id,
            review_status="reviewed" if gate.ready else "pending",
            trace_contract="causora.contract.v2" if trace_contract.ready else "release-gated-v2-pending",
        ),
    )


@app.post("/api/simulate")
async def simulate(request: Request, payload: Any = Body(...)) -> JSONResponse:
    """Validate v1 request, then use explicit dev mode or the fail-closed reviewed route."""
    request_id = _request_id(request)
    try:
        if not isinstance(payload, dict):
            raise ContractInputError("JSON object required")
        # Before review is available, validate the v1 wire shape only. The
        # reviewed contract (not the frozen mock) validates forecast/scenario
        # coherence inside the reviewed engine once all gates pass.
        validate_request(payload, dataset_id=DEFAULT_DATASET_ID, contract=None, allow_unfrozen_scenarios=True)
    except (ContractInputError, OSError, ValueError, TypeError, KeyError):
        return _failure(422, request_id, code="validation_error",
                        message="Invalid simulation request or unavailable frozen dataset.",
                        reason="invalid_input")

    if unreviewed_development_mode_enabled():
        try:
            success = build_unreviewed_development_success_v2(payload, request_id=request_id)
            # Retain the actual frozen development contract for Evidence viewing
            # and stale-run detection only. The Boardroom adapter rejects this
            # mode before any formal pipeline/provider invocation.
            _register_boardroom_simulation(payload, success, _load_frozen_contract(), request_id)
        except BoardroomAdapterError as exc:
            return _failure(503, request_id, code="simulation_failed",
                            message="Development calculation completed but its source-backed run record could not be stored.",
                            reason=exc.reason, review_status="unreviewed-development-only",
                            trace_contract="causora.contract.v2-dev-unreviewed")
        except (OSError, ValueError, TypeError, KeyError):
            return _failure(503, request_id, code="simulation_failed",
                            message="Unreviewed development calculation could not produce a Matrix + Trace response.",
                            reason="unreviewed_development_execution_failed", review_status="unreviewed-development-only",
                            trace_contract="causora.contract.v2-dev-unreviewed")
        return JSONResponse(status_code=200, content=success, headers=_headers(
            request_id, review_status="unreviewed-development-only", trace_contract="causora.contract.v2-dev-unreviewed",
            execution_mode="unreviewed-development-only"))

    gate = _gate_status()
    if not gate.ready:
        return _failure(503, request_id, code="simulation_failed", message=gate.message,
                        reason=gate.reason, review_status="pending", missing_reasons=gate.missing_reasons)

    trace_contract = _trace_contract_status()
    if not trace_contract.ready:
        return _failure(503, request_id, code="simulation_failed", message=trace_contract.message,
                        reason=trace_contract.reason, review_status="reviewed", missing_reasons=(trace_contract.reason,))

    try:
        success = build_reviewed_success_v2(payload, gate, trace_contract, request_id=request_id)
        if gate.contract is None:
            raise ValueError("reviewed contract is unavailable")
        _register_boardroom_simulation(payload, success, gate.contract, request_id)
    except BoardroomAdapterError as exc:
        return _failure(503, request_id, code="simulation_failed",
                        message="Verified simulation completed but its source-backed run record could not be stored.",
                        reason=exc.reason, review_status="reviewed", trace_contract="causora.contract.v2")
    except (OSError, ValueError, TypeError, KeyError):
        # Review/approval source details remain server-side; no fallback to an
        # UNAPPROVED preview is allowed when a reviewed run itself fails.
        return _failure(503, request_id, code="simulation_failed",
                        message="Verified simulation inputs could not produce an auditable Matrix + Trace response.",
                        reason="reviewed_simulation_execution_failed", review_status="reviewed",
                        trace_contract="causora.contract.v2")
    return JSONResponse(status_code=200, content=success, headers=_headers(
        request_id, review_status="reviewed", trace_contract="causora.contract.v2", execution_mode="reviewed-release-gated"))


install_boardroom_routes(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.service:app", host="0.0.0.0", port=8000, reload=False)
