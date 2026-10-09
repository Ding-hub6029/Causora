# Day 4 Three-Owner Integration Report

**Date:** 2026-10-08  
**Package:** `Deng_Jinzhu_Day4`  
**Scope:** Ding frontend baseline + Deng simulation/Evidence service + Wang Day 4 AI module.  
**Status:** technical integration complete. Formal G4 acceptance pending human and release conditions.

## 1. Integration decisions

### Kept from Ding

- The five-stage browser flow, public route names, CORS assumptions, v1 Boardroom/Evidence DTOs, v2 Matrix/Trace acceptance rules, saved-example protections, and PDF.js viewer remain the public baseline.
- The frontend still rejects unreviewed v2 output unless `NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE=UNREVIEWED_DEV_ONLY` is set.
- Boardroom, Critic, Synthesizer, Brief, human decision, and Golden cache are still blocked for `unreviewed-v2-dev`.

### Kept from Deng

- The existing Monte Carlo engine and Day 1/2 v1 data remain intact. No model meaning was changed for performance work.
- The FastAPI service retains v1 request/error plus v2 Matrix/Trace success behavior, exact run registration, source verification, deterministic Formula Traces, and review/policy/release gates.
- The previous PyMuPDF-to-PDF.js ambiguity is fixed by `app/evidence_locator.py`: it converts top-left PyMuPDF extraction rectangles to bottom-left PDF user-space points. The Ding PDF.js viewer then applies page rotation and viewport scaling itself.
- A current live development run can use the already-public `GET /api/evidence/{id}` route solely to inspect its source locator. This is a minimal callback selection change in `frontend/app/page.tsx`. It changes neither public DTO nor page flow. It does not open Boardroom/Brief or enable a decision.

### Kept from Wang

- The newest `agent_day4` pipeline, strict output validation, critic/synthesizer sequence, same-family fallback labels, source enrichment, Numeric Guardrail, OpenRouter transport, and Windows-safe persistent budget journal are imported under `agents/wanghao-day3/`.
- `app.boardroom_adapter` lazy-loads that module only after resolving a retained reviewed, decision-ready simulation. Development output fails `review_pending` before any provider import or call.
- The pipeline owns one monotonic request deadline. Each role call receives only the remaining budget. It does not get a new full timeout. Cancellation propagates, while the immutable Monte Carlo record remains retained and is never recomputed for an AI retry.

## 2. End-to-end call chain

1. Ding sends the existing `causora.contract.v1` request to `POST /api/simulate`.
2. Deng validates and runs the actual engine once. The v2 output has exact `simulationId`, `dataVersion`, `scenarioId`, `optionId`, request correlation, Matrix, Deltas, Selections, and nine Formula Traces.
3. The service verifies and retains that exact response with its actual packaged evidence registry and physical source directory. It does not run AI during simulation.
4. `GET /api/evidence/EV-024` re-verifies the source PDF quote and returns the corresponding converted page-4 locator. It is bound to the current run data version.
5. For a formal reviewed run only, `POST /api/boardroom` resolves the exact retained simulation identity, rechecks evidence/source bytes, calls Wang's configured provider pipeline within its total deadline, and validates the returned Critic/Numeric Guardrail result before returning a Brief.
6. AI timeout, cancellation, a malformed result, a missing citation, or an unavailable Critic leaves the retained Matrix and Trace unchanged. No fallback Matrix, recommendation, or approval is manufactured.

## 3. Evidence-coordinate verification

The packaged evidence document is `frontend/public/demo/supplier_a_agreement.pdf`. The server response for a current development simulation returned EV-024 as:

| Field | Actual result |
| --- | --- |
| Citation | `EV-024` — `min_purchase_share_A` |
| Page | `4` |
| Returned PDF user-space bbox | `[54.0, 550.711, 499.676, 565.825]` |
| Browser outcome | The PDF viewer showed **Server-provided PDF bounding box highlighted** over the exact 60% minimum-purchase quote. |
| Run mode | `unreviewed_development_only`, `decisionReady:false` |

The actual local HTTP capture is in `verification/final/dev_ev024.json`. The clean browser screenshot is `verification/final/browser_ev024_live_api_bbox.webp`. This is evidence-location verification only, not legal approval.

## 4. Timeout, cancellation, and provider protection

