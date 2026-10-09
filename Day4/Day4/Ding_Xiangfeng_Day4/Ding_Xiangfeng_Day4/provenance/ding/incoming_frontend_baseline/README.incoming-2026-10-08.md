# Causora Day 4 — Deng Jinzhu three-owner integration

**Package role:** complete Day 4 integration source for Ding Xiangfeng's Day 5 work.  
**Authoritative package name:** `Deng_Jinzhu_Day4.zip` (archive created beside this source directory).  
**Dataset:** `ds-001`.

> This package is an integrated development deliverable. It does **not** claim human contract review, model-policy approval, Trace-v2 release approval, a reviewed Golden Run, a formal Boardroom result, or a procurement decision.

## What is integrated

| Owner | Integrated responsibility | Current state |
| --- | --- | --- |
| Ding Xiangfeng | Frontend public API clients, five-stage page flow, v1/v2 validators, PDF.js viewer, UI gates | Retained as the public interface baseline. Only the existing Evidence callback now requests the same `/api/evidence/{id}` route for a current **unreviewed development** run, so locator integration can be inspected without bypassing Boardroom/Brief gates. |
| Deng Jinzhu | Monte Carlo Matrix/Formula Traces, v1 request/v2 success service, run registry, real source-backed Evidence, PDF-coordinate conversion, CORS, fail-closed gates | Integrated and tested. `/api/simulate` retains one exact run. `/api/evidence/{id}` re-reads the actual packaged PDF and emits PDF.js-compatible coordinates. |
| Wang Hao | `agent_day4` pipeline, OpenRouter provider, source/evidence checks, Numeric Guardrail, Critic, fallback policy, budget journal | Imported under `agents/wanghao-day3/` and lazily called only by the formal Boardroom route. Its offline suite passes. No paid call was made by this integration. |

Read [INTEGRATION_REPORT.md](INTEGRATION_REPORT.md), [MERGE_MANIFEST.md](MERGE_MANIFEST.md), and [G4_ACCEPTANCE_STATUS.md](G4_ACCEPTANCE_STATUS.md) before making shared changes. Historic incoming reports remain preserved under `provenance/`. They are not current integrated-package acceptance evidence.

## Directory map

```text
frontend/                         Ding public UI, contracts, PDF.js Evidence viewer
backend/backend/                  Deng FastAPI service, engine, traces, Evidence/Boardroom adapter
agents/wanghao-day3/              Wang Day 4 AI module and OpenRouter adapter
verification/final/               Current local HTTP and browser evidence (development-only)
provenance/ding|deng|wang/        Preserved incoming owner material and historical reports
release-pending/                  Deliberately pending policy/release inputs, never edited to force a pass
```

No API keys, virtual environments, `node_modules`, `.next`, audit journals, or irrelevant caches are shipped.

## Interfaces and version rule

| Route | Request | Success | Failure / gate |
| --- | --- | --- | --- |
| `GET /health` | none | v1 service state | `503` only if source dependencies are unavailable |
| `POST /api/simulate` | `causora.contract.v1` | `causora.contract.v2`: `data.simulation`, `data.deltas`, `data.selections`, `data.traces[scenarioId][optionId]` | v1 error envelope (`422` or `503`) |
| `GET /api/evidence/{EV-###}` | path ID + optional `X-Request-Id` | v1 `EvidenceRecord`, current run data version, source-backed PDF locator | v1 `404`/`503` |
| `POST /api/boardroom` | v1 identity: `simulationId`, `dataVersion`, `scenarioId` | v1 Boardroom envelope only for an exact retained **reviewed, decision-ready** run | v1 `422`/`503`. Development runs fail `review_pending` |

The version combination is intentional: Day 1/2 request/error and downstream Boardroom/Evidence wires remain `causora.contract.v1`. Day 3 Matrix + Trace success remains `causora.contract.v2`.

## Local startup

### 1. Install backend dependencies

```bash
cd Deng_Jinzhu_Day4/backend/backend
python3 -m venv .venv
source .venv/bin/activate                 # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Start a clearly labelled development-only integration server

This runs a real, deterministic seeded Matrix + Trace calculation using packaged synthetic inputs. It does not use any AI provider and never becomes decision-ready.

```bash
python scripts/start_unreviewed_dev.py --host 0.0.0.0 --port 8000
# Windows CMD: scripts\start_unreviewed_dev.cmd --host 0.0.0.0 --port 8000
```

Expected endpoints:

```bash
curl http://127.0.0.1:8000/health
curl -H 'Content-Type: application/json' \
  --data @examples/simulate_request_v1.json \
  http://127.0.0.1:8000/api/simulate
```

The `200` success carries `UNREVIEWED_DEV_ONLY`, `decisionReady:false`, `X-Causora-Review-Status: unreviewed-development-only`, and `X-Causora-Execution-Mode: unreviewed-development-only`. It is suitable only for interface, Trace, and Evidence-locator inspection.

### 3. Start the frontend against that server

```bash
cd ../../frontend
npm ci
NEXT_PUBLIC_CAUSORA_API_BASE_URL=http://127.0.0.1:8000 \
NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE=UNREVIEWED_DEV_ONLY \
npm run dev -- --hostname 0.0.0.0 --port 3000
```

On Windows PowerShell, set the two `NEXT_PUBLIC_...` variables in the current shell before `npm run dev`. The exact sentinel is mandatory. The frontend rejects an unreviewed v2 response without it.

For a frontend on a **different** machine, use the backend machine's reachable LAN hostname/IP instead of the frontend machine's `localhost`, for example `http://192.168.1.20:8000`. Add the exact browser origin (for example `http://192.168.1.30:3000`) to `CAUSORA_CORS_ORIGINS`. Do not use a wildcard.

See [backend/backend/RUNBOOK.md](backend/backend/RUNBOOK.md) for the reviewed-mode and OpenRouter enablement conditions.

## Formal enablement is deliberately separate

Do **not** use the development launcher for a formal review. Normal Uvicorn startup remains fail-closed until all three are supplied and verified:

1. Wang's reviewed contract bundle, including actual reviewed fields and record.
2. a three-owner approved model-policy record. And
3. a three-owner Trace-v2 release record that binds the schema, Pydantic models, shared contract, TypeScript types, and frontend validator hashes.

Only then can a normal `POST /api/simulate` produce a reviewed v2 run. Only an exact, retained reviewed decision-ready run may enter `/api/boardroom`. The provider additionally requires a configured OpenRouter key, successful read-only preflight, persistent budget journal, and explicit paid-dispatch authorization. No key or paid authorization is included in this package.

## Current verification evidence

- `verification/final/dev_http_smoke_summary.json`: local dev-only `200` Matrix/9 Trace cells, `EV-024` page 4 service-provided locator, CORS preflight, and intentional Boardroom `503 review_pending`.
- `verification/final/browser_ev024_live_api_bbox.webp`: real browser click of EV-024 after a live development simulation. The viewer reports **Server-provided PDF bounding box highlighted**.
- `verification/day4_integration/performance_n1000.json` and `performance_n10000.json`: current engine timing runs, labelled unreviewed benchmark only.
- `verification/day4_integration/wang_agent_offline_tests.log`: Wang AI module offline verification. No provider dispatch occurred in this integration.

## Team status

- **Deng implementation scope:** complete for the source-backed simulation/Trace/Evidence adapter and three-owner connection boundary.
- **Three-owner technical integration:** complete for code, offline checks, and development-only browser flow.
- **Team G4 acceptance:** **PENDING**. It requires real human records, approved policy/release configuration, a separately authorized OpenRouter formal run, and three-owner acceptance. No pending state was changed to approved.
