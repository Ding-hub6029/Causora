# Independent Oracle Controls

`independent_oracle.py` is a deliberately stand-alone Python `Decimal` implementation of the Day 5 public arithmetic semantics. It **does not import** `simulation_day1`, `simulation_day2`, `simulation_day3`, NumPy, FastAPI, or a Causora Pydantic model.

## Current review status

The six inputs and expected labels are executable technical controls, but their source status is currently **`PENDING_HUMAN_REVIEW`**. No package file claims a completed human attestation. A real independent reviewer must complete `HUMAN_REVIEW_RECORD.template.md`, save it as `HUMAN_REVIEW_RECORD.md`, and record the package/control hashes and per-case outcome before the controls may be described as manually reviewed.

## What it tests

- five-line TCO arithmetic and explicit half-even whole-USD rounding;
- renewal-premium and termination-fee conditional treatment;
- `Revenue = 0` yields `INVALID_REVENUE_ZERO`, never a fabricated denominator;
- nearest-rank P90: `ceil(0.90 × N)`;
- deterministic constraint screening and no-feasible handling.

Run it from the project root:

```bash
python evaluation/oracle/independent_oracle.py \
  --input evaluation/oracle/frozen_control_cases.json \
  --output verification/day5/independent_oracle_result.json
```

## What it does not prove

This is not a duplicate 104-week stochastic engine and does not claim to independently regenerate Monte Carlo paths. The simulation engine is separately tested for its stochastic calculations, source hashes, trace identities, and seed reproducibility. The oracle is independent specifically so an arithmetic/selection error in the engine is not also treated as its own expected answer.

The captured Golden record may be audited for public-envelope reconciliation, but a Golden audit is labelled as an audit of a prior reviewed capture—not a newly computed stochastic oracle result.
