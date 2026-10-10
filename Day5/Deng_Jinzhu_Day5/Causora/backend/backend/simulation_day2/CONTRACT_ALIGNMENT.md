# Deng Day 2: Historical Shared Contract Alignment

This records earlier team alignment. The current Deng test package contains only Day 1/Day 2 modules and Ding's byte-identical read-only `lib/`, `demo_data/`, `golden/`, `public/demo/`, `API_CONTRACT.md` fixtures. It has no frontend or Wang implementation and performs no team integration. See [ownership](../JINZHU_TESTABLE_README.md).

Sources were the three original Day 1 deliveries, Ding's `Causora_Day2_Ding_Xiangfeng_Improved_v2(1).zip` and Wang's `Causora-WangHao-Day2-ONLY-ReviewPending(1).zip`. Earlier alignment overlaid Deng's simulation modules and Wang's causora_day1/evidence_day2 without replacing Ding's contract, lib, mock, Golden or UI.

| Boundary | Source / check | Conclusion |
| --- | --- | --- |
| Shared request/response | Ding Day 1/2 API_CONTRACT, contracts.ts, types.ts, mock | Four files byte-identical; `causora.contract.v1` is the sole external interface, no renamed fields. |
| Deng Day 1 | Original `simulation_day1/` | 33 files including P2 matched; reuse strict SimulateRequest, ApiFailure, schemas and oracle. |
| Wang Day 1/2 | Day 1 `src/causora_day1/` vs Day 2 `causora/causora_day1/` | Nine Python sources matched; Day 2 adds evidence pipeline. Pending quote matches are not approved BusinessVariables. |
| Wang scope | `evidence_day2/examples/pending_review/review_request.json` | Eight source/contract hashes and thirteen implementation/DTO hashes matched the earlier combined directory; six evidence and five assumptions pending. Source edits require scope regeneration. |
| Deng Day 2 | `simulation_day2/` | 104 x 3 x 3 computations use internal `jinzhu.deterministic-preview.v1`, referencing shared v1; not SimulateSuccess. |
| P2 lineage | Frozen manifest + five raw hashes + 104 original CSV rows | Check whole manifest and row-level order. Swapping [250,279] while preserving totals/hashes is rejected; see [fix](SOURCE_LINEAGE_P2_FIX.md). |

`test_cross_language_contract.py` reads eleven actual TypeScript DTOs and compares their top-level fields against Pydantic: Scenario, DecisionOption, ContractConstraint, CostBreakdown, MetricCell, SimulationResult, DecisionDelta, SimulateRequest, SimulateResponse, ApiError, ApiFailure. Ding's typecheck/frontend tests validate the TS side separately.

| Interface | Shared fields / units | Execution boundary |
| --- | --- | --- |
| POST /api/simulate | schemaVersion, datasetId, scenarios, options, seed, riskThreshold, budgetCeilingUsd; risk .12, shock -15, USD integers, three fixed decisions | `api_boundary.py` validates actual v1 DTO and 26,000-based scenario demand. Changed shock/lead never replays Day 1 static costs. |
| Review/MC incomplete | `{schemaVersion, requestId, error:{code, message, details, requestId}}` | Valid requests produce typed 503 simulation_failed/human_review_pending; invalid requests 422 validation_error. [Example](examples/simulate_error_PENDING_REVIEW.json). No HTTP server in this package. |
| Future 200 | Nine real probability/P90 cells, percentage-point deltas, three selections, actual MC count | Day 2 computes no such statistics. Internal preview has no outer schemaVersion, probability, P90 or recommendation. `response_validation.py` independently validates future costs/deltas/selections/violations/versions; no 200 branch exists here. |
| Wang-reviewed contract | Public EV-014/019/021/024/027; EV-020 internal conditional-renewal ledger. Separate notice/forecast assumptions; uplift .14, share .6, exit 25000 | `run_reviewed_internal` requires `verify_bundle` with scope/source/dependencies. No reviewed bundle was supplied at Day 2; no automatic reviewer/time is fabricated. |
| Internal costs/traces | Base purchase, separate renewal premium, one D2 fee; weekly inventory/orders/deliveries | 104 x 9 real deterministic computations use explicitly unapproved inputs. Cost shape maps to v1, not probability/P90/no-feasible. |

Joint clarifications remain: renewal-date bridge from decision inventory 1,840 to assumed 1,200; A-only versus all-supplier lead stress (both explicit/tested); selling price, lost margin, holding, target/safety stock, ordering/cash timing, floor cycle and future probability/P90; EV-020 must retain EV-014's notice condition. PDF cannot prove notice records are real or automation approve an actual contract.

Historical test boundary: Deng Day 2 21 + Day 1 16, with fresh extraction/P2 attacks/11 DTO checks. Wang/frontend tests are not this standalone package's targets. These checks establish fixture compatibility, not completed review, MC statistics, live E2E or signed team G2.
