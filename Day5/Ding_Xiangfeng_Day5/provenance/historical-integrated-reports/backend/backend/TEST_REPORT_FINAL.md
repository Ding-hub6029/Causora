# Causora Day 3 final backend — test report

**Executed:** 2026-10-07, Sandbox Linux  
**Dataset ID:** `ds-001`  
**Nominal HTTP port:** `8000` (smoke-test ports `8030` / `8031`)  
**Production status:** no real Wang bundle/policy/release record supplied; default service correctly stays v1 503.

## Final verification results

| Verification | Actual method | Result |
| --- | --- | --- |
| Source-tree complete regression | `pytest -q` after development-mode and portable-write additions | **PASS — 63 passed, 37 subtests** in 8.28s |
| Fresh archive / fresh virtualenv regression | zip → new directory → `python3 -m venv` → `pip install -r requirements.txt` → `pytest -q` | **PASS — 63 passed, 37 subtests** in 7.56s |
| JSON Schema integrity | `Draft202012Validator.check_schema` | **PASS** |
| Fixture-only v2 response / Schema | validates `simulate_response_v2_TEST_FIXTURE_ONLY.json` against final JSON Schema | **PASS** |
| Default health | live `GET /health` | **PASS — HTTP 200**, `simulation: review_pending` |
| Default v1 request gate | live `POST /api/simulate` | **PASS — HTTP 503**, `human_review_pending`, full missing-reason list |
| CORS request / preflight | `Origin: http://localhost:3000` | **PASS —** allow origin, POST/OPTIONS and headers present |
| Reviewed three-gate test path | file-backed **TEST_FIXTURE_ONLY** review/policy/release records plus real seeded engine | **PASS — HTTP 200 v2**, 9 Trace cells and audit artifact |
| Reviewed contract field change | fixture changes reviewed `terminationFeeUsd` and `dataVersion` | **PASS —** matrix fee and simulation ID change |
| Demand change | v1 request modifies scenario shocks/derived demand | **PASS —** actual rerun, changed matrix and simulation ID |
| Trace reconciliation | per-cost component, parameter reference, stockout/service/P90 and 104-week path tests | **PASS** |
| Tamper detection | mutate one trace component after output | **PASS —** Pydantic rejects response |
| Zero-revenue / no-feasible case | zero-demand scenario with zero budget | **PASS —** invalid gross-margin internal status and `no_feasible_option` selections |
| Engine/data reproduction | `scripts/reproduce_deng_day3_data.py --expected-manifest ...` | **PASS —** previewId plus all 3 JSON SHA-256 values match |
| Exact opt-in guard | `CAUSORA_DEV_UNREVIEWED_MODE=true` vs exact `UNREVIEWED_DEV_ONLY` | **PASS —** `true` remains 503; only exact literal enters development mode |
| Development v2 HTTP entry | `scripts/start_unreviewed_dev.py` + real seeded engine, port 8030 | **PASS — HTTP 200 v2**, 9 traces, CORS and Pydantic validation |
| Development labels | HTTP headers, response `executionContext`, trace run identity/provenance | **PASS —** unreviewed status, no review record, `decisionReady:false` |
| Default route after dev addition | normal Uvicorn startup, port 8031 | **PASS — HTTP 503 v1**, `human_review_pending`; default did not become permissive |
| Windows-safe JSON write | byte checks plus path containing spaces | **PASS —** UTF-8 without BOM, LF-only files and all 3 delivered hashes match |

The only observed warning is FastAPI/Starlette's upstream `TestClient` deprecation warning for the installed HTTPX compatibility path; it does not affect test results.

## Fresh-install package versions

| Component | Actual version |
| --- | --- |
| Python | 3.12.3 |
| FastAPI | 0.142.2 |
| NumPy | 2.5.3 |
| Pydantic | 2.13.5 |
| Uvicorn | 0.54.0 |
| HTTPX | 0.28.1 |
| jsonschema | 4.26.0 |

## Live HTTP captures

The normal startup captures in `examples/http-default-gated-final/` show the default `127.0.0.1:8031` service remains review-gated: HTTP 503, `human_review_pending` and `X-Causora-Execution-Mode: review-gated`.

The direct development launcher captures in `examples/http-dev-unreviewed/` show the explicitly named `127.0.0.1:8030` development-only service: HTTP 200, v2 Matrix + 9 Traces, CORS headers and:

- `X-Causora-Review-Status: unreviewed-development-only`;
- `X-Causora-Execution-Mode: unreviewed-development-only`;
- `data.executionContext.decisionReady: false`;
- data version containing `UNREVIEWED_DEV_ONLY`;
- no review record in any trace run identity.

These development captures are not Wang-reviewed, policy-approved, contract-released or Boardroom evidence. They exist solely to allow UI/API integration before the real owner records are available.
