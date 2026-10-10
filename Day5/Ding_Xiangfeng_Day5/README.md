# Causora - Ding Xiangfeng Day 5 corrected baseline

**Local technical delivery: ready for teammate handoff. Public deployment and genuine round-two user validation: delegated to Deng Jinzhu and pending actual evidence. Team G5 is not asserted complete.**

This is a complete runnable source baseline, including frontend, real simulation backend, AI/guardrail code, approved synthetic release records, source data, authentic frozen Golden, tests and two prebuilt website modes. Day 4 acceptance documents describe historical Day 4 evidence; they are not new Day 5 sign-offs.

## Windows: choose one mode

Extract the entire ZIP to a short normal folder, such as C:/Causora/Day5. Do not run files inside the ZIP viewer. Install Node.js 22 and Python 3.12 if missing. No provider credential is required for simulation or Golden replay.

| Goal | Steps | Result |
| --- | --- | --- |
| Real simulation | Run SETUP_WINDOWS.cmd once, then START_LIVE.cmd. Open http://127.0.0.1:3000/ | Real reviewed backend on port 8000, live website on port 3000. New Boardroom needs separately authorized private AI configuration. |
| Read-only replay | With Node.js installed, run START_STATIC.cmd. Open http://127.0.0.1:3000/ and click Open Verified Golden Run | No Python/backend needed. Genuine frozen Matrix, Trace, Evidence PDF, Boardroom and Brief remain explicitly read-only. |

Use only one default-port mode at a time. If a port is occupied, choose different ports instead of stopping somebody else's application:

```powershell
./scripts/start-day5.ps1 -Mode live -BackendPort 8001 -FrontendPort 3001
./scripts/start-day5.ps1 -Mode static -FrontendPort 3002
```

Logs and owned process IDs are in .runtime/<mode>-<frontend-port>/. The launcher checks backend and frontend readiness before reporting success. It does not bypass PowerShell execution policy. If scripts are restricted, use an allowed shell and the separate commands below.

## Separate startup and developer checks

Backend, from backend/backend, after installing requirements in an isolated Python 3.12 environment:

```text
python scripts/start_day4_reviewed.py --port 8000
```

Frontend, from frontend, with Node.js 22:

```text
node scripts/start-mode.mjs live
node scripts/start-mode.mjs static
```

These are alternatives, not simultaneous default-port commands. Live defaults to proxying /api/* and /health to http://127.0.0.1:8000. CAUSORA_BACKEND_URL is a server-only override. Both included builds are mode-marked; requesting the wrong mode fails rather than silently serving a locked replay as live.

Developers changing source must run npm ci and npm run check in frontend. The check performs typecheck, lint, 56 tests, both production builds and three production-server tests. npm run build:previews refreshes both frontend/builds/static and frontend/builds/live; out ends as the live export. Ordinary npm run build alone does not refresh the mode-specific builds.

Run python scripts/verify_package.py before installing or editing to verify the complete delivery inventory. The sole current package inventory is MANIFEST.sha256. PACKAGE_FILE_LIST.csv lists payload files; that CSV is covered by the manifest. Historical component manifests are preserved under provenance/historical-component-manifests and must not be used as current checksums.

## What is live and what is replay

Actual simulation works without a model key. A missing provider key yields AI unavailable while keeping validated Matrix and Formula Trace; it does not unlock approval. New live Boardroom success needs actual authorized provider access. No new paid model call was made in this repair. The bundled Golden retains authentic Day 4 provider output and SHA-256 integrity verification. Its stored Rejected choice is an automated Day 4 browser-test artifact, not a human business decision or team approval.

Do not put keys in browser variables, exports or ZIPs. The existing provider budget/rate/security gates remain intact. Original approved assumptions and Matrix + Trace v2 release records are preserved. Consult the historical Day 4 provider instructions only when a new paid session has been explicitly authorized; this delivery does not authorize additional spending.

## Handoff and evidence

- Deployment and genuine participant-test instructions are supplied separately to Deng Jinzhu, outside this code ZIP: DEPLOYMENT_HANDOFF_DENG.md, DEPLOYMENT.md, TESTER_WALKTHROUGH.md and USER_TEST_ROUND2.md.
- USER_TEST_ROUND2.md and TESTER_WALKTHROUGH.md: Deng's genuine participant-test organization, exact button steps and blank feedback record.
- DING_DAY5_ACCEPTANCE.md: PDF mapping and current acceptance boundary.
- TEST_REPORT_DAY5.md and verification/day5-final/: current technical results and browser screenshots, explicitly automated/AI-assisted.
- SECURITY_AUDIT_DISPOSITION.md: zero reported production dependency findings; five development dependency findings remain disclosed with a tested configuration boundary.
- provenance/day5-incoming/: original incoming documentation retained as historical evidence, including obsolete preview instructions.

Deployment/test handoff documents have been removed from this ZIP, including their obsolete incoming copies. The separate current documents accompany this delivery. There is no current public URL in this package. Deng will return verified public URLs and deployment evidence. Genuine human feedback, feedback-driven changes and retest must be recorded from actual participants before closing that requirement.
