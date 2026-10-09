# Causora — Day 4 Ding Front-End Integration

**Release:** Ding frontend `0.4.0`  
**Baseline:** Day 1/Day 2 data and shared `causora.contract.v1`. Day 3 live `/api/simulate` client  
**Owner scope:** Xiangfeng Ding — Brief UI, Evidence click-through, failure states, and a verified Golden Run shell

> Every claim carries a source. Every choice can be challenged.

## Day 4 delivery

- The five-stage flow remains **Data Intake → Scenario Lab → Decision Matrix → AI Boardroom → Decision Brief**. The shared v1 request/error DTOs, v2 simulation success validator, Day 1/2 fixtures, fixed options, and previously verified Matrix/Formula Trace behavior are preserved.
- A live Boardroom client posts only the existing v1 identity fields (`simulationId`, `dataVersion`, `scenarioId`) and validates the response against the current reviewed-v2 Simulation, matching request ID, scenario, selected feasible option, Critic status, and Numeric Guardrail. It sends no credentials and uses `cache: "no-store"`.
- `AgentOutput.body` metric placeholders (for example `{{delta_tco}}`) must be supported and declared in `metrics[]`. The UI renders them from the selected option in the matching current Simulation/scenario, not from model-supplied numbers. Unknown, malformed, or undeclared tokens fail response validation.
- Brief metrics and decision eligibility derive from the current validated Simulation and its `selections`. Missing/mismatched IDs, unknown metrics, failed guardrails, unreviewed development runs, and stale requests cannot create a decision-ready Brief.
- Approve/Reject are browser-local records bound to the current reviewed Simulation, matching Boardroom response, scenario, and option. They do not contact suppliers, approve contracts, or create an external system record. Saved examples and verified Golden snapshots are read-only.
- Evidence records are retrieved by their preserved ID. The UI validates the data version, source whitelist, page, quote, quote-match fields, and optional PDF-point bounding box. The PDF.js viewer opens the packaged source page and highlights only a valid API bounding box or text found by an exact quote match on that cited page. It never fabricates a locator. Missing/invalid sources, timeout, PDF load failure, and cancellation keep a visible return/retry path.
- An Evidence record with `quoteMatched: false` remains available for transparent inspection, but it cannot satisfy the Verified Golden cache gate. Both cache creation and cache reload require `quoteMatched === true`. The generic Evidence viewer remains ungated.
- Later Boardroom/Critic/Evidence failures do not clear an already validated Simulation, Matrix, Decision Delta, cost details, or Formula Trace. Requests are abortable, stale responses are ignored, and AI retry does not re-run Monte Carlo.
- A cached Golden is created only from a complete reviewed-v2 Simulation + matching validated Boardroom + every cited, matched Evidence record + a browser-local human choice. On reload its digest and validators are rerun. Opening it is read-only. `TEST_FIXTURE_ONLY` responses cannot be cached. The saved Day 1/2 example is clearly distinct from a verified Golden E2E.
- `npm run check` covers TypeScript, ESLint, all Day 1/2/3 regressions, the Day 4 API/template/locator/cache tests, the static export build, and a production static-server smoke that asserts the PDF.js `.mjs` worker uses a JavaScript MIME type.

## Local setup

Prerequisites: Node.js 22.16.x (see `.nvmrc`), npm, and Python 3.11+ if the backend is run locally.

### Frontend only

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev:local
```

Open `http://127.0.0.1:3000`. This frontend-only launch displays the packaged saved example. It does not create a live simulation. With the default empty `NEXT_PUBLIC_CAUSORA_API_BASE_URL`, live requests use same-origin `/api/simulate` and therefore require an external reverse proxy to the backend. If the backend is a separate local origin, set the public endpoint address (for example `http://127.0.0.1:8000`) and allow the frontend origin in the backend CORS allowlist. Use the explicit unreviewed-development instructions below only when you intend to exercise that mode. These frontend variables are not secrets. Never put a provider key in them.

### Explicit unreviewed Monte Carlo integration mode

This mode exercises the actual seeded backend calculation while preserving all human-review, policy, release, and downstream decision gates. Its output is **UNREVIEWED DEVELOPMENT ONLY — NOT DECISION-READY**.

Terminal A:

```powershell
cd backend\backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python .\scripts\start_unreviewed_dev.py --host 127.0.0.1 --port 8000
```

Terminal B:

```powershell
cd frontend
npm ci
Copy-Item .env.unreviewed-dev.example .env.local
npm run dev:local
```

Open `http://127.0.0.1:3000`, enter Decision Matrix, then run the comparison. The example environment file explicitly opts the browser validator into `UNREVIEWED_DEV_ONLY`. Confirm the amber non-decision-ready banner, the real validated Simulation, and the server-returned Formula Trace. This is an integration run, not an approval or a G4 pass.

To test default fail-closed behavior, clear `NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE`, restart Next.js, and run the normal backend service. With current pending team approvals, a valid simulation request is expected to return v1 HTTP 503. Do not set approval variables or edit pending records to make it return success.

## Current backend capability boundary

The integrated FastAPI service currently exposes `/health` and `POST /api/simulate`. It does **not** yet expose `POST /api/boardroom` or `GET /api/evidence/{id}`. Wang-owned Critic/Synthesizer/numeric-scan and fallback policy are not replaced by frontend code. Accordingly, the UI provides explicit locked/unavailable states and keeps Simulation/Formula Trace viewable, but cannot truthfully claim a real Boardroom→Brief→Evidence E2E.

The pre-existing 11-item Wang review record is recognized by the real verifier. The 15-topic team model/policy record and the v2 trace/release approval remain pending. **Formal G4 remains PENDING** until the team supplies the missing reviewed downstream services and records and a real reviewed run passes all matching checks.

## Third-party PDF rendering

`pdfjs-dist` is pinned in `package-lock.json`. Its original Apache-2.0 license is preserved at `third_party/pdfjs-dist/LICENSE`. `scripts/copy-pdf-worker.mjs` deterministically copies the matching worker into `public/pdf.worker.min.mjs` on install and before build.

## Production and verification

```bash
npm run check
```

The successful build exports static files to `out/`. `npm start` serves the export locally. A static deployment requires a separately reachable API origin or a same-origin reverse proxy for live requests. No API server, provider credential, or server-side key is bundled in the frontend archive.

To verify PDF.js against the **production static preview** after `npm run build`, start `HOST=127.0.0.1 PORT=4173 npm start` in `frontend/`, then run `CAUSORA_PRODUCTION_PREVIEW_URL=http://127.0.0.1:4173 python3 verification/day4_production_pdf_acceptance.py` from the package root. The Chromium check clicks `Open source quote`, requires `/pdf.worker.min.mjs` to return HTTP 200 with a JavaScript MIME, and verifies the cited PDF canvas and exact-quote highlight. The backend Boardroom response-header and CORS requirements are specified in `API_CONTRACT.md` and `DAY4_TEAM_HANDOFF.md`.

See `DAY4_CHANGELOG.md`, `DAY4_TEST_REPORT.md`, `DAY4_TEAM_HANDOFF.md`, `verification/DAY4_TASK_MATRIX.md`, the root `README.md`, and the historical Day 3 reports for exact scope and evidence.
