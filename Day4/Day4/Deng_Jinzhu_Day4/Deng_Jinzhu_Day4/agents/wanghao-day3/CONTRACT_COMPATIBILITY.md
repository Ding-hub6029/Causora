# Historical component document

This incoming document is preserved as history and is superseded by the root README.md and DAY4_FINAL_ACCEPTANCE.md. Its original bytes are retained under provenance/historical-integrated-reports/.

---

# Contract compatibility — latest Day3 development adapter

## Versions consumed, not changed

- Request: existing `causora.contract.v1`, `POST /api/simulate`.
- Explicit unreviewed success: supplied `causora.contract.v2` with simulation/deltas/selections/traces/executionContext.
- Pending/error response: v1 422/503; never a mock success fallback.
- Wang output: private `CAUSORA_WANG_DAY3_MC_DEV_ANALYSIS_V1` sidecar, not public BoardroomResponse.

The original Ding Day3 `API_CONTRACT.md` and `lib/contracts.ts` are preserved under `reference/`; no production frontend/shared file was changed. `reference/jinzhu_day3/` contains byte-for-byte copies of the **supplied** v1 request/v2 response JSON schemas and v2 TypeScript candidate. Consuming the already supplied v2 development response does **not** create its formal three-owner release or update Ding's v1 client silently.

**No new public field/endpoint or backend core change is proposed or applied by Wang.** A future public DTO migration must still be circulated with exact old/new fields and tests to all three owners before shared files and Ding's runtime validator change together.

## Statistical fidelity

Real MC fields retain their exact meaning and identity: expectedTco, stockoutProbability, serviceLevel, cashOutflowP90 and existing deltas. Probability uses trial counts; P90 uses the specified nearest-rank ceil(0.90N), cash line inclusion and same MC denominator. Component displays reconcile with Decimal raw-mean/difference metadata. The sample path is a single realised trial, not an aggregate oracle.

The latest provided backend computes 1,000 runs. Old deterministic `stockoutOccurred`/`cashOutflowUsd` values are never accepted as probability/P90, and old v1 mock/deterministic outputs are rejected by the MC path. Hashes preserve raw JSON numeric spelling, while legal option shares written as JSON integers are accepted semantically.

## Development and formal gate separation

Development requires explicit opt-in and exact unreviewed executionContext/header markers. DecisionReady stays false at both response and role output. Selections are checked only for interface/numeric consistency and never sent to role providers or emitted as a decision.

Native review pair verification uses the original latest backend verifier and actual source/hash checks. Pending records fail. The older v1 formal gate remains guarded and cannot manufacture its missing DatasetSuccess/evidence snapshot from a native contract-only record. Genuine human-reviewed v2 production role acceptance is not claimed by this revision.

The standalone TypeScript check validates retained v1 examples against unchanged Ding types; it is **not** evidence that Ding now accepts v2 or that a website has been built. Actual current MC validation uses the original v2 JSON schema and independent semantic checks. Final UI/site/three-way deployment remains Ding's responsibility.
