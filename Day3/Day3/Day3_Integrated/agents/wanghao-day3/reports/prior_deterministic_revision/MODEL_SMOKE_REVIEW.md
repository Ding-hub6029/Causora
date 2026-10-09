# Actual-computation model smoke review

## Scope and provenance

The saved current file `dev_examples/model_proxy_claim_selection_UNREVIEWED.json` is an **actual model-proxy call result on an actually computed deterministic preview**, using the supplied Jinzhu Day1/Day2 engine. Inputs are synthetic demo sources and the explicitly unapproved test policy. The eleven human items remain pending. It is not a production Day3 Monte Carlo calculation or a formal recommendation.

- Model: `gpt-5-mini`. Strict JSON support and reasoning syntax were checked against the live catalog.
- Actual preview ID: `preview-day2-fd1c4e7f3ea4968929f3`.
- Scenario: `demand-drop`.
- Engine source dataVersion: `demo-2026.10.04-v4`.
- Candidate dataVersion: `demo-2026.10.04-v4-wang-ai-review-568c0474a14a`.
- Derived analysis version: `dev-analysis-ce965389ed7234676237`.
- Current saved status: **ALL_READY**. CFO, COO and Risk each `DEV_ONLY`, without failure. `decisionReady=false` and `humanReviewStatus=pending`.

## Provider contract defect found and fixed

The first concurrent attempt returned three `provider_error` results. A diagnostic request established an actual HTTP 400: GPT strict response schemas reject `uniqueItems`. This was an integration defect, not evidence that the analysis was correct or incorrect. The failed artifact is retained as `reports/model_schema_failure_UNREVIEWED.json`.

The unsupported schema keyword was removed. Duplicate claim IDs remain rejected by the local strict Pydantic model, with a regression test. The corrected concurrent attempt completed all three role calls. No failed result was rewritten into success, and there is no silent fallback to mock output.

## What the new content guard does

The model receives only its role-local typed numeric view and a code-generated catalog of verified observations. It can return only:

```text
role / claim_ids / status
```

The model cannot supply narrative, a new option, numerical text, metric values, a recommendation or approval. Code evaluates claim predicates before issuing IDs, then renders English statements and exact numeric bindings from the audited role view. The saved output can be re-rendered against the current catalog. Current additional financial tradeoff predicates are also covered by the offline runner/tests.

The saved COO output selected **procurement exceeds demand** and **lost sales present**. It did not claim supply/demand matched. For the deterministic demand-drop path, D1 purchases are 15,600 from A plus 10,400 from B while realized demand is 22,100. These typed values are preserved in bindings, not authored by the model. The model cannot request the exact-balance claim because its code predicate is false.

The older free-text mode also rejects common English numeric words and common Chinese quantity expressions. That lexical filter is conservative and not exhaustive semantic reasoning. The development selector avoids the original spelling bypass by removing model-authored prose entirely.

## Limits

`ALL_READY` proves successful schema-valid selection and code-backed rendering, not optimal decisions, broad causal correctness, a judge score, real supplier facts, genuine human review, MC probability/P90, or deployment. Templates deliberately avoid unsupported causal or ranking claims. Provider selection may omit useful valid observations. Semantic completeness still needs human/product review.

The prior revision's free-text mock smoke and its known qualitative errors are archived under `reports/prior_revision/`. They are **historical**, not evidence that the revised constrained mode has passed final team acceptance. Critic labels remain author-draft labels requiring independent review and freeze before formal scoring.
