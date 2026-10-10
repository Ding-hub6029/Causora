# Day 5 final technical verification

Date: 2026-10-08 (Asia/Shanghai). Performed by Codex with automated tests and real browser interactions. **This report is not a human participant test, business approval or fresh paid provider validation.**

## Passed checks

| Check | Actual result |
| --- | --- |
| Clean Python 3.12 environment and required dependency install | PASS; actual service launched with project .venv and no audit PYTHONPATH |
| Typecheck and lint | PASS |
| Frontend tests | 56 passed |
| Production server tests | 3 unique tests passed; repeated with inherited static flags enabled |
| Backend/simulation regressions | 76 passed and 37 subtests passed |
| AI/provider/guardrail regressions | 307 passed; fixture transport, no paid calls |
| Production exports | Live and static variants built successfully; mode markers match |
| Actual local HTTP | Ten consecutive reviewed simulations, each followed by explicit missing-key Boardroom failure; six evidence IDs quote-matched |
| Genuine frozen Golden | Valid digest, run binding and evidence; tampered record rejected |
| Actual static browser flow | Fresh visit, Golden, Matrix, stored Boardroom, evidence PDF page 4/highlight, Brief read-only and JSON download verified |
| Actual live browser flow | Simulation, Matrix and Formula Trace, followed by truthful AI unavailable preserving results |
| Responsive review | 390px narrow viewport: no document horizontal overflow; evidence buttons 12px, approximately 73px high after wrapping; desktop checked |
| Dependency audit | Production 0 reported; development-inclusive 5 high findings disclosed in SECURITY_AUDIT_DISPOSITION.md |

Total: **442 unique automated tests plus 37 subtests**. Repeated environment runs and ten HTTP attempts are listed separately, not added to that test count. Actual test logs and screenshots are in verification/day5-final/. The initial run with system temporary-directory access errors was corrected by using a workspace temporary directory. Three inherited AI tests used obsolete capture paths; these now read unchanged captures from their actual preserved provenance directory and the complete AI suite passes.

## Limits and handoff

No current public deployment is claimed; Deng Jinzhu owns it. New model generation was intentionally not billed or represented as successful without valid authorized credentials. Authentic Day 4 provider captures and Golden are historical evidence, not a new Day 5 success. Genuine round-two participant feedback, at least one feedback-driven change and retest are assigned to Deng's test organization and remain pending. Proactive readability changes are not fabricated participant feedback.

The backend regression emits one upstream Starlette/httpx deprecation warning; all tests pass. Five unpatched development dependency findings remain disclosed, with the configured expansion boundary regression-tested. This delivery is ready for local technical handoff, not an unconditional full team G5 sign-off.

## Reproduce

From frontend with Node 22/npm installed: npm ci; npm run check; node scripts/verify-golden-e2e.mjs.

From backend/backend using the installed project environment: python -m pytest tests simulation_day1/tests simulation_day2/tests simulation_day3/tests -q. From agents/wanghao-day3 using the same Python environment: python -m pytest -q. If the system temporary directory has restricted stale files, choose a new --basetemp path in your own workspace.

For the isolated keyless HTTP check, first start Live mode and set CAUSORA_VERIFY_URL to its URL if not port 3000; run python scripts/verify_day5_runtime.py. It deliberately expects missing-provider failure and must not be used with a paid configured service. Explicitly set CAUSORA_VERIFY_KEYLESS_SERVER_CONFIRMED=YES only after starting an isolated server without provider credentials. Default output is .runtime/day5-http-check.

Before editing/installing, run python scripts/verify_package.py. Checksum results are also supplied as a separate final-package sidecar report.
