# Causora Day 4 — Wang Hao

**Status: G4 technical acceptance PASS. Complete shared baseline for Day 5.**

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
| provenance/ | Preserved incoming/historical material; not current acceptance status |
| release-pending/ | Inert original templates; not loaded by the reviewed launcher |

Original Wang review evidence is preserved, including its original-language contents and the supplied English materials. Current application text, filenames and explanatory documents are English; the verbatim approval reply remains evidence with an English translation.

MANIFEST.sha256 covers every published file except itself. PACKAGE_FILE_LIST.csv excludes itself and the root manifest to avoid self-referential hashes. These are integrity inventories, not cryptographic human signatures.
