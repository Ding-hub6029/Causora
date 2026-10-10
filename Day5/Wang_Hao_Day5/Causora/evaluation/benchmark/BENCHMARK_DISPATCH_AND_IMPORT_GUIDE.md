# Day 5 Shared Benchmark: Dispatch and Import Guide

## Current state

The local runner scores **Causora** on the six shared controls and audits the historic Golden separately. Plain LLM and LLM + local code remain `NOT_RUN_NO_PAID_AUTHORIZATION` until a real operator obtains an explicit paid-dispatch authorization. The runner itself makes zero network calls.

## Before any paid dispatch

The operator must record, outside the source tree:

1. the authorization ID, approved model IDs, maximum number of calls, and maximum USD spend;
2. the frozen package SHA-256 and `shared_control_inputs.json` SHA-256;
3. the exact prompt SHA-256 for each method;
4. the provider account/budget owner and the persistent budget-journal location; and
5. the redaction plan for provider receipts and local code-execution logs.

Do not place an API key, authorization header, raw provider transcript, or private source file in this repository or a benchmark capture.

## Model-facing material

For each method, supply only:

- `shared_control_inputs.json`;
- the corresponding file in `prompts/`; and
- the applicable public rules in the shared input fixture.

Do **not** supply `expected_labels.json`, `frozen_control_cases.json`, the independent oracle, Causora source, or prior Golden data to either external method.

Generate the exact model-facing material without making a provider call:

```bash
python evaluation/benchmark/prepare_dispatch_bundle.py \
  --method plain_llm \
  --output /secure/operator-work/plain_llm_dispatch.md
python evaluation/benchmark/prepare_dispatch_bundle.py \
  --method llm_plus_code \
  --output /secure/operator-work/llm_plus_code_dispatch.md
```

## Capture requirements

Create a redacted capture in `captured/plain_llm.json` or `captured/llm_plus_code.json` using `capture_template.json` as a shape guide. For a `COMPLETED` capture, the strict reader requires:

- every canonical shared `caseId` exactly once, with no unknown or duplicate ID;
- an object answer per case;
- the control evidence reference for every case;
- the observed poison-pill flags;
- exact shared-input and prompt hashes;
- method-specific reproducibility evidence; and
- actual timestamps, model ID, run ID, and a redacted audit reference.

For LLM + local code, record the executed code artifact SHA-256 and execution-log SHA-256. A declaration that code was used is insufficient.

## Validate and score

```bash
python evaluation/benchmark/run_offline_benchmark.py \
  --output verification/day5/benchmark_shared_score.json
```

The command rejects missing result lists, unknown IDs, duplicated IDs, missing cases for `COMPLETED`, wrong input/prompt hashes, malformed values, and secret markers. It does **not** silently accept an external `COMPLETED` status as correctness: it reports exact-answer accuracy, control-evidence coverage, poison-pill recognition, and reproducibility separately.

An operator may validate one redacted capture before placing it under `captured/`:

```bash
python evaluation/benchmark/validate_capture.py \
  --method plain_llm \
  --capture /secure/operator-work/plain_llm.json \
  --output /secure/operator-work/plain_llm_validation.json
```

A complete three-method comparison requires each method to be `COMPLETED_AND_FULLY_CORRECT`. A wrong-but-well-formed completed answer is retained as a scored failure, not upgraded to a pass.

## Historic Golden boundary

The historical Golden audit remains in the result for trace/matrix reconciliation only. It is not counted as the Causora shared-case benchmark score, a new simulation, a public deployment result, or a model call.
