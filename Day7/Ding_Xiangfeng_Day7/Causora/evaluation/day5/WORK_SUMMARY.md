# Wang Hao - Day5 Evaluation Engineering Summary



Author-visible fixtures are AUTHOR_DRAFT_NEEDS_INDEPENDENT_REVIEW and validate loaders/scorers only. Historical Ding 12-dev/30-heldout synthetic material is INELIGIBLE / UNVERIFIED and cannot be reused as a fresh unseen corpus. No independent hidden corpus is supplied here.

load_inputs recursively rejects expected, labels, answer and ground_truth leakage. Labels bind the entire canonical input hash and are scorer-only. Dispatch exports ordered input payloads without caseId, split, source, per-case hashes or labels.

Freeze hashes inputs, labels, prompt, credential-free model configuration, scoring source, corpus identity and independent evidence registry. Any change fails closed. The registry binds evidenceRef, claimId, a nonempty source quote and SUPPORTS/DOES_NOT_SUPPORT. Model self-reported supported flags are forbidden.

Import, seal and score reopen physical capture, provider-audit and stage-validation receipt files by relative path and verify SHA-256. File binding alone does not establish a real external provider call. ACTUAL_CAPTURE scores remain SCORED_EXTERNAL_CAPTURE_UNVERIFIED_NOT_OFFICIAL with officialEligible false. TEST_FIXTURE_ONLY receipts produce validation, not performance. Imported claims of independent approval have no trusted identity root and cannot self-certify official eligibility.

## Shared answer contract

causora_pipeline, plain_llm and llm_plus_code share causora.day5.fair-answer.v1. Required fields: criticVerdict, criticReasons, numericStatements, evidenceCitations and stageStatus. Each numerical statement contains statementId, decimal-string value, precision scale/ROUND_HALF_EVEN and roundingTrapId. Numerical scores compare all of these, not display strings alone.

Old strict-object 0/6 results caused by mismatched field names or trap IDs are not mathematical accuracy of 0%. Historical captures cannot be relabelled into new scores.

## External corpus and execution

An independent supplier must provide inputs.jsonl, scorer-only labels.jsonl with canonical input hashes, prompt.md, credential-free model_config.json, source_corpus_identity.json and evidence_registry.json. Expected labels must be unseen by implementation and model-execution teams and never used for debugging.

Run from the repository root with an environment containing the project dependencies:

```bash
python -m evaluation.day5.cli freeze --inputs /secure/inputs.jsonl --labels /secure/labels.jsonl --prompt /secure/prompt.md --model-config /secure/model_config.json --scoring-source evaluation/day5/core.py --source-corpus /secure/source_corpus_identity.json --evidence-registry /secure/evidence_registry.json --author external-corpus-custodian --output /secure/freeze.json --authorization-status PENDING_SEPARATE_PROVIDER_AUTHORIZATION
python -m evaluation.day5.cli dispatch --freeze /secure/freeze.json --output /secure/model_dispatch.json
python -m evaluation.day5.cli import-actual --freeze /secure/freeze.json --capture /secure/external_actual_capture.json --output /secure/bound_predictions.jsonl
python -m evaluation.day5.cli seal --freeze /secure/freeze.json --predictions /secure/bound_predictions.jsonl --output /secure/prediction_seal.json
python -m evaluation.day5.cli score --freeze /secure/freeze.json --predictions /secure/bound_predictions.jsonl --seal /secure/prediction_seal.json --output /secure/metrics.json
```

External execution occurs between dispatch and import and is not performed by this module. Without actual execution, use pending-metrics and report N/A rather than invent predictions.

## Metrics and failures

- Critic recall: TP/(TP+FN). Faulty-case execution failure becomes FN_EXECUTION_FAILURE.
- False-positive rate: FP/(FP+TN). Clean timeout/error/cancelled attempts are reported separately and are not fabricated TNs.
- Numeric fidelity: validated statements / checked statements. The denominator includes expected obligations and extra actual statements. Missing, unknown, timed-out or incorrectly rounded statements fail.
- Evidence support: registry-supported citations / checked citations. Expected and extra citation/claim obligations are included. Unknown extra claims fail.
- Workflow success: all required stages passed / independently validated attempts. Only physical independent stage-validation receipts establish workflow completion. Model stageStatus alone produces N/A.
- Zero denominators produce NA and null with a reason, not 0% or 100%. Failed attempts remain recorded.

Historical module regression: 18 passed with no provider or network calls. Tests cover registry binding, leakage, JSON failures, hash tampering, self-attestation rejection, extra-obligation denominators, clean failures, model mismatch, stage receipts, portability, post-seal tampering and author-visible corpus ineligibility.


Historical validation: core.py and cli.py compiled, 18 tests passed in 0.16 seconds. New model calls, provider calls, network requests, Critic predictions and real three-method performance scores in that historical offline work were all zero. Historical interpreter: /home/ubuntu/causora_day5/.venv/bin/python. Log: verification/wang-day5/evaluation/day5_evaluation_pytest.log. The independent Day4 answer-free loader remains without a missing agent_day3.evals.scoring dependency. These historical offline boundaries do not deny later separately archived Day6 real calls.
