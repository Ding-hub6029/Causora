# Explicitly labelled v2 response examples

| File | Purpose | Status |
| --- | --- | --- |
| `simulate_response_v2_TEST_FIXTURE_ONLY.json` | Schema/consumer test from temporary file-backed review/policy/release records | **TEST_FIXTURE_ONLY**. Not evidence of a Wang review, production approval or Boardroom run |
| `simulate_response_v2_UNREVIEWED_DEV_ONLY.json` | Direct UI/API integration shape generated from packaged synthetic source inputs | **UNREVIEWED — DEVELOPMENT ONLY**. `decisionReady:false`. Never a recommendation, approval or Boardroom input |

Both use the v1 request in `simulate_request_v1_TEST_FIXTURE_ONLY.json` and have `schemaVersion: causora.contract.v2`. Consumers must read `data.executionContext`, not only the outer schemaVersion.
