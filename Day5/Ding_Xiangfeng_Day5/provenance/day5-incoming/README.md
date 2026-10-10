# Causora Integrated Source — Day 4 Baseline + Day 5 Ding

**Day 4 G4 technical acceptance: PASS (historical baseline). Day 5 Ding frontend: PARTIAL — technical staging checks PASS; genuine user validation is pending.**

Read [DAY4_FINAL_ACCEPTANCE.md](DAY4_FINAL_ACCEPTANCE.md) for current results and scope. This package includes the complete frontend, backend, AI pipeline, actual release records, built preview, tests, source data, preserved review evidence and frozen real E2E result. All three owner ZIPs use identical runtime files. Ding Xiangfeng owns frontend/integration, Deng Jinzhu owns simulation/service, and Wang Hao owns AI/Critic review.

## Install once

Use Python 3.12 and Node.js 22 or a supported newer release. From this package directory:

```powershell
python -m venv backend/backend/.venv
backend/backend/.venv/Scripts/python.exe -m pip install -r backend/backend/requirements.txt
cd frontend
npm ci
cd ..
```

The built `frontend/out/` preview is included. Rebuild after source changes with `npm run check` inside frontend.

## Start the complete local application

```powershell
./scripts/start-day4.ps1
```

Open http://127.0.0.1:3000/. The launcher loads all approved release records, starts the real backend on port 8000, and serves the built frontend with same-origin `/api/*` and `/health` forwarding. It does not stop other applications. If ports are occupied, use `-BackendPort 8001 -FrontendPort 3001`. Process IDs and logs are recorded in `.runtime/`. On systems that restrict PowerShell scripts, invoke an allowed shell or run the two components separately below; do not disable security settings.

The actual simulation works without an AI key. Boardroom requires a private provider configuration. A missing key produces a structured unavailable message and retains the Matrix and Trace.

## Configure real OpenRouter AI, when needed

Set these variables in the server/launcher environment; never put a key in a frontend variable or commit it:

```powershell
$env:CAUSORA_AI_PROVIDER='openrouter'
$env:OPENROUTER_API_KEY='<your private key>'
$env:CAUSORA_OPENROUTER_PAID_AUTHORIZED='YES'
$env:OPENROUTER_SCOPED_KEY_CONFIRMED='YES'
$env:CAUSORA_AI_RETRIES='0'
./scripts/start-day4.ps1
```

These YES settings are an explicit authorization to make billable requests with the configured scoped key. The transport checks available models, balance and a persistent budget journal before dispatch. Primary roles and synthesis use `openai/gpt-5-mini`; Critic uses `google/gemini-3.1-pro-preview`, with explicitly labelled same-family fallback when permitted. The journal enforces the existing six-call / USD 1 authorization envelope and persists across restarts. Do not delete it to silently retry; use a separately authorized new journal for a new paid validation session. The launcher supplies the default journal path if none is set. No API key is included in this ZIP.

## Separate component startup

Backend (from backend/backend): `python scripts/start_day4_reviewed.py --port 8000`.

Frontend (from frontend): `npm start`. Its proxy defaults to http://127.0.0.1:8000; override with server-only `CAUSORA_BACKEND_URL`. The included build uses relative API URLs. When deploying the static output elsewhere, provide an equivalent reverse proxy or rebuild with `NEXT_PUBLIC_CAUSORA_API_BASE_URL` set to the public backend address and configure that origin in backend CORS. No public deployment is claimed by this local package.

## Checks and frozen real E2E

```powershell
python scripts/verify_package.py
cd backend/backend
python -m pytest -q
cd ../../agents/wanghao-day3
python -m pytest -q
cd ../../frontend
npm run check
node scripts/verify-golden-e2e.mjs
```

The last command checks the included `verification/g4-final/verified_golden_e2e.json` with the production validators, including digest integrity, run identity, numerical reconciliation, complete cited Evidence and decision binding. It also confirms that a tampered record is rejected, without making provider calls. In the browser, a complete reviewed run can be exported with **Export verified Golden snapshot**. Browser cached Golden runs remain read-only. The supplied snapshot's Rejected decision is an automated UI test record, not a team's business decision or release rejection.

## Current files

| Location | Purpose |
| --- | --- |
| frontend/ | Ding's five-stage UI, contracts, validators, PDF viewer and built preview |
| backend/backend/ | Deng's actual simulation, Matrix/Trace, reviewed service and Evidence registry |
| agents/wanghao-day3/ | Wang's Day 4 roles, Critic, synthesis, numeric/business guards and provider adapters |
| release/ | Current policy approval, Trace-v2 release and authorization provenance |
| verification/g4-final/ | Current tests, real HTTP captures, frozen E2E, usage summary and browser screenshots |
| verification/g5-public-preview/ | Day 5 public HTTPS fresh-browser result and screenshots |
| DING_DAY5_ACCEPTANCE.md | Ding's personal Day 5 status, evidence, and blockers |
| USER_TEST_ROUND2.md | Participant task and feedback form; awaits genuine responses |
| DEPLOYMENT.md | Temporary staging URL, local static-only run, and backend limits |
| TEAM_HANDOFF_DAY5.md | Day 5 module ownership and integration contract; G5 remains pending |
| provenance/ | Preserved incoming/historical material; not current acceptance status |
| release-pending/ | Inert original templates; not loaded by the reviewed launcher |

Original Wang review evidence is preserved, including its original-language contents and the supplied English materials. Current application text, filenames and explanatory documents are English; the verbatim approval reply remains evidence with an English translation.

`MANIFEST.sha256` and `PACKAGE_FILE_LIST.csv` are preserved Day 4 baseline records and are not the current Day 5 checksum. Use `DAY5_MANIFEST.sha256` to verify the current Day 5 package (it excludes itself to avoid a self-referential hash). These inventories are integrity checks, not cryptographic human signatures.

## Day 5 — Ding Xiangfeng frontend staging

The Day 5 frontend adds a public static-only path that bundles the genuine verified E2E snapshot and revalidates it in a fresh browser when no browser cache exists. The verified replay is read-only and marked `CACHED · VERIFIED GOLDEN RUN`. The snapshot's `Rejected` value is an automated G4 UI-test artifact scoped to one browser; it is not a business decision, human rejection, or team release status.

This package does not claim a persistent third-party deployment. Vercel is optional; the owner said they are not registered, so no Vercel account is required or connected. The user-facing preview is an account-free temporary HTTPS Sandbox URL (see `DEPLOYMENT.md`); it may stop when the temporary Sandbox service ends.

The staging build has **no public backend**. Therefore live `GET /health`, `POST /api/simulate`, `GET /api/evidence/{evidence_id}`, and `POST /api/boardroom` (including new Critic/Brief generation) are unavailable until a public API backend is separately authorized, deployed, and configured. The static Golden's Matrix, Formula Trace, cached Boardroom/Brief, cited Evidence records, and bundled PDF remain viewable offline. No API/provider key is included, and no paid AI call is made.

Personal Day 5 technical verification is separate from human validation. `DING_DAY5_ACCEPTANCE.md` records the actual test results and blockers. `USER_TEST_ROUND2.md` is the short participant task and feedback form; genuine participant feedback and at least one feedback-driven high-impact fix remain pending until real people complete it. `TEAM_HANDOFF_DAY5.md` preserves Deng Jinzhu's and Wang Hao's Day 5 ownership and keeps team G5/release gates pending.

New Day 5 source changes are confined to Ding's frontend, public static config, and verification/report assets; the shared Matrix/Trace v2 contract, approved assumptions/policies, backend algorithms, teammate AI pipeline, and Day4 approval records are unchanged.
