"""Regression tests for the Jinzhu unreviewed-development HTTP MC boundary.

The preferred source is the parent-captured real HTTP exchange in
``mc_examples/http_base``; its response headers are validated too.  The backend
attachment is only an explicitly labelled test-fixture fallback via
``CAUSORA_DAY3_BACKEND``.  No backend path is hard-coded, and unavailable
external input is skipped rather than replaced with a local mock.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

import pytest

from agent_day3.mc_validation import canonical_sha, resolve_pointer, validate_mc_response


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEV_HEADERS = {
    "X-Causora-Review-Status": "unreviewed-development-only",
    "X-Causora-Trace-Contract": "causora.contract.v2-dev-unreviewed",
    "X-Causora-Execution-Mode": "unreviewed-development-only",
}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _capture(directory_name: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str] | None:
    """Read one stored real HTTP exchange, including the transport headers."""
    directory = PROJECT_ROOT / "mc_examples" / directory_name
    request = _read_json(directory / "request.json")
    response = _read_json(directory / "response.json")
    transport = _read_json(directory / "transport.json")
    headers = transport.get("headers") if transport else None
    if request is None or response is None or not isinstance(headers, dict):
        return None
    return request, response, headers, f"captured real HTTP fixture: mc_examples/{directory_name}"


@pytest.fixture(scope="session")
def fixture_pair() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    """Use actual HTTP first; use the clearly test-only backend fixture only as fallback."""
    captured = _capture("http_base")
    if captured is not None:
        return captured
    configured = os.environ.get("CAUSORA_DAY3_BACKEND")
    if configured:
        root = Path(configured).expanduser()
        request_path = root / "examples" / "fixtures" / "simulate_request_v1_TEST_FIXTURE_ONLY.json"
        response_path = root / "examples" / "fixtures" / "simulate_response_v2_UNREVIEWED_DEV_ONLY.json"
        request, response = _read_json(request_path), _read_json(response_path)
        if request is not None and response is not None:
            return request, response, _headers(response), f"explicit test-only backend fixture: {root}"
    pytest.skip(
        "Jinzhu HTTP MC fixture is unavailable; capture mc_examples/http_base or set CAUSORA_DAY3_BACKEND "
        "for the explicit test-only fixture."
    )


@pytest.fixture()
def payloads(fixture_pair: tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]) -> tuple[dict[str, Any], dict[str, Any]]:
    request, response, _headers_from_transport, _source = fixture_pair
    return copy.deepcopy(request), copy.deepcopy(response)


@pytest.fixture()
def transport_headers(fixture_pair: tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]) -> dict[str, Any]:
    return copy.deepcopy(fixture_pair[2])


@pytest.fixture(scope="session")
def changed_http_captures() -> tuple[
    tuple[dict[str, Any], dict[str, Any], dict[str, Any], str],
    tuple[dict[str, Any], dict[str, Any], dict[str, Any], str],
    tuple[dict[str, Any], dict[str, Any], dict[str, Any], str],
]:
    captures = tuple(_capture(name) for name in ("http_base", "http_demand_changed", "http_lead_changed"))
    if any(capture is None for capture in captures):
        pytest.skip("real HTTP changed-request captures are unavailable under mc_examples/")
    return captures  # type: ignore[return-value]


def _headers(response: dict[str, Any]) -> dict[str, str]:
    return {**DEV_HEADERS, "X-Request-Id": response["requestId"]}


def _reject(request: dict[str, Any], response: dict[str, Any], headers: dict[str, str] | None = None) -> None:
    with pytest.raises(ValueError):
        validate_mc_response(request, response, headers)


def test_explicit_unreviewed_mc_fixture_passes_full_audit(
    fixture_pair: tuple[dict[str, Any], dict[str, Any], dict[str, Any], str],
    payloads: tuple[dict[str, Any], dict[str, Any]], transport_headers: dict[str, Any],
) -> None:
    request, response = payloads
    summary = validate_mc_response(request, response, transport_headers)
    assert "fixture" in fixture_pair[3]
    assert summary == {
        "kind": "CAUSORA_DAY3_UNREVIEWED_MC_HTTP_VALIDATION_V1",
        "devOnly": True,
        "decisionReady": False,
        "matrixCells": 9,
        "sampleWeeks": 936,
        "simulationId": response["data"]["simulation"]["simulationId"],
        "dataVersion": response["data"]["simulation"]["dataVersion"],
        "requestSha256": canonical_sha(request),
        "responseSha256": canonical_sha(response),
    }


def test_canonical_sha_retains_original_integer_float_representation() -> None:
    assert canonical_sha({"b": "é", "a": 1}) == canonical_sha({"a": 1, "b": "é"})
    assert canonical_sha({"number": 1}) != canonical_sha({"number": 1.0})
    with pytest.raises(ValueError):
        canonical_sha({"notJson": float("nan")})


def test_resolve_pointer_uses_rfc6901_escapes_and_rejects_missing_values() -> None:
    document = {"a/b": {"~key": ["zero"]}}
    assert resolve_pointer(document, "/a~1b/~0key/0") == "zero"
    assert resolve_pointer(document, "") is document
    with pytest.raises(ValueError):
        resolve_pointer(document, "/a~2b")
    with pytest.raises(ValueError):
        resolve_pointer(document, "/a~1b/~0key/1")


def test_headers_are_optional_but_complete_development_markers_are_required_when_supplied(
    payloads: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    request, response = payloads
    assert validate_mc_response(request, response)["matrixCells"] == 9
    _reject(request, response, {"X-Request-Id": response["requestId"]})


def test_header_request_id_must_match_response_body(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    headers = _headers(response)
    headers["X-Request-Id"] = "different-request"
    _reject(request, response, headers)


def test_execution_mode_tampering_is_rejected(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    response["data"]["executionContext"]["mode"] = "reviewed_release_gated"
    _reject(request, response)


def test_fake_review_record_is_rejected(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    response["data"]["traces"]["baseline"]["D0"]["runIdentity"]["reviewRecordId"] = "pretend-review-1"
    _reject(request, response)


def test_v1_or_local_mock_success_is_rejected(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    response["schemaVersion"] = "causora.contract.v1"
    response["data"]["simulation"]["simulationId"] = "sim-LOCAL_MOCK-001"
    _reject(request, response)


def test_zero_monte_carlo_runs_is_rejected(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    response["data"]["simulation"]["monteCarloRuns"] = 0
    _reject(request, response)


def test_request_seed_mismatch_is_rejected(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    request["seed"] += 1
    _reject(request, response)


def test_changed_demand_request_cannot_reuse_old_response(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    request["scenarios"][0]["demandShock"] = 1
    _reject(request, response)


def test_trace_option_binding_mismatch_is_rejected(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    parameters = response["data"]["traces"]["baseline"]["D1"]["parameters"]
    next(row for row in parameters if row["key"] == "option.shareA")["value"] = 1.0
    _reject(request, response)


def test_trace_identity_mismatch_is_rejected(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    response["data"]["traces"]["lead-stress"]["D2"]["scenarioId"] = "baseline"
    _reject(request, response)


def test_probability_count_identity_mismatch_is_rejected(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    probability = response["data"]["traces"]["baseline"]["D0"]["stockoutProbability"]
    probability["numeratorStockoutRuns"] += 1
    _reject(request, response)


def test_p90_rank_and_common_monte_carlo_denominator_are_rejected_when_tampered(
    payloads: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    request, response = payloads
    response["data"]["traces"]["baseline"]["D0"]["cashOutflowP90"]["rankOneBased"] = 899
    _reject(request, response)


def test_raw_rounding_difference_mismatch_is_rejected(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    rounding = response["data"]["traces"]["baseline"]["D0"]["components"][0]["roundingAudit"]
    rounding["displayedMinusRawMeanUsd"] = "0"
    _reject(request, response)


def test_missing_and_duplicate_delta_identities_are_rejected(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    response["data"]["deltas"].pop()
    _reject(request, response)

    request, response = copy.deepcopy(payloads[0]), copy.deepcopy(payloads[1])
    response["data"]["deltas"][1]["optionId"] = "D0"
    _reject(request, response)


def test_selection_must_follow_request_risk_budget_and_feasibility(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    response["data"]["selections"]["baseline"]["recommendedOptionId"] = "D0"
    _reject(request, response)


def test_sample_path_cannot_claim_aggregate_semantics(payloads: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = payloads
    path = response["data"]["traces"]["baseline"]["D0"]["samplePath"]
    path["classification"] = "aggregate_monte_carlo_trials"
    _reject(request, response)


def test_real_http_changed_requests_are_bound_and_produce_distinct_run_ids(
    changed_http_captures: tuple[
        tuple[dict[str, Any], dict[str, Any], dict[str, Any], str],
        tuple[dict[str, Any], dict[str, Any], dict[str, Any], str],
        tuple[dict[str, Any], dict[str, Any], dict[str, Any], str],
    ]
) -> None:
    base, demand_changed, lead_changed = changed_http_captures
    base_request, base_response, base_headers, _base_source = base
    demand_request, demand_response, demand_headers, _demand_source = demand_changed
    lead_request, lead_response, lead_headers, _lead_source = lead_changed

    base_summary = validate_mc_response(base_request, base_response, base_headers)
    demand_summary = validate_mc_response(demand_request, demand_response, demand_headers)
    lead_summary = validate_mc_response(lead_request, lead_response, lead_headers)
    assert {base_summary["simulationId"], demand_summary["simulationId"], lead_summary["simulationId"]} == {
        base_response["data"]["simulation"]["simulationId"],
        demand_response["data"]["simulation"]["simulationId"],
        lead_response["data"]["simulation"]["simulationId"],
    }
    assert len({base_summary["simulationId"], demand_summary["simulationId"], lead_summary["simulationId"]}) == 3

    # An altered request cannot be paired with a response generated for the base
    # request, even though all three captures share the same development mode.
    _reject(demand_request, base_response, base_headers)
    _reject(lead_request, base_response, base_headers)
