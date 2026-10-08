# G4 Acceptance Status — Integrated Day 4

**Current status: PENDING.** This is a precise technical status matrix, not a team sign-off.

| G4 requirement / team expectation | Current evidence | Status | Owner / remaining condition |
| --- | --- | --- | --- |
| Ding public frontend preserves v1/v2 contracts and page flow | Frontend typecheck, lint, 49 automated tests, production build | PASS (technical) | Ding baseline preserved. |
| Actual Matrix + Formula Trace from same simulation | Dev-only browser and HTTP capture show 9 cells, 9 traces, identity correlation | PASS (development integration) | Deng; not reviewed decision output. |
| Trace math/provenance/sample paths remain visible | Formula Trace browser inspection showed five components, raw/display audit, provenance, and 104-week actual trial path | PASS (development integration) | Deng; policy confirmation still pending. |
| Evidence source and PDF locator are real | EV-024 current-run API record, page 4, converted bbox, browser highlight screenshot | PASS (development integration) | Deng; human/legal confirmation is not implied. |
| Coordinates match PDF.js coordinate system | `EVIDENCE_COORDINATE_CONVENTION.md`, unit/integration tests, browser highlight | PASS (technical) | Deng. |
| AI module is current Wang implementation | Latest `agent_day4` imported; repaired default suite `294 passed` against the current integrated backend | PASS (offline integration) | Wang. |
| Unified provider deadline, cancel safety, budget journal | Imported pipeline/provider implementation and offline tests | PASS (code/offline) | Wang; real formal call still needs separate authorization. |
| AI called only from successful exact simulation | Retained run registry + formal Boardroom resolver source/tests | PASS (technical) | Deng/Wang. |
| AI failure/timeout preserves Matrix and Trace | Browser copy and backend/client tests keep simulation; no rerun on downstream failure | PASS (technical) | Deng/Ding. |
| Development data cannot generate Boardroom/Brief/approval | Browser Boardroom and Brief displayed `REVIEW GATE CLOSED` / `NOT DECISION-READY`; HTTP Boardroom returned `503 review_pending` | PASS (safety gate) | All owners. |
| Reviewed contract fields drive real calculation | Code path and fixture tests exist | CONDITIONAL | Wang's actual reviewed bundle must be provided and verified. |
| Model policy, calculation assumptions, Trace-v2 release | Gate templates and verifiers exist | PENDING | All three owners must approve current hashes/configuration. |
| Formal OpenRouter Boardroom run | No new key/authorization was supplied; no paid call made | NOT RUN | Authorized owner must provide private key and explicit paid-call authorization. |
| Formal human decision / Golden Run | Correctly blocked | PENDING | Requires reviewed simulation + validated matching Boardroom + human decision. |
| Team G4 signature | None fabricated | PENDING | Ding, Deng, Wang must review current package results and sign externally. |

## Required acceptance sequence

1. Verify the package manifest and run fresh local tests.
2. Install and validate Wang's genuine reviewed contract bundle; validate a contract-field change against the engine.
3. Record the three-owner policy confirmation and Trace-v2 release record against this package's current artifact hashes.
4. Start normal reviewed service mode; verify health and the reviewed v2 Matrix/Trace path.
5. Only after explicit paid authorization, configure a private OpenRouter key and persistent budget journal; run read-only preflight then one bounded formal Boardroom request.
6. Have Ding complete reviewed browser acceptance: simulation, matrix, trace, service Evidence, Boardroom, Critic, Brief, and disabled/enabled decision transitions.
7. Record the human decision separately; do not convert the development run into a Golden record.
8. Obtain actual three-owner G4 acceptance.

## Non-acceptance facts

- The browser demonstration is explicitly `UNREVIEWED — DEVELOPMENT ONLY`.
- No OpenRouter credential, top-up, payment, or provider invocation was made in this work.
- A quote match/highlight is source-location evidence, not legal or human approval.
- Historic reports in `provenance/` remain preserved but do not substitute for the steps above.
