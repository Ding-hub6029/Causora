# Final Validation Report — Deng Jinzhu Day 4 Integrated Package

**Final validation date:** 2026-10-08  
**Method:** source staged with generated caches excluded → ZIP → newly extracted directory → new Python virtual environment and new frontend dependency installation.  
**Scope:** source, contract, portability, and build regressions only. No provider credential, OpenRouter request, human review, policy release, or approval was created or simulated.

## Fresh-extract results after the final two repairs

| Area | Command in newly extracted copy | Actual result |
| --- | --- | --- |
| Deng backend | `python -m pytest -q` from `backend/backend` | **75 passed, 1 warning, 37 subtests passed in 10.27s** |
| Wang default AI/integration entry | `CAUSORA_DAY3_BACKEND=<fresh backend> python -m pytest -q` from `agents/wanghao-day3` | **294 passed in 75.75s; zero skipped** |
| Ding frontend | `npm ci && npm run check` from `frontend` | TypeScript and zero-warning ESLint passed; **49 tests passed**; Next.js production build passed; **1/1** production static-server test passed |
| Current engine N=1,000 | `benchmark_monte_carlo.py --runs 1000 --out ...` | **0.327409s** wall time in the fresh copy |
| Current engine N=10,000 | `benchmark_monte_carlo.py --runs 10000 --out ...` | **1.750359s** wall time in the fresh copy |
| Windows telemetry downgrade | `tests/test_benchmark_portability.py` and fresh script import | **PASS** — absent POSIX `resource` reports `peakRssMiB: null` and `peakRssStatus: unavailable`; timing remains available |
| Test-before-install archive scan | ZIP name/path scan | **PASS** — 685 entries; no `node_modules`, `.next`, `.venv`, `__pycache__`, `.pytest_cache`, `.pyc`, or `.pyo` entries |

The single backend warning is the existing upstream FastAPI/Starlette `TestClient` deprecation warning associated with the installed HTTPX compatibility path. It did not affect any assertion.

`npm ci` reported five high-severity advisories in its dependency tree. This package does not conceal the warning or run a breaking automatic audit fix. The existing dependency audit material is preserved, and the fresh frontend build/test suite completed successfully.

## Repair-specific verification

- `agents/wanghao-day3/pytest.ini` now includes `tests` and the preserved `tests_day4` integration entry point. The current Day 4 provider/deadline/guardrail/budget/source-evidence tests therefore execute from plain `pytest`.
- The performance script no longer imports `resource` unconditionally. Linux/macOS RSS remains available where supported; Windows completes the elapsed-time benchmark with explicitly unavailable memory telemetry.
- The repair report and targeted logs are in `TECHNICAL_FIX_REPORT.md` and `verification/final-repair/`.

## Current runtime evidence retained in the package

| Evidence | Result | Location |
| --- | --- | --- |
| Local development HTTP smoke | Real seeded development Matrix: 9 cells, 9 Trace cells, `decisionReady:false`; EV-024 page-4 bbox; CORS preflight; Boardroom intentionally `503 review_pending` | `verification/final/dev_http_smoke_summary.json` |
| Browser Evidence verification | EV-024 opened after a current development simulation; PDF viewer labelled server-provided bbox highlighted; browser console had no errors | `verification/final/browser_ev024_live_api_bbox.webp`, `browser_console_after_live_flow.log` |
| Final fresh backend result | 75 passed / 37 subtests | `verification/final-repair/fresh-finalfix/backend_pytest.log` |
| Final fresh Wang result | 294 passed / zero skipped | `verification/final-repair/fresh-finalfix/wang_default_pytest.log` |
| Final fresh frontend result | 49 browser-contract tests and production static test | `verification/final-repair/fresh-finalfix/frontend_check.log` |
| Final fresh benchmarks | Rechecked N=1,000 and N=10,000 exact current source | `verification/final-repair/fresh-finalfix/performance_n1000.json`, `performance_n10000.json` |
| Final fresh archive exclusion scan | No cache/dependency/runtime bytecode included before fresh install | `verification/final-repair/fresh-finalfix/archive_scan.json` |

## Deliberate acceptance limits

The successful rows above confirm technical integration and reproducibility. They do **not** mean:

- an actual reviewed contract bundle, model-policy record, or Trace-v2 release record has been approved;
- a development `UNREVIEWED_DEV_ONLY` simulation is decision-ready, reviewed, Golden, or publishable;
- an OpenRouter request was sent, paid for, or independently tested in this package; or
- three-owner team G4 acceptance was signed.

Refer to `G4_ACCEPTANCE_STATUS.md` for the exact prerequisites that remain pending.
