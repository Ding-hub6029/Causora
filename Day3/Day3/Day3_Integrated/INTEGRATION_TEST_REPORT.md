# Causora Day 3 Three-Owner Integration Test Report (Historical)

Current status is in TECHNICAL_FIX_REPORT.md. Wang's supplied confirmation is now preserved in backend/backend/reviewed/wang-2026-10-07; old pending worksheets remain historical. Policy/release approval is still outstanding.

Executed 2026-10-07 on Ding frontend, Deng FastAPI/Monte Carlo and Wang agent/MC/evidence review. Automated and actual development HTTP integration passed. Formal G3/decision gate was not signed by this report.

| Module | Environment / check | Historical result |
| --- | --- | --- |
| Frontend | Node 22.16.0; npm run check: TS, ESLint, Node tests, Next build, production static server | Type/lint passed, 34/34 tests, static build, 1/1 server test. |
| Backend | Python 3.12; python -m pytest -q | 63 tests, 37 subtests passed; one Starlette/httpx deprecation warning. |
| Wang | Full pytest against integrated backend | 98/98 passed. |

Frontend regression covered shared v1, frozen Golden/fixtures, fail-closed API validation, view navigation retaining the live run, no formal development winner, formula/weekly sources.

Actual HTTP checks used frontend buildSimulateRequest/postSimulate against the running Deng service, not fabricated fixtures: health 200 labelled unreviewed_development_only/NOT DECISION-READY; shared v1 requests -> isolated unreviewed v2 responses. Both headers, identity, matrix/deltas, accounting, constraints and weekly traces validated. Results contained 1,000 seeded runs, 104 weeks, three scenarios x three options and nine 104-week sample paths. Same seed with demand-drop changed -15% to -25% produced new request/simulation identities and recomputed D0 TCO without mutating the baseline/request object. Wang fetch-analyse captured a fresh response and offline selector returned ALL_READY UNREVIEWED MC DEVELOPMENT ONLY with decisionReady=false, no approval/recommendation.

Boundary at report time: UNREVIEWED DEVELOPMENT ONLY results were not formal winners, Boardroom inputs or Brief approval grounds. This report covered automation and Node HTTP integration, not browser clicks/CORS or actual human review. Production static serving passed. Dependencies were not changed merely to remove the warning. Later browser verification and technical fixes are recorded separately in verification/ and TECHNICAL_FIX_REPORT.md.

The three source modules are integrated under frontend/, backend/, agents/wanghao-day3/ with shared Day 1/2 data preserved. This is a reproducible development delivery. Authorized real review, policy approval and common-version release remain necessary for formal G3 production sign-off.