- `agent_day4.pipeline._Execution` starts one monotonic clock per Boardroom request. Role/critic/synthesizer calls receive the minimum of their stage setting and the remaining total time. Retry attempts use the remaining time rather than a fresh stage budget.
- Provider calls are wrapped with `asyncio.wait_for`. Request cancellation is re-raised through `boardroom_adapter` and does not delete the stored simulation.
- A timed-out or cancelled provider reservation remains conservatively recorded by the OpenRouter budget journal because a remote request may have reached the provider.
- The service returns a typed failure (`provider_timeout`, unavailable Critic, stale run, source mismatch, or validation failure) and leaves client-side Matrix/Trace state intact.
- The browser timeout is independent only for its HTTP wait. It never causes a re-run of Monte Carlo.

## 5. AI provider status and cost boundary

No usable `OPENROUTER_API_KEY` or paid-dispatch authorization was supplied for this integrated package. No credential was recovered from incoming material, no purchase was made, and no new paid model call was triggered.

Wang's imported code is configured for OpenRouter only when all of these are deliberately set in a private environment:

- `CAUSORA_AI_PROVIDER=openrouter`
- `OPENROUTER_API_KEY` (not shipped)
- `CAUSORA_OPENROUTER_PAID_AUTHORIZED=YES`
- `OPENROUTER_SCOPED_KEY_CONFIRMED=YES`
- `CAUSORA_OPENROUTER_BUDGET_JOURNAL=/private/writable/path.json`

It also performs read-only `/models` and `/key` preflight, limits a process to six calls and USD 1.00 maximum authorized spend, reserves budget before dispatch, and persists reservations under a cross-platform lock. Historic Wang reports are preserved as provenance only. They do not prove a new integrated end-to-end provider call.

## 6. Current performance verification

The current engine was run with the same request, seed `1042026`, 104-week horizon, and current packaged engine hashes. It produced nine cells and 936 trace-week records in both cases.

| Configuration | Wall clock | Peak RSS | Environment | Evidence |
| --- | ---: | ---: | --- | --- |
| N=1,000 | 0.287491 s | 66.645 MiB | Python 3.12.3, NumPy 2.5.3, Linux, 6 CPUs | `verification/day4_integration/performance_n1000.json` |
| N=10,000 | 1.349088 s | 118.348 MiB | Python 3.12.3, NumPy 2.5.3, Linux, 6 CPUs | `verification/day4_integration/performance_n10000.json` |

Both files explicitly state `UNREVIEWED_ENGINE_BENCHMARK_ONLY_NOT_A_PUBLIC_SIMULATION`. Performance validation did not change calculations and is not reviewed/Golden/Boardroom proof.

## 7. Tests already executed before final package re-validation

| Area | Result | Boundary |
| --- | --- | --- |
| Wang Day 4 AI module offline suite | Historical initial run: `195 passed`. Repaired default entry: `294 passed` with `CAUSORA_DAY3_BACKEND` set to this integrated backend | No new paid provider dispatch. |
| Ding frontend type/lint/tests/build | typecheck + lint + `49` tests + production build passed | Public UI contract validation. |
| Deng backend gated/trace regressions | prior integrated backend suite passed | Includes source-backed Evidence, tamper, gate, and Boardroom rejection cases. |
| Real local browser flow | passed | Development-only simulation → Matrix → Trace → EV-024 service locator → Boardroom/Brief gate. No console output. |
| Current HTTP smoke | passed | 9 Matrix cells, 9 traces, converted EV-024 bbox, CORS preflight, Boardroom `503 review_pending`. |

The final archive is re-tested after documentation and manifest creation. The current full result and the two post-review portability/pytest repairs are recorded in `FINAL_VALIDATION_REPORT.md` and `TECHNICAL_FIX_REPORT.md`.

## 8. Limits and required next steps

1. Wang must provide/operate the real reviewed contract bundle. No hand-entered approval field may substitute for it.
2. All three owners must approve the model-policy configuration and Trace-v2 release record with current artifact hashes.
3. An authorized owner must supply a private OpenRouter credential and explicitly authorize a formal paid call. A formal preflight/dispatch test must be recorded separately.
4. Ding must run the reviewed browser acceptance flow after the above inputs exist. The test must confirm a matching Boardroom response and Brief but must not relabel development output as Golden.
5. Team members must sign the G4 checklist after reviewing current—not historic—results.
