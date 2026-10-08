# Historical component document

This incoming document is preserved as history and is superseded by the root README.md and DAY4_FINAL_ACCEPTANCE.md. Its original bytes are retained under provenance/historical-integrated-reports/.

---

# Day 4 Test Report — Ding Frontend

Date: 2026-10-08  
Source under test: an independent working copy of the integrated Day 3 baseline with Ding-owned Day 4 follow-up fixes  
Runtime: Node.js 22.16, Next.js 15.5.27, Chromium/Playwright

## Result summary

| Area | Result | Evidence |
|---|---|---|
| TypeScript | Passed | `verification/logs/day4_frontend_feedbackfix_check.log` |
| ESLint | Passed with `--max-warnings=0` | Same log |
| Frontend regression + Day 4 tests | **49 passed, 0 failed, 0 skipped** | Same log; includes Boardroom token validation/rendering and Golden matched-Evidence gates |
| Next static production build | Passed; `/` exported, 102 kB route / 205 kB first-load JS | Same log |
| Production static-server smoke | **1 passed, 0 failed** | Same log; GET `/pdf.worker.min.mjs` returns JavaScript MIME |
| Production-preview Chromium Evidence click | **Passed** | `verification/logs/day4_production_pdf_acceptance.log` and `verification/evidence/day4-production-evidence-pdf-1440x900.png` |
| Previous four-viewport/live-simulation acceptance | Passed in the prior integrated Day 4 run; retained as historical evidence | `verification/logs/day4_browser_acceptance_final.log` and `verification/evidence/` |
| Earlier backend and Wang regression suites | Retained from prior integration run; not rerun in this Ding-only correction | `verification/logs/day4_backend_pytest.log`, `verification/logs/day4_wang_pytest.log` |
| Production dependency audit | Previously **0 production vulnerabilities**; dependency files unchanged in this correction | `verification/logs/day4_npm_audit_production.json` |
| Full npm audit | Previously documented **5 high findings in development tooling only** | `verification/DEPENDENCY_AUDIT.md` and audit JSON |

## New feedback-fix coverage

- **Production PDF:** the static-server unit smoke fetches the actual built `/pdf.worker.min.mjs` and asserts `text/javascript`. A separate Chromium test runs against the production static preview, clicks “Open source quote”, observes the worker response as HTTP 200 with `text/javascript; charset=utf-8`, renders `EV-014` page 4 and confirms an exact-source-text quote highlight. The browser reported zero page errors.
- **Boardroom tokens:** `Expected change {{delta_tco}}.` is accepted when the token is declared in `metrics[]`, resolves to the current selected Simulation's computed delta, and no longer displays braces. Undeclared and unsupported tokens are rejected. No real Boardroom endpoint was stubbed or called.
- **Verified Golden Evidence:** `quoteMatched: false, matchScore: 0` passes the structural Evidence validator for display, but is rejected when saving a Golden cache and when reloading a digest-valid cache. This preserves transparent Evidence viewing while preventing an unmatched citation from satisfying verification.
- **Team handoff:** the API contract and handoff now state the required provider/Critic response headers and browser CORS exposure/allow-list settings.
- **Manifest:** the frontend SHA-256 file is regenerated after the final source edits; the integrated package manifest is regenerated after staging.

## Production PDF browser result

`verification/day4_production_pdf_acceptance.py` ran against `http://127.0.0.1:4173` served by `npm start` from the static export (not `next dev`). Result:

- `GET /pdf.worker.min.mjs` — HTTP 200, `text/javascript; charset=utf-8`.
- Evidence `EV-014`, cited PDF page 4 — canvas rendered and exact source quote highlighted.
- No `.evidence-pdf-error` state and no uncaught browser runtime errors.
- Viewport: 1440 × 900; screenshot is included in `verification/evidence/`.

## Scope and boundary

The focused follow-up changes only Ding-owned frontend rendering, validation, static serving, tests, manifests, and interface documentation. Shared public DTOs and upstream Day 1/2/3 data are unchanged. No unreviewed result is promoted and no team approval is created. The integrated backend does not provide live Boardroom or Evidence endpoints, so no real Boardroom-to-Evidence-to-human-choice Golden E2E is claimed; team G4 remains **PENDING**. Work not supplied by other owners is not counted as a Ding frontend defect.

## Reproduction

From `frontend/`, run `npm ci` then `npm run check`. For the production browser check after the build, start `HOST=127.0.0.1 PORT=4173 npm start` from `frontend/`, then from the package root run:

```bash
CAUSORA_PRODUCTION_PREVIEW_URL=http://127.0.0.1:4173 python3 verification/day4_production_pdf_acceptance.py
```

The earlier live health/simulation browser acceptance requires the explicitly unreviewed backend and preview setup in the root README; it is a development integration run, not approval evidence.
