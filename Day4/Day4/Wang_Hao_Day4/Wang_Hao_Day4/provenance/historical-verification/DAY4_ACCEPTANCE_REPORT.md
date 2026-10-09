# Causora Day 4 Acceptance Report — Ding Xiangfeng

Date: 2026-10-08  
Revision: focused follow-up to the prior Day 4 delivery. The original Desktop ZIP was not modified.  
Baseline: the integrated Day 3 source copy.  
Owner scope: Ding-owned frontend and integration work only.

## Executive result

The five findings from the independent review of Ding's Day 4 frontend have been fixed and independently re-tested in the source copy:

1. The production static server now returns a JavaScript MIME for the PDF.js `.mjs` module worker. Chromium opened `EV-014`, rendered page 4, and highlighted the exact quote against the production static preview.
2. Boardroom `AgentOutput.body` now resolves supported `{{token}}` placeholders from the selected option in the matching validated Simulation/scenario. Unknown, malformed, or undeclared tokens are rejected.
3. `quoteMatched === true` is required both when creating and reloading a Verified Golden cache. Unmatched Evidence remains viewable in the Evidence flow.
4. The exact Boardroom response-header and browser CORS requirements are stated in the API contract and team handoff.
5. `frontend/MANIFEST.sha256` has been regenerated. The integrated root manifest is regenerated after the final package contents are staged.

**Ding-owned frontend finding status: PASS after these fixes.** This is not a claim that team G4 has passed: the integrated service still does not provide the live Boardroom or Evidence endpoints, and the v2 release/policy records remain **PENDING**. Work not yet supplied by other owners is not counted as a Ding frontend defect. No review, approval, or release gate was bypassed or changed.

## Acceptance matrix

| Area | Status | Evidence / boundary |
|---|---|---|
| Day 1/2 baseline and shared DTOs | **PASS** | Existing request/response contracts and upstream data are unchanged by this follow-up. |
| P1 production PDF.js worker MIME | **PASS** | `serve-static.mjs` serves `.mjs` as `text/javascript. Charset=utf-8`. Production HTTP smoke verifies the worker. Chromium production-preview acceptance reports worker HTTP 200, rendered PDF page 4, exact quote highlight, and zero browser runtime errors. |
| P2 Boardroom metric-template rendering | **PASS — frontend logic** | `{{delta_tco}}`, `{{stockout_probability}}`, and `{{cash_outflow_p90}}` are rendered from the current selected Simulation cell/delta. Contract tests verify declared tokens render and unknown/unbound tokens fail closed. No live Boardroom service is claimed or fabricated. |
| P2 Verified Golden evidence threshold | **PASS — cache creation and reload** | `quoteMatched: false, matchScore: 0` remains structurally viewable but is rejected from cache write and cache reload, including a record with a recomputed digest. |
| P2 Boardroom headers/CORS handoff | **PASS — documentation** | `API_CONTRACT.md` and `DAY4_TEAM_HANDOFF.md` specify provider/Critic response values, `X-Request-Id`, `Access-Control-Expose-Headers`, allowed origin/methods/request headers. |
| P2 frontend file manifest | **PASS** | `frontend/MANIFEST.sha256` is regenerated after frontend edits. `INTEGRATED_MANIFEST.sha256` covers the final package source, docs, logs, and evidence, excluding itself and generated/dependency caches. |
| Automated frontend gates | **PASS** | `npm run check`: TypeScript, ESLint, **49 tests passed**, static production build, and production static-server smoke **1/1 passed**. |
| Production-preview browser PDF acceptance | **PASS** | `verification/day4_production_pdf_acceptance.py`. Actual local static preview, actual click on “Open source quote”, actual module-worker request and canvas render. Screenshot and JSON log included. |
| Existing live Simulation/failure/health shell | **PASS — prior integrated acceptance retained** | The prior Day 4 Chromium report/log and real development `/health` + `/api/simulate` evidence remain included. This focused follow-up did not alter that API lifecycle. |
| Live Boardroom/Evidence endpoints and full E2E | **PENDING team services** | No live `/api/boardroom` or `/api/evidence/{id}` endpoint is present in the integrated backend. This boundary is not scored as one of Ding's five frontend defects. |
| Human review, team policy, v2 trace release, G4 | **PENDING** | No pending record was edited and no approval was inferred. A simulation-only or saved-example run is not a real reviewed Golden E2E. |

## Final automated checks

- `cd frontend && npm run check` — TypeScript, ESLint (`--max-warnings=0`), **49 tests passed / 0 failed / 0 skipped**, Next.js 15.5.27 static production build, and static-server smoke **1/1 passed**. The static test requests `/pdf.worker.min.mjs` and asserts a JavaScript MIME.
- Build output: `/` exported. 102 kB route / 205 kB first-load JavaScript.
- Production browser check: start the static export on `127.0.0.1:4173`, then run `verification/day4_production_pdf_acceptance.py`. Result: worker HTTP 200 with `text/javascript. Charset=utf-8`, PDF canvas rendered, exact quote highlighted, no browser runtime errors. Evidence is in `verification/logs/day4_production_pdf_acceptance.log` and `verification/evidence/day4-production-evidence-pdf-1440x900.png`.
- The earlier full responsive/live-simulation acceptance is preserved in `verification/logs/day4_browser_acceptance_final.log` and `verification/evidence/`. The focused follow-up adds a fresh production-preview browser run. No live Boardroom result was fabricated to exercise a gated view.
- Backend and Wang suites are retained as historical integration evidence and were not rerun for this Ding-only follow-up. They are outside the five findings and are not treated as Ding defects.
- Dependency versions were not changed by this follow-up. The previously recorded production audit had zero production vulnerabilities. The documented dev-toolchain findings remain in `DEPENDENCY_AUDIT.md`.

## Reproduction and delivery contents

1. Extract `Ding_Xiangfeng_Day4.zip` into a new directory. The original ZIP remains untouched.
2. Verify `INTEGRATED_MANIFEST.sha256` from the extracted package root.
3. Follow `README.md` and `frontend/README.md`. Node.js 22 and `npm ci` are required. Dependency/build caches are excluded.
4. From `frontend/`, run `npm run check`.
5. After the production build, start `HOST=127.0.0.1 PORT=4173 npm start` in `frontend/`. From the package root run `CAUSORA_PRODUCTION_PREVIEW_URL=http://127.0.0.1:4173 python3 verification/day4_production_pdf_acceptance.py`.
6. For the earlier live Simulation acceptance, follow the explicit unreviewed-development setup in the README. Do not add approval variables or modify pending records.
