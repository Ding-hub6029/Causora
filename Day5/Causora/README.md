# Causora Day 5 Public Delivery

This package contains the deployable Causora Day 5 source subset: the reviewed simulation API, Matrix and Formula Trace contracts, source-backed Evidence route, guarded Boardroom integration, frontend source, release records required by the reviewed launcher, and Render/Vercel configuration.

It includes runnable frontend tests and focused backend regression tests. It does **not** contain imported historical provenance, validation logs, earlier acceptance records, benchmark corpora, evaluation artifacts, . Those materials are retained separately in the private full-delivery archive and are not rewritten here.

## Current status

This is a source and deployment-preparation delivery. No public service, human test, paid provider request, external benchmark capture, or formal G5 acceptance is claimed by this package.

## Quick validation

```bash
python scripts/verify_package.py
python deployment/render_start.py --validate-only
```

## Local reviewed API

```bash
python -m pip install -r backend/backend/requirements.txt
HOST=0.0.0.0 PORT=8000 python deployment/render_start.py
```

The launch path rejects unreviewed development flags. A formal Boardroom request additionally requires the separately configured private OpenRouter secret, explicit authorization flags, and persistent budget journal.

## Frontend build

```bash
cd frontend
npm ci
npm run build:live
```

The production frontend uses `NEXT_PUBLIC_CAUSORA_API_BASE_URL` for the actual HTTPS API. Never put a secret in a `NEXT_PUBLIC_*` value.

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for the precise Render/Vercel settings and [PUBLIC_DELIVERY_SCOPE.md](PUBLIC_DELIVERY_SCOPE.md) for included and omitted material.

