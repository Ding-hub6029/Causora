# Causora Ding Day3 — Fix Verification Report

**Result:** The source and production checks passed for this package revision. This does **not** claim a live backend E2E, manual browser review, or team G3 sign-off.

## Fixes verified

- Matrix scenario browsing and option inspection now use independent view state. They do not change request assumptions or clear a still-current validated live response. Editing demand, risk, or budget assumptions continues to invalidate stale results.
- Formula Trace and the proof header use the scenario currently being inspected in the Matrix.
- Live winner styling is derived from the validated per-scenario `selections`. A response tone hint cannot make a non-winner appear selected; saved Day2 mock tone remains unchanged.
- `MANIFEST.sha256` was regenerated after the final source/doc edits and covers the delivered source package (excluding the manifest itself and generated build/dependency directories).

## Test environment

- Execution environment: Manus Sandbox (Linux)
- Node.js: `v22.13.0` (`.nvmrc` requests major version 22)
- npm: `10.9.2`
- Next.js: `15.5.27`
- Dependency installation: `npm ci --no-audit --no-fund` succeeded from `package-lock.json`

## Results

| Check | Result | Details |
| --- | --- | --- |
| `npm run typecheck` | **PASS** | `tsc --noEmit`, exit code 0 |
| `npm run lint` | **PASS** | `eslint . --max-warnings=0`, exit code 0 and no warnings |
| `npm test` | **PASS** | 31 tests passed; 0 failed, 0 skipped. Includes the new matrix-retention and selection-derived-tone regressions. |
| `npm run build` | **PASS** | Next.js production build and static export completed successfully. |
| `npm run test:production` | **PASS** | 1 production-preview test passed; response content types and source-file privacy verified. |
| `npm run check` | **PASS** | Complete chain above exited with code 0. |

The source-test and production-preview totals are **32 passed, 0 failed**. The final source ZIP omits generated `node_modules/`, `.next/`, and `out/` directories; run `npm ci` and `npm run check` to reproduce the verification.

## Not verified / not claimed

1. **Real `POST /api/simulate` E2E is pending.** No reviewed Day3 backend endpoint was available in this test run. The client tests use an injected test-only response fixture; this is not a real Monte Carlo result or backend acceptance.
2. **Manual browser/human visual review was not performed.** The available verification is automated type/lint/test/build and a production static-server test.
3. **Team G3 sign-off is pending** the actual backend integration and team review.
4. **Weekly formula drivers are not available in the shared v1 DTO.** Formula Trace shows the returned aggregate components and states this limit; it does not invent weekly holding/stockout detail.
5. **No dependency security audit was run in this verification.** Installation used `--no-audit`; this report makes no dependency security claim.
6. **No deployment, public release, supplier action, or approval submission was performed.**

## Reproduce

From the source ZIP root:

```bash
npm ci
npm run check
```
