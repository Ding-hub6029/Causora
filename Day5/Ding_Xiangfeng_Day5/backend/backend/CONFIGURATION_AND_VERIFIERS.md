# Historical component document

This incoming document is preserved as history and is superseded by the root README.md and DAY4_FINAL_ACCEPTANCE.md. Its original bytes are retained under provenance/historical-integrated-reports/.

---

# Three-input configuration and verifier guide

The service includes executable, file-backed verifiers in `app/release_verifiers.py`. They are intentionally simple recorded confirmations, not a new approval system. They validate file hashes, field coverage and required owner roles; they cannot certify a person's identity or create Wang's review.

## 1. Wang reviewed bundle — owner: Wang Hao

Set `CAUSORA_REVIEW_BUNDLE_DIR` to a directory containing:

```text
reviewed_contract.json
review_record.json
```

`reviewed_contract.json` has `kind: causora.wang.reviewed-contract-bundle.v1`, `datasetId: ds-001`, a distinct `dataVersion`, complete contract fields, `contractSource`, and a `fieldProvenance` record for **every** contract field. Each field entry must carry one evidence ID, source file/hash and review-item ID.

`review_record.json` has `kind: causora.wang.review-record.v1`, `status: reviewed`, reviewer role/id, exactly the six evidence IDs EV-014/019/021/024/027/020 and five assumptions decisionDate/renewalDate/noticeSent/forecastBasis/lockedForecastUnits24m, and canonical SHA-256 bindings to the contract payload and field-provenance map. Confirmed typed values must match the contract; EV-020 confirms the conditional clause exists. Every provenance entry must be reviewed and carry its complete `derivedFromReviewItemIds` dependency list from `app/release_verifiers.py:FIELD_PLAN`. Source paths must stay within the backend project and their actual file bytes must match the recorded hashes. Its review-record SHA is kept separately from source SHA in every Trace.

The supplied Wang human confirmation is preserved in `reviewed/wang-2026-10-07/`, with the original Word and its hash. `recordedAtUtc` is the technical transcription time; `humanReviewDate` preserves the date Wang actually supplied. This confirms synthetic demonstration inputs only and does not approve a model policy or v2 release. `python scripts/start_review_gated.py` loads this review while preserving the other gates.

The default `CAUSORA_REVIEW_VERIFIER=app.release_verifiers:verify_reviewed_bundle_record` verifies this structure. Substitute a stronger organization-owned verifier only with the same return fields.

## 2. Team policy — owners: Deng, Ding, Wang

Set both:

```bash
CAUSORA_APPROVED_POLICY_PATH=/absolute/path/team_policy.json
CAUSORA_POLICY_APPROVAL_RECORD_PATH=/absolute/path/policy_approval_record.json
CAUSORA_POLICY_VERIFIER=app.release_verifiers:verify_team_policy_record
```

The policy file must validate as `Day3Policy` and set `TEAM_APPROVED`. The **separate** record must bind the exact policy-file SHA-256, contain all three roles (`simulation_owner`, `frontend_owner`, `review_owner`) with `decision: approved`, and contain every `confirmedTopics` key in `MODEL_POLICY_CONFIRMATIONS.md`. It also supplies an immutable `policyConfigurationId`, which is included in the simulation ID and all Trace run identities.

## 3. Matrix + Trace release — owners: Deng, Ding, Wang

Set:

```bash
CAUSORA_TRACE_CONTRACT_V2_RELEASE_RECORD=/absolute/path/trace_v2_release_record.json
CAUSORA_COMMON_API_CONTRACT_PATH=/absolute/path/API_CONTRACT_V2.md
CAUSORA_TYPESCRIPT_V2_TYPES_PATH=/absolute/path/contracts-v2.ts
CAUSORA_FRONTEND_V2_VALIDATOR_PATH=/absolute/path/simulate-api.ts
CAUSORA_TRACE_CONTRACT_V2_VERIFIER=app.release_verifiers:verify_trace_contract_release
```

The release record binds SHA-256 values for five artifacts: backend JSON Schema, Python Pydantic model, common API contract, TypeScript DTO and frontend validator. It also contains all three owner roles and a `contractApprovalReference`. This prevents a backend-only release while the frontend still rejects v2.

## Failure behavior

| Missing/invalid input | HTTP behavior |
| --- | --- |
| no review bundle | v1 503 `human_review_pending` |
| invalid review bundle/record | v1 503 `review_bundle_not_verified` |
| no policy or policy record | v1 503 `simulation_policy_unapproved` |
| incomplete/mismatched trace release | v1 503 `trace_contract_unconfirmed` |
| verified input cannot calculate | v1 503 `reviewed_simulation_execution_failed`; never mock fallback |

`error.details.missingReasons` and `/health.data.missingReasons` list all currently missing dependencies. Templates are under `config/templates/` and deliberately contain placeholders that fail verification until the real owners complete them.
