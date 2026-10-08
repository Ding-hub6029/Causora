# Historical component document

This incoming document is preserved as history and is superseded by the root README.md and DAY4_FINAL_ACCEPTANCE.md. Its original bytes are retained under provenance/historical-integrated-reports/.

---

# Reproducible checks

Node.js 22 and npm are required. From a clean checkout:

```sh
npm ci
npm run check
```

`npm run check` runs strict TypeScript typecheck, ESLint with zero warnings, Day1/Day2 regression tests, Day3 v1 simulation-client contract tests, the Next.js production build, and the production static-server test. Contract tests use test-only DTO fixtures and make no network request; they are not a live Monte Carlo simulation. The production-server test requires a freshly built `out/` directory.

For offline source iteration, `npm test` does not require a build or backend. Real browser/API regression steps are in `DAY3_INTEGRATION.md`. The saved Day2 handoff and test reports remain historical records; a real endpoint E2E must use a running backend that conforms to `API_CONTRACT.md`.
