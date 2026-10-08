# Day 3 release blockers and next owner actions

The HTTP service and genuine reviewed-input v2 path are implemented. **Default 503 is a deliberate missing-input result, not a missing-service/code-path result.**

| Owner(s) | Remaining real-world input | Concrete action | Service result until complete |
| --- | --- | --- | --- |
| Wang Hao | Contract review | Supply `reviewed_contract.json` + `review_record.json` with 11+ reviewed items, source-vs-review hashes and field-level evidence | `human_review_pending` / `review_bundle_not_verified` |
| Deng + Ding + Wang | Model policy | Freeze every item in `MODEL_POLICY_CONFIRMATIONS.md`, save approved policy and its three-owner hash-bound record | `simulation_policy_unapproved` |
| Deng + Ding + Wang | v2 interface release | Ding syncs common contract/types/validator; record the five artifact hashes and three approvals | `trace_contract_unconfirmed` |

## Frontend and Boardroom prerequisites

1. Ding integrates `contracts/causora.contract.v2.ts` and the JSON Schema into the shared contract/runtime validator without changing v1 error handling.
2. All owners create the v2 release record only after those frontend artifacts are in place.
3. After a verified v2 200, Boardroom receives its `simulationId` and `dataVersion` only from `data.simulation`; see `VERSION_MIGRATION_AND_BOARDROOM_HANDOFF.md`.

No owner should solve a missing record by placing `approved: true` in a policy or environment variable: each verifier requires separate hash-bound records. The dataset remains synthetic; no resulting response is a real procurement, legal or financial decision.
