# Validation report — latest supplied Day3 Monte Carlo integration

Recorded 2026-10-07 (UTC+08:00). Supersedes the previous deterministic revision archived under `prior_deterministic_revision/`.

## Observed results

| Check | Actual result | Boundary |
| --- | --- | --- |
| Wang default suite, latest backend root configured | **98 passed**; `latest_wang_tests.log` | Old v6 external-engine tests excluded explicitly; no human approval or final acceptance |
| Latest original Jinzhu backend suite | **63 passed; 37 subtests passed; one warning**; `latest_jinzhu_backend_tests.log` | Unit fixture approval is not an actual human signature |
| Actual HTTP MC service | Four newly sent v1 POSTs returned v2 success with **1,000 runs, nine cells, 936 sample-path weeks each** | Synthetic unreviewed data/policy, not real-world facts |
| Scenario analysis | All baseline/demand-drop/lead-stress scenarios for all four captures; **12 ALL_READY offline-selector analyses**, each with CFO/COO/Risk DEV_ONLY | Offline selector is not AI prose or recommendation |
| Changed demand | Fresh -25% / 19,500-unit request has new simulation ID and numerical results | Source dataVersion stays the same legitimately |
| Changed lead | Fresh multiplier 1.8 request has new simulation ID and numerical results | No source dataset version fabricated |
| Browser JSON number compatibility | Fresh valid request with integer numeric spelling accepted; numerically equivalent result | Raw canonical request spelling remains separately hashed |
| Actual model smoke | Three concurrent `gpt-5-mini` calls on actual base demand-drop MC; **ALL_READY** | Constrained selection, not final decision or complete business analysis |
| Default formal HTTP mode | Actual `/api/simulate` returned **503**; saved under `mc_examples/formal_pending` | Development launcher is a separate process/configuration |
| Native review compatibility | Actual new verifier exposed; pending draft mapping reproducible, renaming rejected by both wrapper and original verifier | No genuinely reviewed positive pair supplied/tested |
| Existing Ding v1 TS compatibility | Passed unchanged-reference type check; `latest_v1_contract_check.log` | Does not prove Ding's frontend now accepts v2 |
| Engine ownership | Supplied backend core/schema source pins unchanged | Runtime service trace artifacts are expected mutable outputs |
| Critic corpus | 12 development inputs, 30 blind held-out inputs and separate hash-bound labels preserved/tested | Draft labels; no official score, full Critic or Day4 stages |
| Human review | Original eleven decisions and native worksheet eleven rows remain pending; signer/reference/time empty | AI checks are not human sign-off |

Detailed actual matrix values and run identities: `MC_INTEGRATION_RUNS.md`. Actual model call: `MODEL_SMOKE_REVIEW.md`.

## Integration guards covered

V1 request and supplied v2 schema; dataset/seed/scenario/option identity; per-cell shared run/policy/contract identity; changed-input stale pairing; envelope/matrix/trace version; required development headers and request ID; exact executionContext/no fake review references; true probability numerator/denominator and service counts; P90 rank/denominator/cash inclusion and matrix value; Decimal component rounding and cost sums; nine D0 deltas; selection feasibility/risk/budget consistency without promoting it to a decision; contract primitive types/provenance; immutable capture hashes; strict per-role fields; concurrent-start barrier; one-role provider error, invalid response, timeout and cancellation isolation; outer cancellation propagation; pointer/value/identity re-read and payload mutation isolation; Critic split/label leakage and formal-score refusal.

The 104-week trace path is one realised trial. **This is not independent full-trial replay or P90 reconstruction**: aggregate identities/counters are checked against matrix values, while the trusted supplied unchanged service performs the actual Monte Carlo calculation. No full Day4 Numeric Guardrail is claimed.

## Reproduce

```bash
CAUSORA_DAY3_BACKEND=/absolute/path/to/latest/backend python -m pytest -q
python scripts/verify_latest_backend.py --backend-root /absolute/path/to/latest/backend
python scripts/check_contract_types.py
npm run test:contract
```

For new service calls, follow the dedicated backend launcher and `mc_cli fetch-analyse` examples in README. Without the latest backend directory the two actual-source native-review tests skip explicitly, rather than being called successful integration tests. This default suite does not import/use the old v6 external computation target.

## Deferred formal acceptance

1. Genuine human completion of all six evidence and five assumption items.
2. Genuine team approval of stochastic operating/financial assumptions and the three-owner v2 trace release.
3. Ding's actual frontend migration/three-way integrated UI and deployment. No frontend edits, website build or remote-team E2E is claimed.
4. Genuine native reviewed-pair positive verification and reviewed v2 production role acceptance after the missing dataset/evidence/release prerequisites exist. No native contract-only record is fabricated into DatasetSuccess.
5. Independent Critic label review/freeze; future complete Critic, Synthesizer, final Numeric Guardrail and final Boardroom acceptance.

**Status: latest real Monte Carlo development integration and owner tests completed; human review and formal team acceptance deferred.**

## Clean-extraction portability check

The candidate owner-only ZIP was extracted into a new directory and a **new virtual environment** installed only Wang's requirements. With the supplied latest backend root configured, the fresh default suite returned **98 passed in 13.58 seconds**. An explicit C locale/disabled Python UTF-8 coercion run also returned **98 passed in 14.15 seconds**. Logs are `fresh_mc_tests.log` and `fresh_mc_C_locale_tests.log`.

The extracted immutable changed-lead capture produced `ALL_READY` for lead-stress, package SHA-256 verification passed, unchanged Ding v1 TypeScript compilation passed, and latest backend source-pin verification passed. No old engine workspace was assembled or used. Final packaging adds only this report/log evidence and clearer legacy-document headings after the tested candidate; executable Python/test/config files remain byte-identical to that fresh-tested candidate.
