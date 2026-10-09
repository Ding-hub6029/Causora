# Formal review format: compatible with Jinzhu, no approval performed

This development revision **does not** complete the eleven human sign-offs. The current `data/human_review_request.json` remains six pending evidence decisions plus five pending assumption decisions, with an empty reviewer name and timestamp. The AI candidate is not a human-approved dataset.

## Common future formal input

Retain the original Wang Day2 `evidence_day2` workflow used by Jinzhu. Its verified output is a directory containing `bundle_manifest.json`, `jinzhu_contract_input.json`, `approved_review.json`, `review_receipt.json`, `review_scope.json`, `dataset_success.json`, and the original evidence response files. Jinzhu can continue reading this exact format. Wang Day3 now accepts it too, provided the combined source root is explicit and the **original** verifier passes.

Use `scripts/bootstrap_dev_workspace.py` to assemble the original code and sources without overlaying either owner's project. For later *real* human review, create a fresh canonical pending form from those exact current sources:

```bash
python -m evidence_day2.cli preprocess --project-root PATH_TO_COMBINED_ROOT --out NEW_PENDING_DIRECTORY
```

Run that command from the combined root. The original form has different decision/acknowledgement fields and a source/code-bound scope. Do not copy the newer AI-candidate form into it, change pending to approved automatically, reuse an old scope, or fabricate a reviewer. The genuine responsible reviewer must independently check all six clauses and all five assumptions. Any real-world/policy approval remains outside an automatic synthetic source match.

After genuine completion, the original Day2 controlled promotion/verifier workflow can publish its normal bundle. This has **not** been executed for this delivery.

## Direct Wang consumption

```python
from agent_day3.projections import verify_human_review_bundle

dataset = verify_human_review_bundle(
    original_verified_day2_bundle,
    legacy_project_root=combined_source_root,
)
```

The original source/scope/code/DTO/file-hash verifier is run in an isolated Python process. The handoff's contract/dataVersion must agree with `dataset_success.json`. The receipt must cover exactly six evidence IDs and five assumptions. Missing/pending/stale or edited bundles are rejected.

## Optional internal re-wrapping

If a backend integration already consumes the previous Wang Day3 three-file gate, it can re-wrap an **already verified** original bundle without re-signing or changing dataVersion:

```bash
python -m agent_day3.dev_cli convert-verified-review \
  --jinzhu-root PATH_TO_COMBINED_ROOT \
  --bundle ORIGINAL_VERIFIED_DAY2_DIRECTORY \
  --out NEW_COMPATIBILITY_DIRECTORY
```

The compatibility directory contains `dataset_success.json`, `review_scope.json`, `human_receipt.json` and a `legacy_provenance.json` note retaining the original receipt. The derived receipt preserves the original reviewer and timestamp. It is a wrapper of a supplied attestation, not a new attestation or authenticated identity. Pending data cannot be converted. The converter positive wrapper test uses a clearly named verifier test double in a temporary unit-test directory. It is **not** evidence that a real approved bundle was supplied.

The current development outputs deliberately use `development_manifest.json` and not `bundle_manifest.json`/`jinzhu_contract_input.json`, preventing accidental inclusion in the formal source path. No `ready` public DatasetSuccess or signed receipt is produced by development computation.
