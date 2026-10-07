> Technical fix status (2026-10-07): See the integrated package root TECHNICAL_FIX_REPORT.md. Original pending templates remain historical. Wang's supplied confirmation is preserved at backend/backend/reviewed/wang-2026-10-07. Model policy and release still require team confirmation.

# Causora — Day 3 Ding Front-End Integration

**Release:** Day3 Ding UI package `0.3.0`  
**Integration baseline:** Day1/Day2 team archive; shared `causora.contract.v1`  
**Owner scope:** Xiangfeng Ding — Decision Matrix + Formula Trace UI and the client-side `/api/simulate` integration

> Every claim carries a source. Every choice can be challenged.

This package starts from Ding's Day2 project inside the three-person team bundle. Day1 data, scenario IDs, fixed options D0/D1/D2, `lib/contracts.ts`, the Golden snapshot, API contract and the existing visual system are preserved. The shared contract file and Day1/Day2 fixtures are not rewritten.

## Day3 delivery

- Replaces the single-scenario mock table with a **3-scenario × 3-option Matrix**. The saved Day2 values are explicitly labelled until a validated server response is received.
- Builds the existing v1 `SimulateRequest` from the Day2 scenarios/options and current controls. Risk percent is sent as a decimal fraction; cash ceiling is whole USD; the selected demand shock is rescaled against the same scenario forecast rather than changing the locked option allocations.
- Sends `POST /api/simulate` to the same-origin route by default, or to the configured backend origin. No client-side provider credentials are used.
- Validates the response envelope/version, dataset version consistency, 104-week horizon, positive Monte Carlo run count, seed, non-mock simulation ID, complete matrix, cost reconciliation, purchase/unit reconciliation, all option-minus-D0 deltas, and per-scenario constraint selection/violation ordering before applying any live values.
- Formula Trace reads the selected live cell’s server-returned component breakdown, shows run/version/seed/request metadata and the returned Decision Delta, and marks weekly holding/stockout drivers as not exposed by the shared v1 DTO rather than inventing them.
- Failed, malformed, stale, or timed-out requests do not overwrite the saved example. Changed assumptions invalidate an earlier response. A live Matrix cannot be mistaken for the Day2 Boardroom/Brief mock; those downstream stages are gated until a matching Boardroom response exists.
- Browsing a scenario or inspecting an option inside the Matrix changes only the view state; it does not edit request assumptions or discard an otherwise valid live run. Formula Trace uses the scenario currently being inspected.
- Live recommendation highlighting is derived from the validated per-scenario `selections` response, not from the server’s decorative `tone` hint.
- Adds contract-focused client tests and retains the Day1/Day2 data, Golden Run, evidence and static production-serving regression tests.

## Run locally

Prerequisites: Node.js `22.16.x` (see `.nvmrc`) and npm.

```bash
npm ci
Copy-Item .env.example .env.local   # Windows PowerShell; edit values as needed
npm run dev
```

Open `http://localhost:3000`. Configure `NEXT_PUBLIC_CAUSORA_API_BASE_URL` as follows:

- Leave it blank when the backend is reverse-proxied at the same origin; the client posts to `/api/simulate`.
- Set it to the backend origin, e.g. `http://localhost:8000`, when the service is hosted separately. The backend must allow the frontend origin through CORS.
- Set `NEXT_PUBLIC_CAUSORA_DATASET_ID` to a dataset already loaded on that backend. The default is the shared-contract example ID `ds-001`.

These are public frontend settings, not secrets. The endpoint address is compiled into the client bundle; never put an API key or provider secret in these variables.

Run the full source and production checks from the project root:

```bash
npm run check
```

`npm run build` creates the static site in `out/`; `npm start` serves that export locally. A static host still needs a separately reachable API origin or a same-origin reverse proxy for live simulation requests. This frontend archive does not add or claim an API server.

## Data and integration boundary

- Synthetic records under `demo_data/` and `public/demo/` remain the Day1/Day2 fixtures. They are not evidence about a real supplier or contract.
- A saved Matrix is a Day2 example with `monteCarloRuns: 0`; it remains labelled **saved example** and is never relabelled as simulated.
- A test-only response is used solely to exercise the v1 client validator. It is not a Monte Carlo run, benchmark, backend acceptance, or real E2E result.
- `API_CONTRACT.md` and `lib/contracts.ts` remain the shared v1 source of truth. The client does not change their field names or units.
- The Day2 Jinzhu handoff explicitly records that its deterministic preview is unreviewed, not decision-ready, and not the public `/api/simulate` success endpoint. This package is the Ding-owned frontend integration; it does not substitute that preview for a live Monte Carlo API or claim team G3 sign-off.
- After a live simulation, the Day2 Agent/Brief sample is intentionally hidden. The UI waits for a Boardroom result tied to the exact simulation rather than showing an unrelated saved recommendation or permitting approval.

See `DAY3_CHANGELOG.md`, `DAY3_INTEGRATION.md`, `DAY3_TEST_REPORT.md`, `API_CONTRACT.md`, and the historical Day2 reports for detailed scope and verification.


## Day 3 team integration — explicit unreviewed development mode

The team backend exposes a real seeded Monte Carlo v2 response only through its clearly named development launcher while the external review, three-owner policy and v2 release records are pending. This is **integration-only and not decision-ready**. Never use the development `selections` as a recommendation or approve from this run.

1. In a first PowerShell window, from `backend\backend`:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python .\scripts\start_unreviewed_dev.py --host 127.0.0.1 --port 8000
   ```

2. In a second PowerShell window, from `frontend`:

   ```powershell
   npm ci
   Copy-Item .env.unreviewed-dev.example .env.local
   npm run dev:local
   ```

3. Open `http://127.0.0.1:3000`, enter **Decision Matrix**, and run the simulation. The browser adapter accepts v2 only when the explicit `UNREVIEWED_DEV_ONLY` variable, both unreviewed response headers, data/version marker, execution context, the full 3×3 response and every weekly trace validate. The page keeps a persistent amber warning and cannot display a formal winner or approve the run. Formula Trace exposes the server formulas, rounding/count basis, parameter provenance, identities and one labelled 104-week sample path per selected cell.

4. To return to the default fail-closed behavior, stop the frontend, restore `.env.example` (or clear `NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE`), restart Next.js, and use the backend's normal Uvicorn command. Without real external records the backend is expected to return v1 HTTP 503; do not replace that with a mock success.

The Wang Agent/Monte Carlo review workspace stays isolated in `agents\wanghao-day3`; it is not injected as an approved Boardroom recommendation. See the root integration README and the backend `RUNBOOK.md`, `DEV_UNREVIEWED_INTEGRATION.md`, and `G3_DECISIONS_PENDING.md` for their respective controls and open decisions.
