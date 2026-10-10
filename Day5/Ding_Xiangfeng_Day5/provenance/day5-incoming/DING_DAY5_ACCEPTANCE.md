# Ding Xiangfeng — Day 5 Acceptance

**Status: PARTIAL — frontend technical staging checks PASS; genuine second-user validation and feedback-driven change are still pending.**

**Owner:** Ding Xiangfeng  
**Scope:** Ding's frontend, static public preview, and evidence-backed integration checks only. Team G5 and teammate-owned work are not included in this personal result.

## Baseline and boundaries

- Sole active baseline: the integrated `Day4/Ding_Xiangfeng_Day4.zip` nested in the user's `Hackathon.zip` (baseline SHA-256: `bbef5a19a2d2062d4d50b67c6e3f020a9f90f9da86195d66b9c803bc1b23c59f`). Earlier source archives and standalone teammate ZIPs were not used as development baselines.
- The approved 15 assumptions, Matrix + Trace v2 schema, IDs/units, release records, backend simulation algorithms, teammate AI pipeline, and approval gates were not changed.
- No API/provider key was read into the package, no paid provider request was made, and no human or release decision was recorded.

## Technical results

| Check | Result | Evidence |
|---|---|---|
| Locked dependency install | PASS (`npm ci`, exit 0) | `verification/logs/day5_npm_ci.log` |
| TypeScript typecheck | PASS | `verification/logs/day5_frontend_quality.log` |
| ESLint | PASS, `--max-warnings=0` | Same log |
| Frontend automated tests | PASS, 55/55 | Same log; includes timeout abort, AI/provider-failure preservation, run identity, and strict Golden/evidence validation cases |
| Production server tests | PASS, 3/3 after the static-only route gate addition | Same log; validates PDF.js worker MIME, normal proxy behavior, and that static-only `/health` and `/api/*` never reach an upstream backend |
| Production build | PASS | Same log; static export generated successfully |
| Production-only npm audit | PASS, 0 vulnerabilities | `verification/logs/day5_npm_audit_production.json` |
| Full dependency-tree audit | WARNING: full audit reports 5 high-severity development/toolchain findings (`@next/eslint-plugin-next`, `braces`, `eslint-config-next`, `fast-glob`, `micromatch`). Production-only audit is clean. npm proposes `eslint-config-next@14.2.35` as a semver-major fix; it was not force-applied. | `verification/logs/day5_npm_audit_full.json`, `day5_npm_audit_full.stderr`, and production audit JSON |
| Fresh-browser Golden replay | PASS | `verification/g5-public-preview/day5_public_preview_acceptance.json` |
| Public Evidence/PDF click-through | PASS | Worker: HTTP 200, `text/javascript`; PDF: HTTP 200, `application/pdf`; page canvas 918×1188; one locator highlight overlay. Screenshot: `verification/g5-public-preview/day5-staging-evidence-pdf-1440x1000.png` |
| Responsive layout | PASS, no horizontal overflow at 1440×1000, 1280×900, 768×1024, or 390×844 | Browser acceptance JSON and screenshots in `verification/g5-public-preview/` |
| Public static-only route isolation | PASS | Static UI issued zero API/health calls; direct `/health` and `/api/simulate` probes return 503 `backend_not_configured`; the server-side static-only test confirms no upstream request |
| Browser console | PASS, no console/page errors | Browser acceptance JSON |

The public browser run used a fresh context with `localStorage.length === 0`. The complete frozen Golden source, the site-bundled asset, and the production `out/` copy were byte-identical (raw SHA-256 `14ba108319cb8cbbdec940eb19658aecd027a1ed802266917cc5ffaff6d0bfdf`). The production validator revalidated the replay before display. Its stored `Rejected` value remains identified as an automated G4 browser-test artifact, not a human, business, or team rejection.

A browser-driven QA review also found and fixed a provenance mismatch: cached ProofEngine evidence/policy cards now use the revalidated Golden records rather than Day 2 demo fixtures. This is an owner-side technical QA correction; it is **not** a participant-feedback-driven fix.

## Public staging

**Temporary HTTPS preview:** <https://4173-i1t66nnenc24dtd3xsye3-aa4a5cab.sg2.manus.computer>

The preview is intentionally static-only and temporary; it is not a persistent Vercel deployment or production service. There is no public backend. Therefore these live functions are unavailable on the preview until a public API backend is separately authorized and deployed:

- live Monte Carlo `POST /api/simulate`;
- live Evidence lookup `GET /api/evidence/{evidence_id}`;
- new live Boardroom/Critic/Brief generation `POST /api/boardroom`.

The bundled Golden Matrix, Formula Trace, Boardroom/Brief snapshot, cited Evidence, and PDF remain read-only and available. Static-only `/health` and `/api/*` paths fail closed with an explicit 503 and never proxy to localhost.

## Not completed / not claimed

1. **Second genuine user test:** no participant sessions or responses were available. `USER_TEST_ROUND2.md` is ready to share. The requested 2–3-user test, verbatim feedback capture, and at least one feedback-driven high-impact code change remain **WAITING FOR USER TESTERS**. Personal Day 5 cannot be signed fully complete before those inputs arrive.
2. **Live backend and provider validation:** not performed on public staging because no public backend is configured. Automated frontend tests exercise health timeout/abort and provider/backend error preservation, but public live Simulation, live AI, live CORS/rate-limit behavior, and real provider usage were not exercised.
3. **Repeated-request/late-response stress:** not separately run against a live or delayed backend during this static-only acceptance. Do not interpret source-level cancellation guards as a completed live race test.
4. **Team G5:** Deng Jinzhu's benchmark/oracle and Wang Hao's held-out Critic, prompt-injection, and negative-evidence work remain unstarted/PENDING and are not Ding defects or Ding passes.
5. Existing team review, model-policy, human-choice, and release gates remain exactly as supplied; no pending gate was promoted.

## Evidence index

- Browser result and API/MIME details: `verification/g5-public-preview/day5_public_preview_acceptance.json`
- Cold-start state: `verification/g5-public-preview/day5-staging-cold-start-1440x1000.png`
- Matrix and ProofEngine provenance: `verification/g5-public-preview/day5-staging-matrix-1440x1000.png`
- Evidence PDF and quote highlight: `verification/g5-public-preview/day5-staging-evidence-pdf-1440x1000.png`
- Mobile Brief: `verification/g5-public-preview/day5-staging-brief-390x844.png`
- Reproducible browser script: `verification/day5_public_preview_acceptance.py`
- Current package inventory: `DAY5_MANIFEST.sha256`
