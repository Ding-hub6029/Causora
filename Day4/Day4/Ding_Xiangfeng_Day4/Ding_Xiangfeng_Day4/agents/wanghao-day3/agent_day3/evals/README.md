# Critic development and held-out preparation

**Day 3 deliverable, not measured Critic performance.** The PDF p.22 asks for preparation; Critic implementation is Day 4 and an actual held-out evaluation is Day 5. No model predictions, recall or precision from a real Critic run are claimed in this archive.

| File | Size | Authorized use |
| --- | --- | --- |
| `critic_dev.jsonl` | 12: 8 faulty + 4 clean | Development/prompt tuning; includes draft labels. |
| `critic_heldout_inputs.jsonl` | 30: 20 faulty + 10 clean | Input-only frozen cases for a later locked model runner. |
| `critic_heldout_labels.jsonl` | 30 digest-bound references | Offline scoring only; never retrieved or inserted into a model prompt. |
| `build_fixtures.py` | Deterministic generator | Auditable source, **contains expected labels**; evaluator-only, not a model-runner dependency or context. |
| `scoring.py` | Loader and offline scorer | `prompt_payload()` admits only input records; formal scoring refuses unreviewed draft labels. |
| `test_corpus.py` | Infrastructure tests | No model performance measurement; synthetic predictions exercise scoring arithmetic only. |

## Improvements over the previous handoff

- Opaque `h001`-style IDs, no `fault`/`clean` identifiers, and a fixed mixed order: IDs and file ordering no longer directly disclose the label.
- Explicit scenario assignment. No expected rationale is used to heuristically build model facts.
- Fact packets include matched mock contract fields, notice dates, forecast basis, fixed option allocations, same-scenario cells, baseline cells and explicit cash/stockout eligibility limits. These remain **Ding's frozen illustrative LOCAL MOCK**, not newly generated simulation output.
- No identical complete inputs are shared between dev and held-out, including clean controls. Taxonomy and business motifs necessarily overlap; exact disjointness is **not proof of semantic independence**.
- Cases about omissions focus on an **explicitly discarded concern in the combined discussion**, rather than penalizing CFO/COO/Risk for their intentionally restricted field access.
- No invented emergency-purchasing mechanism is used to label a mock cash result. Holding aggregates are not attributed solely to contractual causation.

## Layer ownership

This corpus tests **layer C only**: cross-role conflict, material omission or compound interaction. It must not award Critic credit for layer-A arithmetic correction, layer-B quote matching, or layer-D input-security detection. The synthetic/real notice epistemic case checks a cross-source inference, not an altered quote.

The separate role-module leakage and injection-canary unit tests are security/allowlist tests, not Critic scores. In the later standalone Critic runner, **disable Numeric Guardrail and Evidence Validator** and record that configuration; otherwise they may catch faults on Critic's behalf. The offline scorer cannot attest that this actually happened.

## Independent label review still required

Every label is `AUTHOR_DRAFT_NEEDS_INDEPENDENT_REVIEW`. None is an independently reviewed oracle or a true supplier-performance claim. Some ordinal conflicts are easy to verify against the mock, while omission/compound materiality is a human judgment. An independent reviewer should assess and, if needed, revise/freeze those references before a formal score. Do not upgrade labels by merely changing `labelStatus` text.

The generator and labels are shipped for team audit, so this is not a secured benchmark. Give the model runner access only to the input file and a label-free runner; keep generator, dev labels, held-out labels and raw reviewer notes out of its filesystem/tool retrieval. Use evaluator-only access outside the model process. If a held-out case has been used in prompt tuning, retire it from final scoring or clearly report contamination.

## Later evaluation protocol

1. Tune using dev only, then freeze the prompt, provider/model version, timeout and input hashes.
2. Review/freeze references independently and separate evaluator from model runner.
3. Load only `record['input']` using `prompt_payload(record)`; no case label/category/reference reason enters the prompt. Case ID and SHA are harness bookkeeping outside the model message.
4. Run Critic itself without helper validators/guards, log provider failures and save immutable predictions **before** opening labels in the scorer.
5. Each prediction must have exactly `caseId`, `inputSha256`, `status` (`ok|timeout|error`), and `faultDetected` (boolean for ok; null for failure). Report every case, including failures.
6. Score offline and report TP, FP, FN, TN, recall, precision, false-positive count and failed-call count. Faulty timeouts count as FN; clean timeouts are failed controls, not TN. Missing cases, duplicate IDs and digest mismatches are rejected.
7. Do not claim cross-model superiority without actual controlled comparisons. This package does not deploy or evaluate a cross-model Critic.

```bash
python -m agent_day3.evals.build_fixtures
python -m pytest -q agent_day3/evals/test_corpus.py
# Future independently reviewed labels + actual locked predictions only:
python -m agent_day3.evals.scoring --inputs agent_day3/evals/critic_heldout_inputs.jsonl \
  --labels /path/to/reviewed_labels.jsonl --predictions /path/to/locked_predictions.jsonl \
  --output /path/to/new_score.json
```

`--draft-rehearsal` may explicitly exercise draft labels, but outputs are labelled `DRAFT_HARNESS_REHEARSAL_NOT_CRITIC_PERFORMANCE`. Do not present a harness rehearsal as a competition result.
