# Day 5 Package Verification Record

**Date:** 2026-10-08  
**Owner:** Ding Xiangfeng  
**Active baseline:** integrated `Ding_Xiangfeng_Day4.zip` from the user's `Hackathon.zip`; baseline SHA-256 `bbef5a19a2d2062d4d50b67c6e3f020a9f90f9da86195d66b9c803bc1b23c59f`.  
**Package-level status:** frontend technical staging verified; genuine user test and team G5 remain pending.

## Environment and commands

- Node.js: `v22.13.0`; npm: `10.9.2`.
- `npm ci`: exit 0 from the committed lockfile (`verification/logs/day5_npm_ci.log`). Full audit exits 1 with 5 high-severity development/toolchain findings: `@next/eslint-plugin-next`, `braces`, `eslint-config-next`, `fast-glob`, and `micromatch` (`verification/logs/day5_npm_audit_full.json`). npm proposes `eslint-config-next@14.2.35` as a semver-major fix; that potentially breaking change was not force-applied.
- `npm audit --omit=dev`: exit 0; 0 production dependency vulnerabilities (`verification/logs/day5_npm_audit_production.json`). The full development-inclusive tree warning is disclosed and not hidden.
- `npm run check`: exit 0 (`verification/logs/day5_frontend_quality.log`). TypeScript, ESLint (`--max-warnings=0`), all 55 frontend tests, static production build, and 3 production server tests pass.
- `NEXT_PUBLIC_CAUSORA_STATIC_ONLY=true npm run build`: static-only export; final `frontend/out/` built successfully. Reproducible log: `verification/logs/day5_static_bundle_build.log`.
- `node scripts/verify-golden-e2e.mjs`: production validator checks the frozen Golden record without provider calls. The acceptance browser additionally revalidated the bundled record in an empty browser context.

## Public preview evidence

- HTTPS preview: <https://4173-i1t66nnenc24dtd3xsye3-aa4a5cab.sg2.manus.computer> (temporary Sandbox service, not a permanent deployment).
- Browser script: `verification/day5_public_preview_acceptance.py`.
- Browser JSON: `verification/g5-public-preview/day5_public_preview_acceptance.json`.
- The fresh Chromium context began with zero `localStorage` entries, opened the bundled full Golden, remained read-only, and refreshed/reloaded from the site bundle.
- Final public acceptance run: **11/11 checks PASS**. It covers HTTPS/static-only state; fresh-browser Golden; Matrix no-false-Live; cached Boardroom no provider claim; stored-choice provenance/read-only; Evidence PDF worker and quote highlight; four responsive widths; refresh without storage; no page-origin backend requests; browser console; and direct static-only `/health` and `/api/simulate` route blocking.
- Measured values: no page-origin `/health` or `/api/*` requests; direct server-only probes return HTTP 503 with `backend_not_configured`; worker is `text/javascript`; PDF is `application/pdf`; the rendered PDF canvas is nonzero and the cited quote has one highlight overlay; widths 1440, 1280, 768, and 390 px have no horizontal overflow; no console/page errors.
- The 5 public browser screenshots are retained under `verification/g5-public-preview/`.
- The bundled Golden asset, original frozen record, and production `out/` copy share raw SHA-256 `14ba108319cb8cbbdec940eb19658aecd027a1ed802266917cc5ffaff6d0bfdf`.

## Known exclusions and honest blockers

- No public API backend is configured. The public preview therefore does not verify live Simulation, live Evidence lookup, live Boardroom/Critic generation, public CORS, public rate limiting, or real provider usage.
- The frontend automated tests cover timeout/abort and AI/provider-error classification/preservation. A live delayed-server repeated-request/late-response stress run was not performed on the static-only public stage.
- No human participants have completed Round 2. Do not claim a participant feedback-driven fix, user-validation pass, or Day5 full sign-off until genuine responses and retest evidence are collected.
- Deng Jinzhu's and Wang Hao's Day 5 work, team G5, and all human/policy/release gates remain **PENDING**.

## Integrity inventory

The packaging preflight found no secret-like token values, no real `.env` configuration, and no project symlink outside excluded dependency caches; only documented `.example` environment templates remain. All 31 files under `release/` and `verification/g4-final/` are byte-identical to the sole Day 4 baseline. Existing `release-pending/` records remain untouched.

`DAY5_MANIFEST.sha256` covers the current delivered project files and verification assets, excluding itself to avoid a self-referential hash. The final ZIP's overall SHA-256 is reported outside the archive with its owner-only Handoff receipt. The inherited Day4 `MANIFEST.sha256` remains a historical baseline record, not the current Day5 integrity inventory.
