"""Regression tests for the unreviewed Monte Carlo v2 role adapter."""
from __future__ import annotations

import asyncio
import copy
import json
import os
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("agent_day3.mc_validation", reason="MC validation is delivered by its owning agent")

from agent_day3.mc_roles import DevClaimStubProvider, build_mc_projections, run_mc_parallel


FIXTURE_NAME = "simulate_response_v2_UNREVIEWED_DEV_ONLY.json"


def _backend_root() -> Path:
    configured = os.environ.get("CAUSORA_DAY3_BACKEND")
    candidates = [
        Path(configured).expanduser() if configured else None,
        Path("/home/ubuntu/causora/jinzhu-day3-current/Causora-DengJinzhu-Day3-Integrated/backend"),
    ]
    for root in candidates:
        if root and (root / "examples" / "simulate_request_v1.json").is_file():
            return root
    pytest.skip("Set CAUSORA_DAY3_BACKEND to a backend containing the v2 development fixture")


@pytest.fixture(scope="session")
def actual_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    capture_root = Path(__file__).resolve().parents[2] / "mc_examples" / "http_base"
    captured_request = capture_root / "request.json"
    captured_response = capture_root / "response.json"
    if captured_request.is_file() and captured_response.is_file():
        return json.loads(captured_request.read_text(encoding="utf-8")), json.loads(captured_response.read_text(encoding="utf-8"))
    root = _backend_root()
    request_path = root / "examples" / "simulate_request_v1.json"
    response_candidates = [
        root / "examples" / "fixtures" / FIXTURE_NAME,
        root / "examples" / "http-dev-unreviewed" / FIXTURE_NAME,
    ]
    response_path = next((path for path in response_candidates if path.is_file()), None)
    if response_path is None:
        pytest.skip("No actual or fallback MC response fixture is available")
    request_candidates = [request_path]
    resolved_request = next((path for path in request_candidates if path.is_file()), None)
    assert resolved_request is not None
    return json.loads(resolved_request.read_text(encoding="utf-8")), json.loads(response_path.read_text(encoding="utf-8"))


