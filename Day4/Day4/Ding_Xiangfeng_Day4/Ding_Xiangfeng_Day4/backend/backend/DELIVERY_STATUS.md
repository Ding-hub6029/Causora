# Historical component document

This incoming document is preserved as history and is superseded by the root README.md and DAY4_FINAL_ACCEPTANCE.md. Its original bytes are retained under provenance/historical-integrated-reports/.

---

# Delivery status — Day 3 reviewed Matrix + Trace backend

| Requirement | Delivered now | Activation state |
| --- | --- | --- |
| Runnable FastAPI service | `POST /api/simulate`, `GET /health`, port 8000, CORS allowlist | Running locally after install |
| v1 request and pending/error behavior | Strict `causora.contract.v1` request / v1 422–503 envelopes with `missingReasons` | Active by default |
| Real reviewed-input engine path | Verified contract fields/data version flow into `run_reviewed_monte_carlo`; no mock fallback | Implemented, release-gated |
| Formula Trace v2 | Final Pydantic model, JSON Schema, TS recommendation, nine-cell output and field/component/statistical audits | Implemented, release-gated |
| Wang-bundle verifier | Built-in file-backed adapter with contract/source/review-record separation and 11-item check | Requires Wang's real bundle |
| Policy verifier | Exact policy hash, three roles, all model-policy topics, configuration ID | Requires three real owner records |
| Contract-release verifier | Hashes backend/common/TypeScript/frontend artifacts + three roles | Requires shared artifacts and real release record |
| Test fixture v2 200 | Schema-valid, file-backed fixture records, real seeded engine | **TEST_FIXTURE_ONLY**, never approval evidence |
| Unreviewed data package reproduction | Engine source hashes and seed reproduce all three delivered data JSON hashes | Passed; remains UNAPPROVED |

## What remains intentionally absent

- No Wang-reviewed bundle, real three-owner policy record, or real v2 frontend-release record was invented in this delivery.
- Therefore a default local invocation correctly returns v1 503; it does **not** mean that the HTTP service or v2 code path is absent.
- No `GET trace`, Boardroom endpoint, recommendation/approval action or mock-success fallback is added.

Use `RUNBOOK.md` for exact enablement steps and `CONFIGURATION_AND_VERIFIERS.md` for the record formats.
