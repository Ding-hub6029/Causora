# Day 5 Shared Benchmark

This folder defines one strict comparison for **Causora**, **plain LLM**, and **LLM + local code**. Every method receives the same answer-free fixture in `shared_control_inputs.json`. The scorer-only expected labels are in `expected_labels.json`; they must never be sent to an external model or embedded in a provider capture.

## Current no-cost result

Run from the project root:

```bash
python evaluation/benchmark/run_offline_benchmark.py \
  --output verification/day5/benchmark_shared_score.json
```

The command makes **zero network/provider calls**. It:

1. executes Causora production rounding, P90, and selection helpers on all six shared controls;
2. independently validates/scans existing external captures, if any;
3. scores exact answer accuracy, control-evidence coverage, poison-pill recognition, and reproducibility identity; and
4. keeps the historic reviewed-Golden audit separate from the three-method comparison.

A `COMPLETED` external capture is **not** a pass. It is only scored after strict structural and identity validation. Missing, duplicate, or unknown cases; malformed answers; incorrect input/prompt hashes; absent reproducibility evidence; and secret markers are rejected before scoring. A complete but wrong answer stays `COMPLETED_BUT_NOT_FULLY_CORRECT`.

## Current completion status

Causora is locally scored on the same six controls. Plain LLM and LLM + local code remain `NOT_RUN_NO_PAID_AUTHORIZATION` until an operator has explicit paid-dispatch authorization, a valid model configuration, and persistent budget protection. This package does not manufacture their results.

See [Benchmark Dispatch and Import Guide](BENCHMARK_DISPATCH_AND_IMPORT_GUIDE.md) for the required authorization, redaction, capture, code-execution, import, and scoring steps.
`prepare_dispatch_bundle.py` writes model-facing material with no provider call; `validate_capture.py` validates and scores one redacted capture locally before it is imported.

## Historic Golden boundary

The old reviewed Golden capture is still reconciled for matrix/trace/selection integrity. It is labelled `HISTORIC_CAPTURED_GOLDEN_AUDIT_ONLY`; it is **not** a shared-control score, new Monte Carlo run, provider call, public deployment check, or replacement for external-method results.
