# Day 4 integrated backend runbook

## Prerequisites

- Python 3.11+ (the current benchmark used Python 3.12.3).
- Node.js 22 only for the separate frontend.
- No OpenRouter key is required for simulation, Trace, Evidence, or offline tests.

```bash
cd Deng_Jinzhu_Day4/backend/backend
python3 -m venv .venv
source .venv/bin/activate                    # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Development-only frontend integration

```bash
export CAUSORA_CORS_ORIGINS='http://localhost:3000,http://127.0.0.1:3000'
python scripts/start_unreviewed_dev.py --host 0.0.0.0 --port 8000
```

This wrapper is the only development shortcut. It requires the literal `UNREVIEWED_DEV_ONLY`, clears review/policy/release configuration, and returns an actual deterministic v2 Matrix/Trace response that remains non-decision-ready.

```bash
curl -i http://127.0.0.1:8000/health
curl -i -X POST http://127.0.0.1:8000/api/simulate \
  -H 'Content-Type: application/json' \
  -H 'X-Request-Id: local-dev-simulate' \
  --data @examples/simulate_request_v1.json
curl -i -H 'X-Request-Id: local-dev-evidence' \
  http://127.0.0.1:8000/api/evidence/EV-024
```

Expected: health `200`, simulate `200` with v2 `unreviewed_development_only`, and Evidence `200` with a source-backed page/bbox. A development-mode Boardroom request deliberately returns v1 `503` with `review_pending`.

## Frontend pairing

```bash
cd ../../frontend
npm ci
NEXT_PUBLIC_CAUSORA_API_BASE_URL=http://127.0.0.1:8000 \
NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE=UNREVIEWED_DEV_ONLY \
npm run dev -- --hostname 0.0.0.0 --port 3000
```

The frontend requires the same exact development sentinel to accept the marked unreviewed v2 response. It displays the Matrix, formula traces, and source Evidence, but Boardroom/Brief/human decision remain disabled.

## Normal reviewed mode

Do not set `CAUSORA_DEV_UNREVIEWED_MODE`. Supply the separately controlled paths from `.env.example`:

```bash
export CAUSORA_REVIEW_BUNDLE_DIR=/absolute/path/to/wang-reviewed-bundle
export CAUSORA_APPROVED_POLICY_PATH=/absolute/path/to/team_policy.json
export CAUSORA_POLICY_APPROVAL_RECORD_PATH=/absolute/path/to/policy_approval_record.json
export CAUSORA_TRACE_CONTRACT_V2_RELEASE_RECORD=/absolute/path/to/trace_v2_release_record.json
export CAUSORA_COMMON_API_CONTRACT_PATH=/absolute/path/to/API_CONTRACT_V2.md
export CAUSORA_TYPESCRIPT_V2_TYPES_PATH=/absolute/path/to/contracts-v2.ts
export CAUSORA_FRONTEND_V2_VALIDATOR_PATH=/absolute/path/to/simulate-api.ts
export CAUSORA_TRACE_ARTIFACT_DIR=/absolute/path/to/writable/audit-artifacts
uvicorn app.service:app --host 0.0.0.0 --port 8000
```

The normal endpoint succeeds only after the three verifiers pass. A reviewed `200` uses actual reviewed contract values/data version and registers that exact run. If engine, source verification, or release validation fails, it returns a typed error. It never falls back to mock success.

## Formal OpenRouter Boardroom enablement

Only an authorized owner may configure this in a private environment after reviewed mode is operating:

```bash
export CAUSORA_AI_PROVIDER=openrouter
export OPENROUTER_API_KEY='private value, never commit or send in chat'
export CAUSORA_OPENROUTER_PAID_AUTHORIZED=YES
export OPENROUTER_SCOPED_KEY_CONFIRMED=YES
export CAUSORA_OPENROUTER_BUDGET_JOURNAL=/absolute/private/writable/openrouter-budget.json
# Optional bounded timing values, pipeline uses one decreasing total deadline.
export CAUSORA_AI_TOTAL_TIMEOUT=30
export CAUSORA_AI_STAGE_TIMEOUT=12
export CAUSORA_CRITIC_TIMEOUT=12
export CAUSORA_AI_RETRIES=0
```

The provider first performs `/models` and `/key` preflight. It uses only the allowed OpenRouter models, six calls maximum, a USD 1.00 process limit, conservative persistent reservations, no automatic top-up, and no fallback to other credentials. A timeout/cancelled request may retain its reservation because remote execution may already have occurred.

## Cross-machine CORS

If the frontend is on a second computer, bind server to `0.0.0.0`, set `CAUSORA_CORS_ORIGINS` to that browser's actual origin (for example `http://192.168.1.30:3000`), and configure `NEXT_PUBLIC_CAUSORA_API_BASE_URL=http://192.168.1.20:8000`. Never configure the second computer to call its own `localhost:8000`.

## Tests and current performance capture

```bash
pytest -q
python scripts/benchmark_monte_carlo.py --runs 1000 --out ../../verification/day4_integration/performance_n1000.json
python scripts/benchmark_monte_carlo.py --runs 10000 --out ../../verification/day4_integration/performance_n10000.json
```

The benchmark outputs are explicitly labelled unreviewed engine performance evidence. On Windows, where Python does not provide the POSIX `resource` module, elapsed time still runs. The report explicitly sets `peakRssMiB` to `null` and `peakRssStatus` to `unavailable`. They must not be used as a review, release, Golden, Boardroom, or procurement attestation.
