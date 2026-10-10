#!/usr/bin/env python3
"""Offline/local HTTP smoke test. Never sends a model request or uses a key."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from start_day5 import simulation_environment

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    base = f"http://127.0.0.1:{port}"
    env = simulation_environment()
    env.update({"PORT": str(port), "HOST": "0.0.0.0"})
    rows = []

    def request(route, payload=None, request_id="wang-day5-local-smoke"):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(base + route, data=data, headers={"Content-Type": "application/json", "X-Request-Id": request_id})
        try:
            response = opener.open(req, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            value = json.loads(response.read())
            row = {"route": route, "status": response.code, "requestId": request_id,
                   "headers": dict(response.headers.items()), "response": value}
            rows.append(row)
            return row

    with (out / "backend.log").open("w") as log:
        proc = subprocess.Popen([sys.executable, "deployment/render_start.py"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            end = time.monotonic() + 35
            while True:
                if proc.poll() is not None:
                    raise RuntimeError("Backend exited; inspect backend.log")
                try:
                    health = request("/health", request_id="wang-day5-health")
                    if health["status"] == 200:
                        break
                except OSError:
                    pass
                if time.monotonic() >= end:
                    raise RuntimeError("Backend readiness timeout")
                time.sleep(0.3)
            assert health["response"]["data"]["simulation"] == "ready"
            sim_request = json.loads((ROOT / "backend/backend/examples/simulate_request_v1.json").read_text())
            simulation = request("/api/simulate", sim_request, "wang-day5-simulate")
            assert simulation["status"] == 200
            body = simulation["response"]
            assert body["schemaVersion"] == "causora.contract.v2"
            assert body["data"]["executionContext"]["decisionReady"] is True
            assert set(body["data"]["simulation"]["matrix"]) == {"baseline", "demand-drop", "lead-stress"}
            matrix_hash = digest(body["data"]["simulation"]["matrix"])
            trace_hash = digest(body["data"]["traces"])
            sim_id = body["data"]["simulation"]["simulationId"]
            version = body["dataVersion"]
            for evidence_id in ("EV-014", "EV-019", "EV-020", "EV-021", "EV-024", "EV-027"):
                item = request("/api/evidence/" + evidence_id, request_id="wang-day5-" + evidence_id)
                assert item["status"] == 200
                assert item["response"]["data"]["evidence"]["quoteMatched"] is True
                assert item["response"]["dataVersion"] == version
            failed_ai = request("/api/boardroom", {"schemaVersion": "causora.contract.v1", "simulationId": sim_id,
                                                   "dataVersion": version, "scenarioId": "baseline"}, "wang-day5-no-key")
            assert failed_ai["status"] == 503
            assert failed_ai["response"]["error"]["details"]["reason"] == "provider_unavailable"
            assert request("/api/evidence/EV-024", request_id="wang-day5-post-failure")["status"] == 200
            assert digest(body["data"]["simulation"]["matrix"]) == matrix_hash
            assert digest(body["data"]["traces"]) == trace_hash
            # One second identical simulation is a deterministic check, not an AI success.
            repeated = request("/api/simulate", sim_request, "wang-day5-repeat")
            assert repeated["status"] == 200
            assert digest(repeated["response"]["data"]["simulation"]["matrix"]) == matrix_hash
            assert digest(repeated["response"]["data"]["traces"]) == trace_hash
            result = {"kind": "LOCAL_HTTP_NO_MODEL_SMOKE", "status": "PASS", "modelCalls": 0,
                      "simulationSuccesses": 2, "completeAiSuccesses": 0, "matrixSha256": matrix_hash,
                      "traceSha256": trace_hash, "note": "Reviewed simulation uses supplied unchanged approvals. Missing-key AI failure is expected, not a model test.",
                      "requests": rows}
            (out / "http-smoke.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            print("PASS: reviewed local simulation, six source quotes, missing-key AI failure and deterministic retained Matrix/Trace; zero model calls.")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


if __name__ == "__main__":
    main()
