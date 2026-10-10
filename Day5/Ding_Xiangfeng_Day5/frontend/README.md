# Causora frontend — Ding Xiangfeng

This frontend preserves the integrated Day 4 five-stage workspace and Matrix/Trace v2 contracts. Its public Day 5 preview is intentionally **static-only** unless a separately reviewed public HTTPS API is configured.

## Install and verify

```sh
npm ci
npm run check
```

`npm run check` runs TypeScript, ESLint, regression tests, the static Next.js production build, and production static-server tests. The PDF.js `.mjs` worker must be served as JavaScript. Verify the frozen Golden with:

```sh
node scripts/verify-golden-e2e.mjs
```

`public/golden/verified_golden_e2e.json` is the genuine frozen E2E record, byte-identical to `../verification/g4-final/verified_golden_e2e.json`. If browser storage is empty or invalid, the app loads only the fixed same-origin asset path and runs the production validators. Browser storage is optional, never the only Golden source.

## Public static-only preview

Use this configuration only when no public API backend is deployed:

```sh
NEXT_PUBLIC_CAUSORA_STATIC_ONLY=true npm run build
CAUSORA_STATIC_ONLY=true npm start
```

This mode shows **backend not configured**, issues no `/health` request from the frontend, and opens the verified replay read-only after validating the bundled complete Golden. The stored `Rejected` value is an automated G4 UI-test artifact, not a human decision, business rejection, or release approval. At the static-server layer, `/health` and `/api/*` return HTTP 503 `backend_not_configured` and are not forwarded to localhost.

The following require a separately deployed public API backend and are unavailable in static-only staging:

- `POST /api/simulate` — live Monte Carlo Simulation;
- `GET /api/evidence/{evidence_id}` — live Evidence record fetch (the cited Golden Evidence and bundled PDF remain viewable);
- `POST /api/boardroom` — new Boardroom/Critic and live Brief generation.

Matrix, Formula Trace, snapshot Boardroom/Brief, cited Evidence, and the source PDF remain available in the read-only Golden replay. No provider call is made by that replay.

## Future live API configuration

Only after a public backend is separately authorized and deployed, set `NEXT_PUBLIC_CAUSORA_API_BASE_URL` to its public HTTPS origin at build time and configure an exact CORS allowlist with required exposed response headers. Never use a visitor-localhost URL, never put private keys in `NEXT_PUBLIC_*` variables, and keep the backend's review, policy, numeric, budget, and release gates authoritative.

## Day 5 verification

- `tests/golden-bootstrap.test.mjs`: empty/corrupt cache falls back to same-origin verified Golden; valid cache is accepted; tampered/off-origin assets are rejected.
- `tests/golden-health.test.mjs`: 2.5-second timeout behavior and static-only no-request state.
- `tests/static-server.test.mjs`: production static assets, PDF.js worker MIME, normal proxy behavior, and static-only direct-route blocking without contacting an upstream.
- `../verification/day5_public_preview_acceptance.py`: fresh-context public-preview browser acceptance; set `CAUSORA_PREVIEW_URL` to an HTTPS URL.
