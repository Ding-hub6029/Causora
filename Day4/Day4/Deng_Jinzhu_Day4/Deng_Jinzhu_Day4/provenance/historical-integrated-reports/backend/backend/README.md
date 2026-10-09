# Causora Day 4 integrated backend

This directory is the runnable Deng Jinzhu service layer for the Day 4 combined project. It preserves Day 1/2 v1 requests/errors and the Day 3 104-week Monte Carlo engine while adding a run-bound Evidence route and the formal Wang Day 4 Boardroom boundary.

## API contract

| Endpoint | Request | Outcome |
| --- | --- | --- |
| `GET /health` | none | v1 readiness/gate status |
| `POST /api/simulate` | `causora.contract.v1` | reviewed or explicit development v2 Matrix + Trace response |
| `GET /api/evidence/{EV-###}` | optional `X-Request-Id` | v1 Evidence record for the retained current run, reverified against packaged source PDF |
| `POST /api/boardroom` | v1 `{schemaVersion, simulationId, dataVersion, scenarioId}` | v1 Boardroom response only for a retained reviewed decision-ready run |

A v2 simulation success includes `data.simulation`, `data.deltas`, `data.selections`, `data.traces[scenarioId][optionId]`, and `data.executionContext`. A Matrix/Trace run is retained once. Evidence and AI never re-run Monte Carlo.

## Safe default

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn app.service:app --host 0.0.0.0 --port 8000
```

Without reviewed contract, policy, and Trace-release records, `POST /api/simulate` correctly returns a v1 `503` with exact missing reasons. It does not wrap an unapproved preview as reviewed success.

## Explicit development-only entry point

Use this only to let the frontend inspect actual deterministic Matrix, Trace, and Evidence behavior before human records exist:

```bash
python scripts/start_unreviewed_dev.py --host 0.0.0.0 --port 8000
# Windows CMD: scripts\start_unreviewed_dev.cmd --host 0.0.0.0 --port 8000
```

The launcher requires the exact `UNREVIEWED_DEV_ONLY` sentinel and clears approval configuration. It returns a real seeded v2 calculation marked:

- `executionContext.mode = unreviewed_development_only`.
- `executionContext.decisionReady = false`.
- `dataVersion` contains `UNREVIEWED_DEV_ONLY`.
- `X-Causora-Review-Status: unreviewed-development-only`. And
- `X-Causora-Execution-Mode: unreviewed-development-only`.

In this mode, Evidence source/locator inspection is available for the current retained run, but `/api/boardroom` returns `503 review_pending`. No provider import, AI request, Brief, approval, or Golden Run is possible.

## Evidence coordinates

Evidence comes from the actual source registry and physical document. `app.evidence_locator` extracts a PyMuPDF rectangle, converts it from PyMuPDF's top-left page coordinates to PDF user-space bottom-left points, then returns it in the existing v1 `locatorBbox` field. Ding's PDF.js viewer applies viewport rotation/zoom. See `EVIDENCE_COORDINATE_CONVENTION.md`.

## Formal reviewed + AI route

Normal reviewed success requires all three external records described in `CONFIGURATION_AND_VERIFIERS.md`:

1. Wang's verified reviewed contract bundle.
2. a three-owner approved policy record. And
3. a three-owner Trace-v2 release record binding current artifacts.

A formal Boardroom call additionally requires Wang's provider configuration. `CAUSORA_AI_PROVIDER=openrouter` is inert without a private `OPENROUTER_API_KEY`, preflight, a persistent budget journal, and explicit `YES` authorization flags. The service does not fall back to Manus/OpenAI credentials or a test provider.

## CORS and cross-machine use

Set `CAUSORA_CORS_ORIGINS` to a comma-separated exact allowlist. Default: `http://localhost:3000,http://127.0.0.1:3000`. For a frontend on another computer, use the backend computer's address and add the exact frontend origin. Do not point a remote browser at its own `localhost` and do not use `*`.

## Verification

Run `pytest -q` from this directory. `scripts/benchmark_monte_carlo.py` produces the current N=1,000/N=10,000 engine timing records without changing the engine. It is Windows-compatible: when Python's POSIX-only `resource` module is unavailable, the output keeps `wallClockSeconds`, sets `peakRssMiB` to `null`, and records `peakRssStatus: "unavailable"` rather than failing. Current integration evidence and the final fresh-package result are linked from the project root README.