@pytest.fixture
def request_response(actual_inputs: tuple[dict[str, Any], dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    return copy.deepcopy(actual_inputs[0]), copy.deepcopy(actual_inputs[1])


def _selection(role: str, payload: dict[str, Any], *, status: str = "Watch") -> dict[str, Any]:
    return {"role": role, "claim_ids": [payload["claimCatalog"][0]["id"]], "status": status}


def _run(request: dict[str, Any], response: dict[str, Any], provider: Any, **kwargs: Any) -> dict[str, Any]:
    return asyncio.run(run_mc_parallel(request, response, provider=provider, scenario_id="demand-drop", enabled=True, **kwargs))


def test_builds_strict_filtered_views(request_response: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = request_response
    views = build_mc_projections(request, response, "demand-drop")
    cfo = views["CFO"].model_dump(mode="json")
    coo = views["COO"].model_dump(mode="json")
    risk = views["Risk"].model_dump(mode="json")
    assert set(views) == {"CFO", "COO", "Risk"}
    assert cfo["options"][0]["expectedTco"] == response["data"]["simulation"]["matrix"]["demand-drop"][0]["expectedTco"]
    assert "stockoutProbability" not in json.dumps(cfo)
    assert "cashOutflowP90" not in json.dumps(coo)
    assert "expectedTco" not in json.dumps(risk)
    serialized_risk = json.dumps(risk).casefold()
    for forbidden in ("sourcepath", "sourcehashpayload", "pdfquote", "humanreceipt", "fullmatrix", "fulltraces", "samplepath", "unitsfroma"):
        assert forbidden not in serialized_risk


def test_requires_explicit_enablement(request_response: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = request_response
    with pytest.raises(PermissionError, match="enabled=True"):
        asyncio.run(run_mc_parallel(request, response, provider=DevClaimStubProvider(), scenario_id="demand-drop"))


def test_result_has_unreviewed_identity_and_stable_roles(request_response: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = request_response
    result = _run(request, response, DevClaimStubProvider())
    assert result["kind"] == "CAUSORA_WANG_DAY3_MC_DEV_ANALYSIS_V1"
    assert result["sourceMode"] == "UNREVIEWED_MONTE_CARLO_SERVICE"
    assert result["decisionReady"] is False
    assert result["humanReviewStatus"] == "not_reviewed_development_only"
    assert result["executionContext"] == response["data"]["executionContext"]
    assert result["monteCarloRuns"] == 1000
    assert result["state"] == "ALL_READY"
    assert [item["role"] for item in result["outputs"]] == ["CFO", "COO", "Risk"]
    assert "selections" not in json.dumps(result).casefold()


def test_matching_metrics_and_typed_bindings(request_response: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = request_response
    result = _run(request, response, DevClaimStubProvider())
    cfo = result["outputs"][0]
    expected_ref = "response:/data/simulation/matrix/demand-drop/0/expectedTco"
    assert cfo["metricBindings"][expected_ref]["value"] == response["data"]["simulation"]["matrix"]["demand-drop"][0]["expectedTco"]
    assert type(cfo["metricBindings"][expected_ref]["value"]) is int
    assert set(cfo["metricRefs"]) == set(cfo["metricBindings"])
    for output in result["outputs"]:
        for reference, binding in output["metricBindings"].items():
            assert reference.startswith(("response:/", "request:/"))
            assert binding["responseSha256"] == result["responseSha256"]
            assert binding["simulationId"] == result["simulationId"]
            assert binding["dataVersion"] == result["dataVersion"]
            assert binding["scenarioId"] == "demand-drop"


def test_clause_and_request_references_are_canonical(request_response: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = request_response
    result = _run(request, response, DevClaimStubProvider())
    risk = result["outputs"][2]
    values = list(risk["metricBindings"].values())
    assert any(item["pointer"].startswith("/data/traces/demand-drop/D0/parameters/") and item["metric"] == "contract.renewalLocked" for item in values)
    assert any(item["document"] == "request" and item["pointer"] == "/riskThreshold" for item in values)
    assert all("sourceFile" not in item and "sourceSha256" not in item for item in values)


def test_provider_receives_only_role_local_data(request_response: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = request_response

    class InspectingProvider:
        kind = "TEST_DOUBLE"

        async def complete(self, *, role, system, payload, schema):
            del system
            serialized = json.dumps(payload, sort_keys=True).casefold()
            assert set(payload) == {"role", "view", "claimCatalog"}
            assert payload["role"] == role == payload["view"]["role"]
            assert set(schema["properties"]) == {"role", "claim_ids", "status"}
            assert "uniqueitems" not in json.dumps(schema).casefold()
            for forbidden in ("selections", "recommend", "fullmatrix", "fulltraces", "samplepath", "sourcefile", "pdfquote", "humanreceipt"):
                assert forbidden not in serialized
            if role == "CFO":
                assert "stockoutprobability" not in serialized
                assert "contract" not in serialized
            elif role == "COO":
                assert "expectedtco" not in serialized
                assert "cashoutflowp90" not in serialized
            else:
                assert "expectedtco" not in serialized
                assert "unitsfroma" not in serialized
            return _selection(role, payload)

    assert _run(request, response, InspectingProvider())["state"] == "ALL_READY"


def test_parallel_barrier_starts_all_roles(request_response: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = request_response

    class BarrierProvider:
        kind = "TEST_DOUBLE"

        def __init__(self) -> None:
            self.arrived: list[str] = []
            self.release = asyncio.Event()

        async def complete(self, *, role, system, payload, schema):
            del system, schema
            self.arrived.append(role)
            if len(self.arrived) == 3:
                self.release.set()
            await asyncio.wait_for(self.release.wait(), timeout=1)
            return _selection(role, payload)

    provider = BarrierProvider()
    result = _run(request, response, provider)
    assert provider.arrived == ["CFO", "COO", "Risk"]
    assert result["state"] == "ALL_READY"


def test_timeout_is_isolated_to_its_role(request_response: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = request_response

    class SlowProvider:
        kind = "TEST_DOUBLE"

        async def complete(self, *, role, system, payload, schema):
            del system, schema
            if role == "CFO":
                await asyncio.sleep(0.05)
            return _selection(role, payload)

    result = _run(request, response, SlowProvider(), timeout_seconds=0.001)
    assert result["state"] == "PARTIAL"
    assert result["outputs"][0]["failure"] == "timeout"
    assert [item["availability"] for item in result["outputs"][1:]] == ["DEV_ONLY", "DEV_ONLY"]


def test_provider_error_is_isolated_to_one_role(request_response: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = request_response

    class MixedProvider:
        kind = "TEST_DOUBLE"

        async def complete(self, *, role, system, payload, schema):
            del system, schema
            if role == "COO":
                raise RuntimeError("test failure")
            return _selection(role, payload)

    result = _run(request, response, MixedProvider())
    assert result["state"] == "PARTIAL"
    assert [item["failure"] for item in result["outputs"]] == [None, "provider_error", None]


def test_bad_claim_and_free_reason_text_are_rejected(request_response: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = request_response

    class InvalidProvider:
        kind = "TEST_DOUBLE"

        async def complete(self, *, role, system, payload, schema):
            del system, schema
            if role == "COO":
                return {"role": role, "claim_ids": ["not_in_catalog"], "status": "Watch"}
            if role == "Risk":
                return {**_selection(role, payload), "reason_text": "Provider prose is forbidden"}
            return _selection(role, payload)

    result = _run(request, response, InvalidProvider())
    assert result["state"] == "PARTIAL"
    assert [item["failure"] for item in result["outputs"]] == [None, "invalid_response", "invalid_response"]


def test_provider_mutation_cannot_change_saved_bindings(request_response: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = request_response
    original_expected = response["data"]["simulation"]["matrix"]["demand-drop"][0]["expectedTco"]

    class PoisonProvider:
        kind = "TEST_DOUBLE"

        async def complete(self, *, role, system, payload, schema):
            del system, schema
            payload["view"].clear()
            payload["claimCatalog"][0]["metricRefs"].clear()
            response["data"]["simulation"]["matrix"]["demand-drop"][0]["expectedTco"] = 1
            return {"role": role, "claim_ids": [payload["claimCatalog"][0]["id"]], "status": "Watch"}

    result = _run(request, response, PoisonProvider())
    cfo_binding = result["outputs"][0]["metricBindings"]["response:/data/simulation/matrix/demand-drop/0/expectedTco"]
    assert cfo_binding["value"] == original_expected
    assert cfo_binding["value"] != response["data"]["simulation"]["matrix"]["demand-drop"][0]["expectedTco"]


def test_stale_changed_request_is_rejected_before_provider(request_response: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = request_response
    request["scenarios"][1]["demandUnits24m"] += 1

    class CountingProvider:
        kind = "TEST_DOUBLE"

        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, **kwargs):
            self.calls += 1
            raise AssertionError("provider must not be called for stale input")

    provider = CountingProvider()
    with pytest.raises(ValueError, match="stale|validation|request"):
        _run(request, response, provider)
    assert provider.calls == 0


def test_outer_cancellation_propagates(request_response: tuple[dict[str, Any], dict[str, Any]]) -> None:
    request, response = request_response

    class HangingProvider:
        kind = "TEST_DOUBLE"

        def __init__(self) -> None:
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def complete(self, *, role, system, payload, schema):
            del role, system, payload, schema
            self.started.set()
            await self.release.wait()
            raise AssertionError("outer cancellation should arrive first")

    async def exercise() -> None:
        provider = HangingProvider()
        task = asyncio.create_task(run_mc_parallel(request, response, provider=provider, scenario_id="demand-drop", enabled=True))
        await provider.started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())
