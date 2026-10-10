# Causora Deployment Guide

## Repository layout

Place this directory at `Day5/Causora` inside the team repository. Do not deploy a repository root containing earlier project days and do not deploy `backend/backend` alone.

## Render API

Create a Python Web Service with:

| Field | Value |
| --- | --- |
| Root Directory | `Day5/Causora` |
| Build Command | `python -m pip install --upgrade pip && python -m pip install -r backend/backend/requirements.txt` |
| Start Command | `python deployment/render_start.py` |
| Health Check | `/health` |
| Compute | Free, simulation hosting only |

Initial non-secret values:

```text
CAUSORA_AI_PROVIDER=openrouter
CAUSORA_OPENROUTER_PAID_AUTHORIZED=NO
OPENROUTER_SCOPED_KEY_CONFIRMED=NO

```

Do not set development overrides. Do not enter an OpenRouter key during initial API deployment.

## Vercel frontend

Create a Next.js project with Root Directory `Day5/Causora/frontend`, Install Command `npm ci`, Build Command `npm run build:live`, and Output Directory `builds/live`.

After the Render HTTPS URL exists, set:

```text
NEXT_PUBLIC_CAUSORA_API_BASE_URL=https://<render-host>
NEXT_PUBLIC_CAUSORA_STATIC_ONLY=false
```

Then set `CAUSORA_CORS_ORIGINS=https://<vercel-host>` in Render and redeploy. Do not use a wildcard CORS origin or a local development URL.

