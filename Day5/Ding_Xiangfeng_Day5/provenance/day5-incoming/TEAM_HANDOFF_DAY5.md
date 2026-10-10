# Team Handoff — Causora Day 5

**Shared starting point:** `Ding_Xiangfeng_Day5.zip` (this package).  
**Team G5 / release status:** **PENDING**. The package does not claim that teammate work or human review has passed.

## Day 5 ownership

| Owner | Day 5 responsibility | Keep out of concurrent edits |
|---|---|---|
| Ding Xiangfeng | Frontend experience, local live/static verification, Golden/read-only provenance, frontend integration, final package assembly | Owns `frontend/` and the final integration/release packaging. Review shared changes before integrating. |
| Deng Jinzhu | Public frontend/backend deployment (delegated by Ding on 2026-10-08), benchmark/oracle work, and reproducible result/evaluation artifacts | Keep changes in the simulation/oracle/benchmark-owned module and tests; do not edit Ding's frontend core in parallel. |
| Wang Hao | Held-out Critic evaluation, prompt-injection tests, and negative-evidence evaluation | Keep changes in the AI/Critic/evaluation-owned module and tests; do not edit Ding's frontend core in parallel. |

Deng Jinzhu's and Wang Hao's Day 5 tasks are **not started** in this package and are not counted as defects in Ding's individual frontend scope. Both should begin from this exact Day5 ZIP, not from standalone teammate ZIPs or an older Day4 copy. Work in separate branches/copies; do not create concurrent competing edits to shared files.

## Frozen compatibility requirements

Any returned results or proposed integration must retain:

- Matrix + Trace v2 DTO/schema, option/scenario IDs, units, metrics, verifiers, error envelopes, and stable run/request identity fields.
- `simulationId`, `requestId`, `dataVersion`, scenario, option, seed, dataset, and approved policy bindings.
- All 15 approved assumptions and the distinction between the 1,200-unit synthetic opening-inventory bridge and the observed 1,840-unit CSV value.
- Existing approved model/provider configuration and rate/budget/security gates. No provider key may be added to this package or the browser.
- Human choice, review, policy, team release, and G5 gates must remain as supplied; do not promote any `PENDING` status.
- Evaluation results must distinguish synthetic/held-out fixtures from live or independently verified business evidence.

## Return-to-Ding integration contract

Each owner should return a separate, versioned result package to Ding containing:

1. A concise English change/evaluation report with exact scope, blockers, and actual status.
2. Machine-readable fixtures/results plus the exact schema/model/data version, seed, request/run IDs, and assumptions needed to reproduce them.
3. Automated test commands, raw logs, pass/fail counts, and a SHA-256 inventory for the returned package.
4. Evidence of failure/negative cases as well as successes; no invented user results or hidden changes to approval records.
5. Any shared-contract change proposed as a separate explicit diff and rationale; do not silently modify the frozen shared contract.

Ding will review each return separately, check contract and provenance compatibility, integrate sequentially, run the relevant test suites and clean-browser acceptance, then update the single shared ZIP and manifest. Until that integration and the required human review are done, team G5 remains **PENDING**.

## Current frontend status and blocker

The temporary frontend preview is documented in `DEPLOYMENT.md`. It is static-only and demonstrates the read-only Golden fallback; live Simulation, Evidence API lookup, and new Boardroom/Critic/Brief calls require a separately authorized public API backend. Ding's second genuine user test is ready to share in `USER_TEST_ROUND2.md` but is waiting for 2–3 real participants and a feedback-driven high-impact fix.

## Deployment ownership update

Public deployment is assigned to Deng Jinzhu. Follow DEPLOYMENT_HANDOFF_DENG.md. Ding supplies the corrected baseline; Deng returns public URLs, deployment configuration, and actual verification evidence. Deployment is pending until those checks pass. Human usability testing remains genuine participant work.

