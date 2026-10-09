# Causora Day 3 Integrated Delivery

Current status: TECHNICAL_FIX_REPORT.md. This repaired three-owner baseline is suitable for Day 4 development. Shared Day 1/2 v1 data and Golden inputs remain unchanged. Day 4's full business workflow is not implemented.

Fixes include actual-source SHA and eleven-item dependency validation, fifteen policy topics, reviewed-v2 frontend support, Windows UTF-8 compatibility and readable responsive layout. Original Wang confirmation, native conversion and English translation are under backend/backend/reviewed/wang-2026-10-07. Old pending worksheets are historical.

To load the provided human confirmation while keeping policy/release gates, run `python scripts/start_review_gated.py --port 8000` from backend/backend/. Existing review is then recognized. Policy/trace release still block formal success. The explicit development launcher below deliberately clears review configuration. Formally gated v2 responses are supported without a frontend development opt-in.

Pending team records are in release-pending/. Their status cannot be renamed into approval. This source package excludes node_modules, virtual environments and build caches. Install and build for deployment.

## Scope and runtime modes

Ding owns Decision Matrix/Formula Trace frontend. Deng owns FastAPI/Monte Carlo. Wang owns independent agent/MC review tools and evidence materials. Directories remain separated. Agent output is not injected as an approved Boardroom. Shared v1 contracts/fixtures are preserved.

Development sends shared v1 POST /api/simulate and accepts v2 only with exact UNREVIEWED_DEV_ONLY opt-in, both unreviewed headers, correct execution context, identity, matrix, accounting and nine traces. Actual seeded synthetic computation remains NOT DECISION-READY: persistent banner, no formal winner, no approval, no unreviewed downstream Brief/Boardroom injection. Traces contain real formulas, components, rounding, statistical denominators/rank, provenance and one labelled 104-week trial path, not an aggregate mean. Default formal backend fails closed with v1 503 until review, three-owner policy and common v2 release validate.

Day 3 matrix/traces support entering Day 4. Formal decision release remains PARTIAL. The eleven-item Wang confirmation is supplied and converted. Policy/release remain outstanding.

## Windows PowerShell local integration

Python 3.11+ (verified with 3.12), Node.js 22, npm and initial registry access are required.

Terminal A:

```powershell
cd backend\backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python .\scripts\start_unreviewed_dev.py --host 127.0.0.1 --port 8000
```

Default dataset ds-001. http://127.0.0.1:8000/health must show unreviewed_development_only and decisionReady=false. Launcher isolates trace audit output. True/1 are not valid opt-ins. Do not fabricate approval variables.

Terminal B:

```powershell
cd frontend
npm ci
Copy-Item .env.unreviewed-dev.example .env.local
npm run dev:local
```

Open http://127.0.0.1:3000, enter Decision Matrix and Run simulation. Check nine server cells, navigation retaining the same run, selected scenario/option trace context, full costs/weekly trace and persistent warning. Change assumptions and rerun. Previous results become stale. Missing headers/identity/provenance/traces must fail closed.

Restore formal defaults by stopping frontend, restoring .env.example or clearing NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE, restarting and using normal backend Uvicorn per RUNBOOK.md. Without approvals, 503 is expected.

## Wang's isolated optional development analysis

Keep a separate Python environment. Offline claim selector needs no provider key. With backend running:

```powershell
cd agents\wanghao-day3
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m agent_day3.mc_cli fetch-analyse --enable-unreviewed-dev --base-url http://127.0.0.1:8000 --request mc_examples\http_base\request.json --capture ..\..\fresh-mc-capture --scenario baseline --provider offline --out ..\..\fresh-baseline-analysis.json
```

Capture/output paths must be new. CLI requests fresh data and saves immutable request/response/headers/digest rather than replaying an old capture. Analyse the same capture for demand-drop/lead-stress if needed. DEV_ONLY role analysis is not AgentOutput, recommendation or approval. Pending worksheets are not signed records. Do not execute a real sign-off on another person's behalf.

## Checks and reading order

- frontend/: npm run check (types, lint, tests, build, production serving).
- backend/backend/: install dependencies, python -m pytest -q. RUNBOOK.md.
- agents/wanghao-day3/: python -m pytest -q with CAUSORA_DAY3_BACKEND set to the actual backend/backend directory for verifier compatibility tests.
- Actual HTTP smoke: health and simulate, then real frontend request. Record v2/200, nonempty identities, both headers, unreviewed executionContext and complete traces. Development smoke is not human sign-off.

INTEGRATION_TEST_REPORT.md preserves the historical integration results. TECHNICAL_FIX_REPORT.md and verification/ document later fixes/checks. INTEGRATED_MANIFEST.sha256 and module manifests cover final files. Read frontend/README.md, DAY3_CHANGELOG/INTEGRATION/TEST_REPORT and API_CONTRACT. Backend RUNBOOK, DEV_UNREVIEWED_INTEGRATION, G3_DECISIONS_PENDING, CONFIGURATION_AND_VERIFIERS. Wang APPLY_TO_TEAM, CONTRACT_COMPATIBILITY, evidence_review/FORMAL_REVIEW_FORMAT and reports/.
