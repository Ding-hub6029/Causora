# Day 4 Test Report — Current Integrated Package

The incoming Ding-only test report is preserved at `provenance/ding/incoming_frontend_baseline/DAY4_TEST_REPORT.incoming-2026-10-08.md`. It predates the combined backend/AI service integration and must not be read as the current full-project result.

| Check | Result / file | Meaning |
| --- | --- | --- |
| Frontend static contract/build suite | typecheck + lint + 49 tests + production build passed | Public frontend contract/build remains valid. |
| Wang AI default suite after pytest repair | `294 passed` with current `CAUSORA_DAY3_BACKEND`. `tests` and `tests_day4` are now included by default | Current imported AI source validates offline. No new provider dispatch. |
| Monte Carlo N=1,000 | `0.287491s`, `66.645 MiB` | Current engine benchmark. Unreviewed only. |
| Monte Carlo N=10,000 | `1.349088s`, `118.348 MiB` | Current engine benchmark. Unreviewed only. |
| Current HTTP smoke | `verification/final/dev_http_smoke_summary.json` | 9 Matrix cells, 9 traces, EV-024 bbox, CORS, Boardroom gate. |
| Current browser acceptance | `verification/final/browser_ev024_live_api_bbox.webp` and console log | Development Matrix/Trace/Evidence flow. Boardroom/Brief remain blocked. |

The fresh-extract validation performed at packaging is recorded in [FINAL_VALIDATION_REPORT.md](FINAL_VALIDATION_REPORT.md). No line above constitutes reviewed approval, a Golden Run, or a paid OpenRouter end-to-end claim.
