> Technical fix status (2026-10-07): See the integrated package root TECHNICAL_FIX_REPORT.md. Original pending templates remain historical. Wang's supplied confirmation is preserved at backend/backend/reviewed/wang-2026-10-07. Model policy and release still require team confirmation.

# Causora Day 3 — reviewed Matrix + Trace backend

This is a runnable FastAPI backend for the Day 3 104-week Monte Carlo simulation. It keeps Day1/Day2 v1 mock, Golden and source materials unchanged while implementing a **fail-closed real-input success path**.

| Interface outcome | Request | Response |
| --- | --- | --- |
| malformed request | `causora.contract.v1` | v1 `422` error |
| review/policy/release missing or invalid | `causora.contract.v1` | v1 `503` error with exact missing reasons |
| explicit unreviewed development launcher | `causora.contract.v1` | v2 `200` with `executionContext.mode=unreviewed_development_only`, never decision-ready |
| all three records verified and engine succeeds | `causora.contract.v1` | v2 `200`: `simulation`, `deltas`, `selections`, `traces[scenarioId][optionId]` |

**Dataset ID:** `ds-001`  
**Service:** `POST /api/simulate`, `GET /health`  
**Default CORS:** `http://localhost:3000,http://127.0.0.1:3000`

## What is implemented

- Reads Wang's separately supplied reviewed contract bundle and uses the reviewed contract fields and data version in the engine. No mock contract relabeling.
- Requires an independently recorded three-owner model-policy confirmation with exact policy hash and all required modelling topics.
- Requires a three-owner v2 release record binding backend JSON Schema/Pydantic model, common contract, TypeScript DTO and frontend validator hashes.
- Generates nine Matrix-bound Formula Traces with five component formulas, resolvable parameters, field-level source evidence, a separate review-record reference, statistical bases and 104-week single-trial sample paths.
- Retains raw Monte Carlo means, displayed accounting values and their difference per component. It never claims they are always identical.
- Uses review, contract, policy configuration and release identities in `simulationId` and trace run identity.

## Start here

1. Read [RUNBOOK.md](RUNBOOK.md) for fresh installation, port `8000`, CORS, health check and cross-machine guidance.
2. Read [CONFIGURATION_AND_VERIFIERS.md](CONFIGURATION_AND_VERIFIERS.md) before supplying a reviewed bundle, policy or release record.
3. Confirm fields/version with [FINAL_FIELDS_AND_CONFIRMATION_SUMMARY.md](FINAL_FIELDS_AND_CONFIRMATION_SUMMARY.md) and the migration/Boardroom contract in [VERSION_MIGRATION_AND_BOARDROOM_HANDOFF.md](VERSION_MIGRATION_AND_BOARDROOM_HANDOFF.md).
4. Record the modelling choices in [MODEL_POLICY_CONFIRMATIONS.md](MODEL_POLICY_CONFIRMATIONS.md), then follow the templates under `config/templates/`.
5. For temporary UI/API testing before these owner records exist, read [DEV_UNREVIEWED_INTEGRATION.md](DEV_UNREVIEWED_INTEGRATION.md). This is an explicit, labelled development mode—not an approval shortcut.

## Default safe behavior

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.service:app --host 0.0.0.0 --port 8000
curl -i -X POST http://127.0.0.1:8000/api/simulate \
  -H 'Content-Type: application/json' \
  --data @examples/simulate_request_v1.json
```

Until external owner inputs are installed, the valid request returns a **v1 503** with `human_review_pending`, `simulation_policy_unapproved` and/or `trace_contract_unconfirmed` rather than a mock or unreviewed-preview success. This is expected.

## Direct development integration (no human records required)

To let Ding and Wang exercise a complete Matrix + Trace HTTP 200 before review records exist, run the **separate launcher**:

```bash
python scripts/start_unreviewed_dev.py --port 8000
# Windows CMD: scripts\start_unreviewed_dev.cmd --port 8000
```

It sets the exact opt-in value `CAUSORA_DEV_UNREVIEWED_MODE=UNREVIEWED_DEV_ONLY`, clears approval-related environment variables and returns an actual seeded calculation using packaged synthetic inputs. Every successful response/header/trace is labelled `UNREVIEWED — DEVELOPMENT ONLY`. `data.executionContext.decisionReady` is always `false`. See [DEV_UNREVIEWED_INTEGRATION.md](DEV_UNREVIEWED_INTEGRATION.md) and [WINDOWS_ENCODING_AND_REPRODUCTION.md](WINDOWS_ENCODING_AND_REPRODUCTION.md).

## Tests and package evidence

```bash
pytest -q
```

See [TEST_REPORT_FINAL.md](TEST_REPORT_FINAL.md) for the exact final test/install commands, package versions and results. Fixture-only v2 examples/tests demonstrate the code path but are explicitly not Wang-reviewed, production or Boardroom evidence.
