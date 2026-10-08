# Wang Hao Day 3 — final validation report

Revision validated on **2026-10-07 (+08:00)**, against the supplied Ding Day 3 fixed package. This is an owner-module validation report, **not** the team's G3/G4/E2E acceptance record.

## Environment

- Python **3.12.3**, fresh venv installation from `requirements-tested.txt`.
- Node **22.13.0**, npm **10.9.2**, TypeScript **5.9.3** for an independent shared-contract type check only.
- Ubuntu Sandbox. C-locale tests explicitly disabled Python UTF-8 mode and locale coercion; file operations use explicit UTF-8.

## Actual completed checks

| Check | Observed result | Meaning |
| --- | --- | --- |
| Complete owner-module pytest suite | **39 passed** | Role module, Critic corpus/harness and evidence-review regressions. |
| Same suite under C locale | **39 passed** | Non-default file decoding did not break the final implementation/tests. |
| Latest code from newly extracted candidate ZIP in separately installed fresh venv | **39 passed** | No dependency on earlier Wang/Jinzhu ZIPs or frontend working directory. |
| Latest extracted code under C locale | **39 passed** | Same fresh code and installed dependency environment. |
| `npm ci` / `npm run test:contract` in extracted directory | **Passed** | Actual emitted SimulationResult, reviewed contract/evidence/variables and AgentOutput samples satisfy the unchanged TypeScript contract. No website built. |
| Python `compileall` | **Passed** | Owner source/helpers/scripts compile. |
| Three scenario offline smokes | **ALL_READY**, all `MOCK` | Baseline, demand-drop and lead-stress; deterministic test-double commentary only. |
| Optional actual model smoke on LOCAL_MOCK | Three schema-valid role drafts | Live provider connectivity, not genuine calculation/content evaluation; see content limitations below. |
| Evidence quote verification | **6 matched**, genuine p.4 PDF locators | Quote matching does not establish real supplier facts or human approval. |
| Synthetic review ledger | **11 reviewed_synthetic** | Six contract items + five explicit demo assumptions. **0 human-approved items.** |
| Reproduce reviewed-data generator | Exact JSON equality to bundled data | Inputs and output scope are stable; no simulation/Brief generated. |
| Baseline source immutability | Byte-identical shared API/types, frozen JSON and all bundled demo input files | No frontend edits or mock-metric rewrites. |
| ZIP CRC / file manifest | Verified by packaging / integrity utility | Excludes caches, venvs, node_modules and frontend/site artifacts; runtime credential value scan performed. |

Latest fresh test logs are `fresh_tests_normal.log` and `fresh_tests_c_locale.log`; original-directory final logs are `tests_normal.log` and `tests_c_locale.log`. `typescript_contract_check.log`, `fresh_typescript_contract_check.log`, and `baseline_audit.json` record other checks.

## Regression coverage

- Strict role field isolation; provider payload inspection and unknown-field/injection-canary rejection.
- All three role tasks start before any wait; barrier test, isolated timeout/provider exception/internal cancellation and propagated caller cancellation.
- Invalid digits/template/ref/option output rejected; option-specific refs bound to declared IDs; provider schema/payload mutation cannot expand allowlists.
- ISO dates, finite values, bbox tuples, exact breakdown sums, fixed option meanings, complete scenario cells, allocation ratios and derived renewal state.
- Hash-pinned local mock; immutable full-input references; direct snapshot/scenario edits; frozen mock ID relabelling rejection.
- Missing/false/current-scope human receipt, exact six IDs/five assumptions, missing/failing/unawaited/mutating verifier; no-feasible path without provider calls.
- Internal metadata assembled from unchanged shared request/result objects without adding fields to SimulationResult.
- Critic split sizes, mixed opaque IDs, no exact complete dev/held-out input duplication, model loader label rejection, independent loader module, digest/duplicate/missing-case rejection and explicit failed-call scoring semantics.
- Evidence/assumption typed values, PDF quote coordinates, source tampering, incomplete review findings, deterministic data and no overwrite/no signature/no simulation promotion.

The tiny `jsonschema` and TypeScript checks do not replace runtime cross-field validators. The gate unit tests use explicitly synthetic test-double receipts/results: they are not real confirmations or computations.

## Model smoke is not a content gate

The final optional provider smoke was structurally successful, but manual inspection found an unsupported COO supply/demand alignment inference, weak comparative reference coverage and a spelled-out numerical word in CFO prose. These are retained/documented in `MODEL_SMOKE_REVIEW.md`. One actual preceding partial provider output is also retained.

`ALL_READY` means available, schema-valid **drafts**, not truth or decision readiness. The stronger language-aware Numeric Guardrail and Critic/content review remain later tasks; no Critic recall/precision/false-positive result is claimed.

## Remaining external dependencies

1. Jinzhu's actual Day 3 simulation and independently checking backend verifier.
2. Genuine human confirmation for all six evidence items and five assumptions against the new review scope. AI review cannot sign Wang Hao's name or prove real notice correspondence.
3. Independently reviewed Critic labels and later locked model predictions before any official evaluation score.
4. Ding's final integration, later Critic/Synthesizer/Brief/guardrail and team acceptance tests.

No public interface field was added/changed; the internal assembler constructs its own metadata from existing shared records. The deterministic-zero-run wording ambiguity is documented but the common contract is unchanged. No real simulation, human attestation, final recommendation, approval, frontend rebuild or full-site package is certified here.
