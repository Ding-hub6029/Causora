# Historical component document

This incoming document is preserved as history and is superseded by the root README.md and DAY4_FINAL_ACCEPTANCE.md. Its original bytes are retained under provenance/historical-integrated-reports/.

---

# Day 4 Changelog — Ding Xiangfeng

Date: 2026-10-08  
Release line: frontend `0.4.0`  
Baseline: integrated Day 3 package; Day 1/2 data and shared `causora.contract.v1` preserved.

## Delivered

- Added frontend-private Day 4 state types and strict clients for the existing v1 Boardroom and Evidence DTOs. Downstream state is bound to the current Simulation ID, `dataVersion`, scenario, simulation request ID, and response correlation ID. No shared v1/v2 DTO was silently changed.
- Added a live Boardroom/Decision Brief path that consumes only validated reviewed-v2 simulation data and a matching Boardroom response. Brief metrics and eligibility are derived from the server Simulation and validated `selections`; unknown metric references, stale identities, failed Critic/numeric guardrail state, and unreviewed dev responses remain blocked.
- Added run-bound Evidence lookup, source-file allowlisting, page/quote/locator validation, and a packaged PDF.js viewer. It highlights only a valid API bounding box or an exact source-text match on the cited page; it does not invent coordinates. Missing source, timeout, HTTP error, PDF load failure, and cancellation have visible retry/return handling.
- Preserved a validated Matrix and Formula Trace after later simulation/Boardroom/Evidence failures. Async requests can be cancelled; stale responses are ignored; an AI retry does not trigger a Monte Carlo rerun.
- Added a restricted Golden cache. Only a complete reviewed-v2 Simulation, matching validated Boardroom, cited validated Evidence, and browser-local human choice can be stored. Reopening rechecks the digest and validators and is read-only. Saved Day 1/2 examples and test fixtures cannot become a verified Golden.
- Added a page-load `GET /health` gate with a 2.5-second timeout, no-store/credential-free request, and manual recheck. A waking/unavailable backend shows explicit cold-start guidance; Live Run stays disabled until the service reports ready. A matching complete reviewed cache is the only `Verified Golden Run` fallback; without one, the UI offers the bundled Day 2 example with its “not verified E2E” label.
- Added fail-closed Brief/Gate UI, local-only human-decision wording, explicit saved-example versus live statuses, stage navigation scroll reset, keyboard modal behavior, and responsive PDF/matrix styling.
- Separated primary reviewed LIVE, simulation-only, same-family fallback, AI-review unavailable, and cached verified Golden status labels.
- Added Day 4 API/identity/locator/cache/health tests and Chromium acceptance coverage with four viewports, real `/health` + simulation requests, injected health/simulation/PDF failures, and fallback checks.
- Updated the Next.js 15 maintenance line to `15.5.27`, pinned the compatible PostCSS security override at `8.5.29`, and added pinned `pdfjs-dist` with its Apache-2.0 license.

## Independent QA follow-up — five Ding-owned findings closed

- **P1 production PDF worker MIME:** production static serving now maps `.mjs` to `text/javascript; charset=utf-8`. The static HTTP test checks the actual worker asset; a Chromium run against the production export clicked “Open source quote”, loaded the worker with HTTP 200, rendered `EV-014` PDF page 4, and highlighted the exact quote.
- **P2 Boardroom template values:** supported `{{delta_tco}}`, `{{stockout_probability}}`, and `{{cash_outflow_p90}}` tokens render from the selected option in the same validated Simulation/scenario. The API validator rejects malformed, unsupported, and undeclared tokens; output is plain text, not interpreted HTML.
- **P2 Verified Golden evidence:** cache create and reload now require `quoteMatched === true`. An unmatched record (including `matchScore: 0`) remains inspectable in the Evidence flow but cannot satisfy the Golden gate.
- **P2 API handoff:** `API_CONTRACT.md` and `DAY4_TEAM_HANDOFF.md` now specify `X-Causora-Provider-Mode`, `X-Causora-Critic-Status`, correlation header exposure, CORS allowed methods/headers, and exact-origin handling.
- **P2 frontend manifest:** `frontend/MANIFEST.sha256` is regenerated after all frontend edits; the integrated manifest is regenerated after final package staging.
- **Verification:** `npm run check` passes TypeScript, ESLint, 49 tests, production build, and 1/1 production static-server smoke. The targeted production PDF Chromium acceptance also passes. Current logs/screenshots are in `verification/logs/` and `verification/evidence/`.

## Unchanged / out of scope

- Deng's FastAPI and Monte Carlo engine, Wang's Critic/Synthesizer/numeric-guardrail/fallback policy, shared Day 1/2 inputs, and public shared contract DTOs were not replaced.
- No approval, policy, release, or pending record was edited to force a pass. The frontend does not create supplier actions, purchase orders, signed agreements, or external human approvals.
- No provider key, token, or other credential is bundled. No provider model call is used for this Day 4 frontend integration.

## Current acceptance boundary

The real `/health` and `/api/simulate` Monte Carlo paths were exercised earlier in explicitly marked unreviewed development mode. The integrated backend still has no `/api/boardroom` or `/api/evidence/{id}` route, and team policy/v2 release approvals remain pending. These other-owner/team dependencies are not counted as Ding's five frontend findings. The UI keeps those downstream paths unavailable; no complete reviewed E2E Golden can be bundled or claimed. Formal G4 remains **PENDING**.
