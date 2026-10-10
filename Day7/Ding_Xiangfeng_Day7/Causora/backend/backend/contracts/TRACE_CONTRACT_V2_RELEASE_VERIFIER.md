# Matrix + Formula Trace v2 release record verifier

The built-in verifier is `app.release_verifiers:verify_trace_contract_release`. It is invoked only after the reviewed bundle and policy gates pass, and it fails closed unless all configured artifacts and confirmations match.

## Required environment and record

Set the five paths in `.env.example`:

1. `CAUSORA_TRACE_CONTRACT_V2_RELEASE_RECORD`
2. `CAUSORA_COMMON_API_CONTRACT_PATH`
3. `CAUSORA_TYPESCRIPT_V2_TYPES_PATH`
4. `CAUSORA_FRONTEND_V2_VALIDATOR_PATH`
5. optional explicit verifier override, normally `app.release_verifiers:verify_trace_contract_release`

The JSON record must use:

```json
{
  "kind": "causora.trace-contract-release-record.v1",
  "status": "released",
  "schemaVersion": "causora.contract.v2",
  "traceSchemaVersion": "causora.formula-trace.v1",
  "contractApprovalReference": "immutable-team-reference",
  "artifacts": {
    "backendJsonSchema": "<sha256>",
    "pythonPydanticModel": "<sha256>",
    "commonApiContract": "<sha256>",
    "typescriptTypes": "<sha256>",
    "frontendValidator": "<sha256>"
  },
  "approvals": ["one approved entry for each of simulation_owner, frontend_owner, review_owner"]
}
```

The verifier hashes the local backend schema/model and all configured shared/frontend artifacts, then requires an exact match to the record. A bare `approved` field, an environment boolean or a backend-only schema file cannot unlock v2.

## Runtime outcomes

| Condition | Result |
| --- | --- |
| invalid v1 request | v1 `422 validation_error` |
| review/policy unavailable | v1 `503` with `missingReasons` |
| release record/artifact hash mismatch | v1 `503 trace_contract_unconfirmed` |
| all gates and engine pass | v2 `200` with Matrix + Delta + Selection + 9 Formula Traces |

The successful response is validated by `app.contracts_v2.ApiSuccessV2`, whose JSON Schema is `causora.contract.v2.schema.json`.
