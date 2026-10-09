# Causora Formula Trace v2 — final candidate pending recorded release

This document supersedes the earlier draft narrative. The executable final candidate is:

- Pydantic: `app/contracts_v2.py`
- JSON Schema: `contracts/causora.contract.v2.schema.json`
- TypeScript recommendation: `contracts/causora.contract.v2.ts`
- Full fixture-only example: `examples/fixtures/simulate_response_v2_TEST_FIXTURE_ONLY.json`

## Fixed interface decision

`POST /api/simulate` keeps its `causora.contract.v1` request. Only a verified 200 uses `causora.contract.v2` and returns `data.simulation`, `data.deltas`, `data.selections`, and the required 3 × 3 `data.traces[scenarioId][optionId]`. v1 continues for all malformed/pending/execution-error envelopes.

## Final FormulaTrace additions

Each trace is identity-bound to the matching matrix cell and carries:

1. same simulation/data/formula/scenario/option identifiers.
2. separate review-record, source-contract, policy-configuration and release-record identities.
3. field-level contract evidence. `sourceSha256` identifies source evidence while `reviewRecordSha256` identifies a different review record.
4. all five components with formula, resolvable `inputKeys`, raw mean, displayed integer USD and displayed-minus-raw difference.
5. exact per-cell component/matrix equality, stockout trial count, service quantity count and P90 rank/component inclusion.
6. a 104-week `sampleRunIndex=0` path explicitly marked one realised trial—not an average, expectation or aggregate.

## Required recorded confirmation

The v2 schema shape is ready for Deng, Ding and Wang to confirm, but it is not automatically publicly released. The built-in release verifier requires a three-owner record binding the exact backend JSON Schema/Pydantic, common API contract, TypeScript type and frontend validator hashes. See `CONFIGURATION_AND_VERIFIERS.md` and `contracts/TRACE_CONTRACT_V2_RELEASE_VERIFIER.md`.
