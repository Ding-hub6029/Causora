# Causora Day 3 backend — local runbook

## Directory and dependencies

After unzipping, enter the extracted backend root (the folder containing `app/`, `simulation_day3/` and `requirements.txt`):

```bash
cd Causora-Day3-Backend-Final
python3 -m venv .venv
source .venv/bin/activate              # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Tested package versions are recorded in `TEST_REPORT_FINAL.md`. Runtime uses Python 3.11+. Package test used Python 3.12.

## Start service

```bash
export CAUSORA_CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
uvicorn app.service:app --host 0.0.0.0 --port 8000
```

- Dataset ID: `ds-001`
- Health: `GET http://127.0.0.1:8000/health`
- Simulation: `POST http://127.0.0.1:8000/api/simulate`
- Request schema: `causora.contract.v1`
- Success schema after all gates: `causora.contract.v2`

For a frontend on the **same** computer, use `http://127.0.0.1:8000`. For another computer, do **not** configure the other computer to use its own `localhost`. Use the server computer's reachable LAN hostname/IP and include that exact frontend origin in `CAUSORA_CORS_ORIGINS`, for example `http://192.168.1.20:3000`.

## Current default behavior

With no external review/policy/release configuration, this is correct:

```bash
curl -i http://127.0.0.1:8000/health
curl -i -X POST http://127.0.0.1:8000/api/simulate \
  -H 'Content-Type: application/json' \
  --data @examples/simulate_request_v1.json
```

The simulation call returns HTTP 503 with a **v1 error envelope**, `error.details.reason`, and `error.details.missingReasons`. It does not return a mock or an unreviewed preview.

## Direct unreviewed development integration

For frontend/API integration before Wang's review and the three-owner records exist, use the dedicated launcher rather than changing the normal startup command:

```bash
# macOS/Linux
python scripts/start_unreviewed_dev.py --port 8000

# Windows CMD
scripts\start_unreviewed_dev.cmd --port 8000

# Windows PowerShell
python .\scripts\start_unreviewed_dev.py --port 8000
```

This launcher is the only shortcut: it requires the exact literal `UNREVIEWED_DEV_ONLY`, clears any supplied review/policy/release variables and isolates audit files under `artifacts/traces/unreviewed-development/`. It returns v2 HTTP 200 for a real seeded packaged-synthetic calculation, but **must never be treated as a decision**:

- `data.executionContext.mode = unreviewed_development_only`.
- `data.executionContext.decisionReady = false`.
- `data.simulation.dataVersion` contains `UNREVIEWED_DEV_ONLY`.
- all contract/policy trace provenance is `unreviewed_development_*`.
- response headers state `X-Causora-Review-Status: unreviewed-development-only` and `X-Causora-Execution-Mode: unreviewed-development-only`.

See `DEV_UNREVIEWED_INTEGRATION.md` for the full client handling requirement. Use `WINDOWS_ENCODING_AND_REPRODUCTION.md` for byte-identical data reproduction on Windows.

## Enable reviewed success only after owner inputs exist

1. Wang provides the reviewed bundle described in `CONFIGURATION_AND_VERIFIERS.md`.
2. All three owners record the approved policy and all required calculation topics.
3. All three owners record the released hashes for backend schema, Python model, common contract, TypeScript DTO and frontend validator.
4. Export the environment variables in `.env.example` (or source a local shell file. Never commit approvals/secrets as a generic example).
5. Restart Uvicorn and confirm `/health` shows `simulation: ready` and no missing reasons.
6. Send the same v1 request. A 200 response is v2 and contains the nine Matrix-bound Formula Traces.

## Audit artifact

Set `CAUSORA_TRACE_ARTIFACT_DIR` to an application-writable directory. Each verified 200 creates `<simulationId>.json` with response, review record, contract source, policy configuration/references, release record and engine/input hashes. Do not use this directory as a substitute for the owners' source records.
