# Actual model smoke — latest Day3 HTTP Monte Carlo result

This supersedes the old deterministic report, now under `prior_deterministic_revision/`.

## Actual run

- Input: newly requested latest service capture `mc_examples/http_base`, scenario `demand-drop`.
- Simulation ID: `sim-dev-unreviewed-9d1891657ae72d846c4e`.
- DataVersion: `demo-2026.10.04-v4--UNREVIEWED_DEV_ONLY`.
- Actual Monte Carlo runs: 1,000; 104 weeks.
- Model: actual `gpt-5-mini`, catalog support checked at runtime.
- Calls: CFO/COO/Risk created together and run concurrently.
- Saved output: `mc_examples/http_base/analysis_demand-drop_MODEL_PROXY.json`.
- Outcome: **ALL_READY**, three **DEV_ONLY** outputs, no failures, original executionContext preserved and decisionReady=false.

Selected claims were CFO financial metrics binding, COO operations plus noncausal probability/service comparison, and Risk development status plus actual threshold exceedance. Probability and P90 bindings come directly from the new MC response, not the prior deterministic fields.

## Content and isolation

Providers receive only their strict typed role view and a code-verified claim catalog. They may return role/claim_ids/status, not prose, new options, numeric values, approval or recommendations. The renderer re-reads canonical pointers and immutable result/source identities after the provider returns. Output values and English text are code-authored; model selection itself is not a proof of business correctness or optimality.

The new mode does not admit the old unsupported supply/demand matching assertion or a numeric-word workaround. Original lexical guards remain for historical free-text mode but are not claimed to be comprehensive semantic reasoning.

## Limits

The synthetic contract and operating assumptions remain unreviewed. This smoke does not prove causal findings, completeness, an official Critic score, policy approval, contract release or final team acceptance. Current v2 has no revenue/profit fields, so CFO does not invent them. Only the demand-drop scenario was smoke-tested with a live model; all three scenarios and changed-input captures were additionally checked with the explicitly OFFLINE_STUB claim selector.
