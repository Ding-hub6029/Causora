"""Day 5 Wang lifecycle regressions.

All reviewed data in this module is created by the existing TEST_FIXTURE_ONLY gate
helper.  The tests never initialise a provider or make a network/model call.
"""
from __future__ import annotations

import asyncio
import copy
import json
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.boardroom_adapter as adapter
import app.service as service
from app.boardroom_adapter import BoardroomAdapterError, repository
from test_gated_service import REQUEST, _configure_verified_fixture


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _clear_repository() -> None:
    repository.clear()
    yield
    repository.clear()


def _request_with_demand_drop(shock: float) -> dict:
    request = copy.deepcopy(REQUEST)
    scenario = next(item for item in request["scenarios"] if item["id"] == "demand-drop")
    scenario["demandShock"] = shock
    scenario["demandUnits24m"] = round(26_000 * (1 + shock / 100))
    return request


def _boardroom_payload(simulated: dict, scenario_id: str = "baseline") -> dict:
    simulation = simulated["data"]["simulation"]
    return {
        "schemaVersion": "causora.contract.v1",
        "simulationId": simulation["simulationId"],
        "dataVersion": simulation["dataVersion"],
        "scenarioId": scenario_id,
    }


def test_new_completed_simulation_rejects_an_old_inflight_ai_response(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The post-AI current-run recheck must prevent a retired result from returning."""
    _configure_verified_fixture(monkeypatch, tmp_path)
    first = TestClient(service.app).post(
        "/api/simulate", json=REQUEST, headers={"X-Request-Id": "sim-first"}
    )
    assert first.status_code == 200
    old_request = _boardroom_payload(first.json())

    started = threading.Event()
    release = threading.Event()

    async def slow_local_only_pipeline(*_args, **_kwargs):
        started.set()
        await asyncio.to_thread(release.wait, 5)
        # The route must re-resolve the Boardroom request before it can serialize
        # this synthetic local-only return. It therefore cannot become a response.
        return {}, "primary", "complete"

    monkeypatch.setattr(adapter, "_run_formal_pipeline", slow_local_only_pipeline)
    received: dict[str, object] = {}

    def post_old_boardroom() -> None:
        response = TestClient(service.app).post(
            "/api/boardroom", json=old_request, headers={"X-Request-Id": "br-old-inflight"}
        )
        received["status"] = response.status_code
        received["body"] = response.json()
        received["headers"] = dict(response.headers)

    worker = threading.Thread(target=post_old_boardroom, daemon=True)
    worker.start()
    assert started.wait(5), "the local-only stand-in did not reach the awaited AI boundary"

    replacement = TestClient(service.app).post(
        "/api/simulate", json=_request_with_demand_drop(-20), headers={"X-Request-Id": "sim-replacement"}
    )
    assert replacement.status_code == 200
    replacement_simulation_id = replacement.json()["data"]["simulation"]["simulationId"]
    assert replacement_simulation_id != old_request["simulationId"]

    release.set()
    worker.join(8)
    assert not worker.is_alive()
    assert received["status"] == 422
    body = received["body"]
    assert body["error"]["details"]["reason"] == "stale_simulation"
    assert body["requestId"] == body["error"]["requestId"] == "br-old-inflight"
    headers = received["headers"]
    assert headers["x-request-id"] == "br-old-inflight"
    assert headers["x-causora-current-simulation"] == replacement_simulation_id


def test_ai_failure_keeps_matrix_formula_trace_and_source_backed_evidence_available(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A provider setup failure must not erase the completed reviewed simulation."""
    _configure_verified_fixture(monkeypatch, tmp_path)
    client = TestClient(service.app)
    simulated = client.post("/api/simulate", json=REQUEST, headers={"X-Request-Id": "sim-trace-retained"})
    assert simulated.status_code == 200
    simulation_body = simulated.json()
    simulation = simulation_body["data"]["simulation"]
    assert simulation_body["data"]["traces"]["baseline"]["D1"]["simulationId"] == simulation["simulationId"]

    def no_provider(*_args, **_kwargs):
        raise BoardroomAdapterError("provider_unavailable", "Local test provider setup is unavailable.", status=503)

    monkeypatch.setattr(adapter, "_load_formal_runtime", no_provider)
    failed = client.post(
        "/api/boardroom", json=_boardroom_payload(simulation_body), headers={"X-Request-Id": "br-provider-failure"}
    )
    assert failed.status_code == 503
    assert failed.json()["error"]["details"]["reason"] == "provider_unavailable"
    assert failed.headers["x-request-id"] == "br-provider-failure"

    evidence = client.get("/api/evidence/EV-024", headers={"X-Request-Id": "ev-trace-retained"})
    assert evidence.status_code == 200
    assert evidence.headers["x-request-id"] == "ev-trace-retained"
    assert evidence.headers["x-causora-current-simulation"] == simulation["simulationId"]
    assert evidence.json()["dataVersion"] == simulation["dataVersion"]
    assert evidence.json()["data"]["evidence"]["id"] == "EV-024"
    assert repository.current().simulation_id == simulation["simulationId"]


def test_no_feasible_option_skips_provider_dispatch_and_returns_no_recommendation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No-feasible formal requests run the real local branch but dispatch no provider."""
    _configure_verified_fixture(monkeypatch, tmp_path)
    impossible = copy.deepcopy(REQUEST)
    impossible["riskThreshold"] = 0
    impossible["budgetCeilingUsd"] = 0
    for scenario in impossible["scenarios"]:
        scenario["demandShock"] = -100
        scenario["demandUnits24m"] = 0

    client = TestClient(service.app)
    simulated = client.post("/api/simulate", json=impossible, headers={"X-Request-Id": "sim-no-feasible"})
    assert simulated.status_code == 200
    body = simulated.json()
    assert body["data"]["selections"]["baseline"]["status"] == "no_feasible_option"

    def unexpected_provider_dispatch(*_args, **_kwargs):
        raise AssertionError("No-feasible Boardroom path must not initialise or dispatch an AI provider")

    monkeypatch.setattr(adapter, "_load_formal_runtime", unexpected_provider_dispatch)
    boardroom = client.post(
        "/api/boardroom", json=_boardroom_payload(body), headers={"X-Request-Id": "br-no-feasible"}
    )
    assert boardroom.status_code == 200
    result = boardroom.json()
    assert result["requestId"] == "br-no-feasible"
    assert result["dataVersion"] == body["data"]["simulation"]["dataVersion"]
    assert result["data"] == {
        "scenarioId": "baseline",
        "agentOutputs": [],
        "criticIssues": [],
        "brief": {
            "scenarioId": "baseline",
            "status": "no_feasible_option",
            "recommendedOptionId": None,
            "constraintViolations": body["data"]["selections"]["baseline"]["constraintViolations"],
            "message": "No simulated option meets the current constraints. Revise inputs and run the simulator again.",
        },
        "numericGuardrail": {"passed": True, "rejectedClaims": []},
    }
    assert boardroom.headers["x-request-id"] == "br-no-feasible"
    assert boardroom.headers["x-causora-provider-mode"] == "primary"
    assert boardroom.headers["x-causora-critic-status"] == "complete"
