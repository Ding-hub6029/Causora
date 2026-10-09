# Day 3 model-policy confirmation register

**Owners:** Deng Jinzhu (simulation), Ding Xiangfeng (frontend/contract), Wang Hao (review).  Wang's contract review is necessary but **does not approve** any of the operating/model-policy items below. Until all items are recorded in the team policy approval record, the service remains fail-closed.

| Topic ID / required record key | Current test assumption — not yet production approval | Required decision and bridge/evidence |
| --- | --- | --- |
| `renewal_date_opening_inventory_bridge` | Opening inventory `1,200` effective `2026-11-18` | Confirm renewal date, exact opening units, bridge from decision-date inventory and its source/owner. |
| `selling_price` | `$20/unit` | Confirm sales-price source, currency and effective period. |
| `lost_contribution_margin` | `$5/unit` | Confirm contribution loss definition and why it differs from price. |
| `holding_cost` | `$0.05/unit/week` | Confirm cost basis, unit and calendar/weekly convention. |
| `safety_stock` | `100 units` | Confirm physical target and rationale. |
| `target_stock` | `1,800 units` | Confirm target, and ensure it exceeds each computed reorder point. |
| `replenishment_and_minimum_purchase_schedule` | Reorder at `inventoryPosition <= point`. Target-up ordering. Linear weekly minimum purchase pacing | Confirm purchase scheduling, D1 60/40 fixed quota, renewal minimum treatment and end-of-horizon in-transit treatment. |
| `purchase_and_cash_recognition_timing` | Purchase/cash recorded at order. Holding/premium/fee are cash P90 lines | Confirm purchase recognition, cash timing and accounting timeline. Stockout loss stays non-cash. |
| `supplier_b_lead_distribution` | Triangular 10/14/17 days. Only 12 B POs | Approve/revise values and source. Or provide enough observations for empirical fit. |
| `lead_stress_scope` | `A_only` | Confirm whether lead stress applies to A only or both A/B. |
| `stockout_probability_definition` | `trials_with_at_least_one_lost_unit / monteCarloRuns` | Confirm a run-level stockout event is the decision metric. |
| `service_level_definition` | `fulfilled_units_all_runs / demand_units_all_runs` | Confirm fill-rate definition and zero-demand convention (= 1.0). |
| `cash_p90_method_and_lines` | nearest rank `ceil(0.90N)` after whole-USD half-even per-run cash rounding. Purchase/holding/premium/fee included, stockout loss excluded | Confirm percentile, rank, included/excluded lines and rounding order. |
| `money_and_mean_purchase_rounding` | Mean ordered A/B units half-even to integers. Display purchase/premium recomputed from those integers. Other means rounded half-even to USD | Confirm that raw Monte Carlo means, displayed values and their difference are all retained and are **not asserted equal**. |
| `demand_bootstrap` | 104 historical weekly synthetic demand observations sampled with replacement and scenario-scaled | Confirm scaling and statement that individual run totals vary around scenario forecast. |

The policy verifier requires every key above in `confirmedTopics`, three recorded owner roles and a hash binding to the exact policy file. A `TEAM_APPROVED` flag inside the policy file alone is rejected.
