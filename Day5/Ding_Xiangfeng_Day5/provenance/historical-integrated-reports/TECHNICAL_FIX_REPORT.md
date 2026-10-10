# Day 4 Technical Fix Report — Final Two Repairs

**Date:** 2026-10-08  
**Scope:** two post-integration reliability fixes only. No simulation formula, frontend public DTO, approval record, provider credential, paid provider call, or human review was changed.

## Fix 1 — Wang default pytest coverage

### Issue

`agents/wanghao-day3/pytest.ini` previously omitted the top-level `tests` directory. This meant a plain `pytest` command did not execute the current Day 4 provider, deadline, guardrail, budget, and source-evidence regressions stored there. The empty-but-reserved `tests_day4` integration entry point was not part of the documented default path either.

### Correction

The default `testpaths` is now:

```ini
tests tests_day4 agent_day3/tests agent_day3/evals/test_corpus.py evidence_review/tests
```

The four explicitly excluded historical v6 development-engine tests remain excluded. No current Day 4 test is excluded by this correction.

### Verification

From `agents/wanghao-day3/`:

```bash
CAUSORA_DAY3_BACKEND=/absolute/path/to/Deng_Jinzhu_Day4/backend/backend python -m pytest -q
```

Actual result: **294 passed in 71.72s**, zero skipped. The captured log is `verification/final-repair/wang_default_pytest_with_backend.log`.

Without `CAUSORA_DAY3_BACKEND`, three legacy source-file-integration checks correctly skip because they require an explicit original backend path; that behavior is documented in `wang_default_pytest_skip_reasons.log` and is not a Day 4 coverage omission.

## Fix 2 — Windows-compatible Monte Carlo performance telemetry

### Issue

`backend/backend/scripts/benchmark_monte_carlo.py` imported Python's POSIX-only `resource` module at module import time. Windows therefore failed before the elapsed-time benchmark could run.

### Correction

The script now treats `resource` as optional. It always measures `wallClockSeconds`. When the module or `getrusage` is unavailable, it writes:

```json
{
  "peakRssMiB": null,
  "peakRssStatus": "unavailable",
  "peakRssSource": "resource module is unavailable on this platform"
}
```

No memory value is invented. On Linux/macOS with supported `getrusage`, the existing RSS behavior remains and the report carries `peakRssStatus: "available"` plus its source.

### Verification

- Regression test simulating absent `resource`: **2 passed** (`backend/backend/tests/test_benchmark_portability.py`).
- Actual N=1,000 benchmark after the fix: **0.303001s**, with Linux RSS telemetry `65.195 MiB`, source `resource.getrusage`.
- Evidence: `verification/final-repair/benchmark_portability_pytest.log`, `benchmark_n1000_after_windows_fix.log`, and `performance_n1000_after_windows_fix.json`.

## Remaining acceptance boundary

These repairs make the technical package suitable for handoff. They do not change the separate requirements for actual reviewed inputs, three-owner policy/Trace release, an explicitly authorized private OpenRouter call, reviewed browser end-to-end validation, or formal G4 sign-off.
