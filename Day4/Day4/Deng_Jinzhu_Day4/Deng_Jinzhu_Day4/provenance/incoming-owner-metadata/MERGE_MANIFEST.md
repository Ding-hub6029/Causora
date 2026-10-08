# Day 4 Three-Way Merge Manifest

## Inputs compared before integration

| Input | Role used in the merge | Not used as a blanket replacement |
| --- | --- | --- |
| `Ding_Xiangfeng_Day4(1).zip` | Frontend public API, page flow, public v1/v2 contract clients, styling/assets, source fixtures | Its old backend-state claims and historical reports were not treated as the final system state. |
| `Causora-Day4-DengJinzhu-Backend-Integrated.zip` | Monte Carlo engine, v2 Formula Trace response, gates, FastAPI service, run registration, Evidence/source checks | It did not overwrite Ding UI or Wang AI module. |
| `Wang_Hao_Day4.zip` | Latest `agent_day4` pipeline, OpenRouter adapter, validation repairs, timeout/budget logic, AI tests | It did not overwrite Deng service, Evidence locator, or Ding frontend. |

Historic owner material is retained under `provenance/`. Newer current reports in this package are authoritative for this package only.

## Shared-file resolution

| Shared area | Baseline retained | Applied integration result |
| --- | --- | --- |
| `frontend/` | Ding | Preserved public pages, interface names, validators, modal/UI behavior. `app/page.tsx` now routes a current live development run's existing Evidence buttons through the same v1 Evidence endpoint; local/saved evidence remains local when no run exists. This is necessary to inspect real service coordinates and does not alter DTOs or unlock Boardroom/Brief. |
| `backend/backend/app/service.py` | Deng | Preserved request validation, normal fail-closed reviewed path, explicit dev-only path, CORS, and run registration. Keeps Matrix/Trace after downstream failures. |
| `backend/backend/app/boardroom_adapter.py` | Deng + Wang | Deng's retained-run and physical-source boundary is kept. Wang's `agent_day4` is lazy imported only for formal reviewed requests. Request correlation, evidence enrichment, Numeric Guardrail response validation, current-run recheck, provider/critic headers, cancellation, and typed errors are connected. |
| `backend/backend/app/evidence_locator.py` | Deng | Added/kept coordinate bridge: PyMuPDF top-left extraction rectangle → PDF user-space bottom-left bbox. Ding's PDF.js component applies viewport scale/rotation. |
| `backend/backend/app/config.py`, `.env.example`, `RUNBOOK.md` | Deng | Extended documentation/configuration for CORS, review/policy/release inputs and Wang OpenRouter runtime. No key values added. |
| `agents/wanghao-day3/agent_day4/` | Wang | Imported newest pipeline, wires, input/evidence validation, provider factory, OpenRouter transport, and tests without overwriting service code. |
| `simulation_day3/` | Deng | Kept engine implementation. The N=1,000/N=10,000 benchmark script is additive and does not modify calculations. |
| `tests/` | All owners | Existing suites retained; Deng integration tests cover source registry, Evidence locator, stale/error/review gate behavior. Wang test fixtures are present for offline module regression only. |

## New or integration-specific files

| Path | Purpose |
| --- | --- |
| `backend/backend/app/evidence_locator.py` | Explicit coordinate-system conversion and quote-based bbox extraction. |
| `backend/backend/app/run_registry.py` | Persisted run metadata boundary used by the service integration. |
| `backend/backend/app/evidence_store.py` | Source/evidence lookup support. |
| `backend/backend/tests/test_day4_three_owner_integration.py` | Deng's combined run identity, evidence coordinate, and failure-mode tests. |
| `backend/backend/scripts/benchmark_monte_carlo.py` | Reproducible current-engine N=1,000/N=10,000 timing capture. |
| `verification/day4_integration/performance_*.json` | Current numerical performance outputs. |
| `verification/final/` | Final local HTTP, CORS, browser Evidence, and gate captures. |
| `INTEGRATION_REPORT.md` | Current ownership, boundaries, tests, and open conditions. |
| `G4_ACCEPTANCE_STATUS.md` | Current acceptance matrix; does not promote historical evidence. |
| `FINAL_VALIDATION_REPORT.md` | Fresh-extract validation record generated at packaging. |

## Deliberate non-merges

- No API key, provider journal, cached completion, reviewed contract, policy approval, release record, `node_modules`, virtual environment, or build cache is copied into the deliverable.
- No historical successful OpenRouter record is presented as an end-to-end test of this combined codebase.
- No development Matrix/Trace output is renamed reviewed, Golden, approved, or decision-ready.
- No pending approval file is edited to obtain a green path.

## Conflict-resolution rule for subsequent work

1. Treat Ding's frontend public endpoints and TypeScript validation as the browser contract owner.
2. Treat Deng's service and v2 Trace schema as the calculation/Evidence transport owner.
3. Treat Wang's `agent_day4` module as the AI/provider/guardrail owner.
4. Modify a shared boundary only with a matching backend test, frontend contract test, and a documented version migration.
5. Preserve all identity keys (`simulationId`, `dataVersion`, `scenarioId`, `optionId`, `requestId`) end-to-end; never replace one with a display label.
