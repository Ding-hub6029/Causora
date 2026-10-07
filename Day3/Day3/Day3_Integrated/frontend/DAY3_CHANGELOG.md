# Day 3 Changelog — Xiangfeng Ding

**Scope:** Decision Matrix + Formula Trace UI; frontend integration with the shared `POST /api/simulate` v1 contract.

## Completed

1. Preserved the Day1/Day2 team baseline, including the fixed D0/D1/D2 option definitions, three scenario IDs, common DTOs, local evidence fixtures, Golden Run, static build path and prior regression tests.
2. Added a request builder that maps the existing scenario/options and explicit UI assumptions to the existing v1 request. It sends risk as a fraction, whole-USD budget, configured `datasetId`, and the inherited reproducibility seed; a changed demand shock updates only the selected scenario's demand units.
3. Added a same-origin/configurable-origin `/api/simulate` client with timeout and fail-closed response validation. It checks schema/data version, formula version, seed, 104 weeks, positive Monte Carlo runs, non-mock simulation ID, all requested scenario/option cells, accounting, purchase reconciliation, allocation, all D0-based deltas, and exact per-scenario constraint/violation results.
4. Delivered an interactive 3×3 Matrix with per-cell TCO, stockout probability and P90 cash; scenario-specific API selections; selected-option inspection; server Decision Delta; and an explicit run/error/draft state. A request failure retains and labels only the saved Day2 example.
5. Connected Formula Trace to the selected API cell and returned cost breakdown, with run ID, data version, formula version, seed, run count, horizon, request ID and receive time. The UI distinguishes server-provided aggregate holding/stockout components from detailed weekly drivers absent in v1.
6. Invalidated earlier live results when request-driving assumptions change. Gated Day2 Boardroom/Brief mock content after a live run so it cannot be mistaken for analysis of that run or enable an unrelated approval.
7. Added test-only contract fixtures and regressions for request mapping, validation/rejection, run metadata and unchanged Day1/Day2 fixtures.

## Deliberately unchanged

- `API_CONTRACT.md`, `lib/contracts.ts`, Day1 JSON/evidence, Golden snapshot, option allocations, scenario identities, upstream backend sources and other owners' Day3 scope.
- No AI, `/api/boardroom`, dataset-upload, provider credential, or approval-submission implementation was added to Ding's Day3 scope.

## Verification boundary

The front-end client and test suite can validate the shared v1 response shape. A real Monte Carlo HTTP E2E requires the separate backend owner to expose the reviewed success endpoint; the Day2 handoff explicitly says its deterministic preview is unreviewed and is not that endpoint. No test-only fixture is described as a real run.

## Stabilization fixes — 2026-10-07

1. Split `matrixScenarioId` (the scenario currently being inspected) from `scenarioId` (the scenario that owns request assumptions). Matrix row/cell browsing and option inspection no longer call the assumption-change handler, so they do not invalidate or clear a valid live run. Scenario Lab edits still invalidate the run when request-driving inputs change.
2. Routed Formula Trace and the proof header to the scenario currently being inspected in the Matrix; the API request context remains unchanged.
3. Added `displayMatrixTone`: for live responses, the winner highlight is derived from the already-validated per-scenario `selections`. A non-winner carrying a decorative `tone: "recommended"` hint cannot render as the winner; saved Day2 examples retain their original tone.
4. Added regression tests for matrix browsing/result retention, correct Formula Trace scenario routing, and conflicting server tone hints.
5. Regenerated `MANIFEST.sha256` from the final source-only file set; removed stale `out/` entries and updated hashes for every delivered file.
6. Re-ran the full source/production check: typecheck, zero-warning lint, 31 source tests, production build, and one production-preview test all passed.

**Remaining integration boundary:** a real `POST /api/simulate` E2E and team G3 review still require the reviewed Day3 backend endpoint. The shared v1 response exposes aggregate cost breakdowns, not weekly holding/stockout traces.
