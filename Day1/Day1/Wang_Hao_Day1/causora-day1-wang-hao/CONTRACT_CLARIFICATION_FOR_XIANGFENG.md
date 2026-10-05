# Proposed Contract Clarification for Xiangfeng (not applied)

The original **unsigned** v4.1 `API_CONTRACT.md` §1 says production simulation must have a positive `monteCarloRuns` count. That excludes a legitimate deterministic calculation. The original Xiangfeng ZIP has **not** been modified; this note proposes wording for team review, not a unilateral contract change.

> **Proposed replacement:** `monteCarloRuns` is a nonnegative integer counting Monte Carlo draws. A **static Day 1 mock** reports zero draws and is labelled `LOCAL MOCK`. A **computed deterministic** run may also report zero draws, provided the execution provenance, algorithm/formula version, input snapshot, deterministic result validation and computed-vs-mock status are independently established. A **stochastic** run reports its actual positive draw count. Do not infer whether a result was computed from this count alone.

The existing v4.1 `validateMockData` accepts `0` and does not derive mock status from the count. Wang's `scripts/verify_v41.mjs` proves that structural behavior with an **in-memory shape-only** example; it does **not** fabricate a calculated result. If the team later adds a `runMode` or run-provenance field to HTTP DTOs, update `API_CONTRACT.md`, `lib/contracts.ts`, `lib/types.ts`, `lib/validation.ts`, example responses and tests **together**, with versioning as agreed by the integration owner.

## Day 1 acceptance boundary to record

- **Acceptable Day 1 mock:** machine-readable synthetic PDF, source-linked evidence/schema, model route smoke, v4.1-valid labelled mock adapter, and a frontend walkthrough that opens the matching PDF **page**. Wang's internal fields remain `manually_verified:false`, pending matrix/nil recommendation; Xiangfeng's numerical D1 display is explicitly his pre-existing LOCAL MOCK.
- **Later:** individual human review **before** promoting contract terms as verified production BusinessVariables; real deterministic or stochastic calculation with independently checked results; backend/API integration; optional drawing of the stored PDF bbox as a region highlight. No one should claim these are complete today, but they are **not conditions for accepting the Day 1 mock handoff**.
- **Existing UI wording:** “Verified”/local `Approve D1` on static data should be labelled as mock-only to avoid suggesting external approval. The integration owner should record the team's G1 **mock** signoff separately; real-data/live E2E is a distinct future gate.
