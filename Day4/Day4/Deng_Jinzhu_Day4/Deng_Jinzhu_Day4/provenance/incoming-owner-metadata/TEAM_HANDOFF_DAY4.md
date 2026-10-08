# Day 4 Team Handoff — Current Integrated Package

**Canonical state:** read [README.md](README.md), [INTEGRATION_REPORT.md](INTEGRATION_REPORT.md), [G4_ACCEPTANCE_STATUS.md](G4_ACCEPTANCE_STATUS.md), and [FINAL_VALIDATION_REPORT.md](FINAL_VALIDATION_REPORT.md). The prior incoming Ding handoff is preserved unchanged at `provenance/ding/incoming_frontend_baseline/TEAM_HANDOFF_DAY4.incoming-2026-10-08.md`.

## Public service boundary

| Route | Contract | Current rule |
| --- | --- | --- |
| `POST /api/simulate` | v1 request / v2 Matrix + Trace success | Registers one exact run; v1 errors remain typed and fail closed. |
| `GET /api/evidence/{EV-###}` | v1 Evidence DTO | Re-verifies the physical source and returns PDF.js-compatible coordinates for the current retained run. |
| `POST /api/boardroom` | v1 simulation identity | Requires an exact retained reviewed decision-ready run; development runs return `review_pending`. |
| `GET /health` | v1 health DTO | Reports service/gate state; reachability is not approval. |

The browser must preserve `simulationId`, `dataVersion`, `scenarioId`, option identity, and request ID. A later request, changed scenario, or changed data version is stale and cannot be substituted.

## Day 4 owner responsibilities

| Owner | Current handoff |
| --- | --- |
| Ding | Continue Day 5 from `frontend/`. Preserve explicit saved-example/development/reviewed labels, validator behavior, and exact-origin configuration. |
| Deng | Maintain run identity, v2 Matrix/Trace output, source-backed Evidence, coordinate conversion, CORS, and service gates in `backend/backend/`. Do not use an AI failure to recompute or clear a Matrix. |
| Wang | Maintain `agents/wanghao-day3/agent_day4/` as the provider/critic/guardrail owner. Keep total deadline, cancellation, source-evidence checks, and persistent budget reservations. |

## Development-only integration

`python backend/backend/scripts/start_unreviewed_dev.py --port 8000` is available only for UI/Trace/Evidence locator tests. It returns a marked unreviewed v2 calculation and permits read-only current-run Evidence inspection. It does **not** permit Boardroom, Brief, human decision, or Golden caching.

## Formal enablement conditions

1. Wang supplies and verifies an actual reviewed contract bundle.
2. The three owners approve one model-policy configuration.
3. The three owners approve a Trace-v2 release record against current hashes.
4. An authorized owner configures OpenRouter in a private runtime with explicit paid-dispatch flags and persistent journal.
5. Ding runs reviewed browser acceptance for one exact run before any human decision.

No condition can be replaced by a saved example, a development response, a fixture, or a historical incoming report.
