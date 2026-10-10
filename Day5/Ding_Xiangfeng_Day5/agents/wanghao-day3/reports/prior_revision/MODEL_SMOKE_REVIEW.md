# Observed provider smoke — LOCAL MOCK only

**Observed on 2026-10-07 (+08:00), model `gpt-5-mini` through the configured server-side compatible proxy.** Its live catalog was checked before use. The smoke used only the supplied synthetic role projections, never a private real contract. No credentials are in this package.

## Actual results

- Offline runs for baseline, demand-drop and lead-stress produced three schema-valid ordered role drafts, `LOCAL_MOCK / OFFLINE_STUB`, with `decisionReady=false`.
- The final demand-drop provider smoke produced **CFO, COO and Risk with no schema/ref failure**, `state=ALL_READY`, `sourceMode=LOCAL_MOCK`, `providerKind=MODEL_PROXY`, all internal availability `MOCK`, `criticStatus=NOT_IMPLEMENTED_DAY3`, `decisionReady=false`.
- One preceding provider attempt had a CFO `invalid_response`, while COO and Risk completed. That **actual partial result** is retained in `agent_day3/examples/model_proxy_failure_isolation_local_mock.json`; it demonstrates the failure path without inventing a replacement role.
- The initial provider attempt produced an overlong/incomplete-looking narrative; prompt instructions were tightened for brevity and reference coverage. The final sample was regenerated, not edited into a claimed model success.

## What the successful smoke proves

The adapter contacted a real model endpoint on explicitly mock inputs; the three parallel roles returned values that met their schemas, numeric-digit/template restrictions and role/ref allowlists. It does **not** prove a simulation ran, that a real contract was approved, that explanations are mathematically sound, or that Critic/Brief/approval is complete.

## Content findings still requiring later review

The final sample is intentionally preserved as actual output, not a polished decision:

1. **COO unsupported qualitative inference:** it says total supply aligns with demand. In the supplied demand-drop mock, procurement can exceed realised demand because of the fixed commitment and fixed diversified split. A same-scenario allocation comparison is not proof of alignment. A Critic/content check should flag this before any final Brief.
2. **CFO reference coverage:** its prose discusses options broadly, but the selected metric refs concentrate on D0. Refs are role-valid; that does not establish support for every comparative sentence. Later synthesis/critic should demand properly bound evidence for material claims.
3. **Spelled numerical words:** the CFO prose uses “ninety.” The Day 3 parser checks digits/templates, not a full language-aware numeric extraction/binding algorithm. The stronger Day 4 Numeric Guardrail is still required.

These findings are why the module emits **drafts only** and never returns a decision-ready BoardroomResponse. Do not cite schema-valid `ALL_READY` as semantic evaluation, substitute this sample for a real Jinzhu SimulationResult, or publish a Critic precision/recall score from it. The frontend-compatible bundled sample is derived from the deterministic offline stub, clearly labelled as such.
