# Day4 backend integration handoff

## Routes and version behavior

| Route | Request | Success | Failure |
| --- | --- | --- | --- |
| `POST /api/simulate` | frozen `causora.contract.v1` request | reviewed or explicit development `causora.contract.v2` Matrix/Trace | v1 error envelope |
| `POST /api/boardroom` | `causora.contract.v1`, `simulationId`, `dataVersion`, `scenarioId` | v1 Boardroom data only for the exact retained **reviewed, decision-ready** v2 run | v1 error envelope |
| `GET /api/evidence/{id}` | path ID plus `X-Request-Id` | v1 `EvidenceRecord` from actual packaged PDF lookup | v1 error envelope |
| `GET /health` | none | actual simulation/evidence/Boardroom configuration states | 503 only when source dependencies are unavailable |

This intentional version combination preserves the frozen Day1/Day2 request/error and Boardroom DTOs while Day3 calculation success remains the approved v2 Matrix + Trace format.

## Run correlation

Each successful `/api/simulate` response is persisted under `CAUSORA_RUN_RECORD_DIR` (default `artifacts/runs/`) with the exact request, response, reviewed contract copy, execution context, request/response SHA-256, creation time, and expiry. Boardroom resolves **only** the requested `simulationId` and requires the exact matching `dataVersion`. Unknown, corrupted, expired, stale, development-only, and non-selected runs fail explicitly. The default TTL is one hour (`CAUSORA_RUN_RECORD_TTL_SECONDS`, 1–86400).

Editing any scenario, seed, threshold, cash ceiling, reviewed contract, policy, or release produces a different simulation identity/fingerprint. The frontend must use the new ID. It must not request Boardroom for a prior response after assumptions change.

## Boardroom gate order

1. Resolve retained run and match `simulationId` + `dataVersion` + requested scenario.
2. Reject unreviewed/development or `decisionReady:false` runs.
3. For `no_feasible_option`, return the contractual empty agent/Critic result without calling Wang.
4. Call only the configured Wang Day4 adapter inside the timeout.
5. Require all three role outputs, `criticStatus: complete`, a passing guardrail, matching selected option, safe metric placeholders, recomputed Critic mechanics, and actual quote-matched cited Evidence.
6. Return response headers `X-Causora-Provider-Mode`, `X-Causora-Critic-Status`, and echoed `X-Request-Id` with browser-readable CORS headers.

## Current external dependency

No `Wang_Hao_Day4.zip` was supplied in this workspace. Existing Wang Day3 code is development-only and cannot be promoted. Therefore normal Boardroom readiness remains `not_configured` until a genuine Day4 adapter is delivered and configured. This is an expected fail-closed state, not an incomplete HTTP route.
