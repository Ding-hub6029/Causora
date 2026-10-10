# Dependency security disposition

Audit date: 2026-10-08. Raw results: verification/day5-final/npm-audit-full.json and npm-audit-production.json.

Production dependency audit reports **0 vulnerabilities**. Full development-inclusive audit reports **5 high findings**, related through braces -> micromatch -> fast-glob -> Next ESLint packages. These findings remain visible; no audit suppression or false patched claim is used.

Upstream advisory: https://github.com/advisories/GHSA-vfj7-8cjw-p6xm . The recorded braces advisory has no patched version listed at review time. Review upstream before any future upgrade; a version bump without a patch is not remediation.

The affected brace/glob expansion path is development tooling, not the deployed browser or simulation service. The checked-in ESLint configuration supplies no settings.next.rootDir patterns. tests/toolchain-boundary.test.mjs loads that configuration and the actual Next root-resolution helper, replaces the glob expansion entry with a failing instrumented stub, and verifies deeply braced input remains literal with zero expansion calls. This is evidence for the configured path, not proof that the dependency is safe under every possible future configuration.

Do not lint untrusted directory-pattern overrides, add a glob rootDir setting, or treat public user input as build configuration. Reassess this boundary whenever ESLint configuration or the toolchain changes. Install dependencies only for trusted source development; deploy the built website without development dependencies. Track and apply an actual upstream fix when available.

Residual status: **UNPATCHED DEVELOPMENT DEPENDENCY, scoped configured exposure tested; upstream remediation outstanding**. This is a disclosed limitation, not a fabricated user risk acceptance or an unconditional zero-vulnerability claim.

No new provider key is included or consumed. Existing model budgets, fail-closed approvals, request identity and numeric guards remain unchanged.
