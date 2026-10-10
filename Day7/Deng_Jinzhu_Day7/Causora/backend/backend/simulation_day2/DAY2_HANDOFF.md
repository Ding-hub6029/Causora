# Deng Day 2 Handoff and Integration Boundary

Deng owns only `simulation_day1/` and `simulation_day2/`. Ding's original lib/demo_data/golden/public/demo are unchanged test fixtures. No Ding frontend, Wang review implementation or team integration is included; [inventory](../JINZHU_TESTABLE_README.md).

**Historical status:** executable deterministic weekly engine with unapproved synthetic inputs. G2 and official `/api/simulate` remain incomplete. Shared API/TS/mock, Wang evidence and Day 1 oracle are not replaced. PDF p.22's personal deterministic engine + three decisions + tests is implemented in this limited sense; review, policy and probability/P90 remain separate. [Contract alignment](CONTRACT_ALIGNMENT.md) records earlier field comparisons, not legal validity or acceptance.

## Implemented

| Area | Boundary |
| --- | --- |
| 104-week state | Actual synthetic historical demand, one observation per simulation week scaled by scenario; opening, arrivals, available, fulfilled/lost, ending, inventory position, reorder and future orders. Nine independent 104-row traces, not repeated static 420k/411k costs. |
| Deliveries | A 36/B 12 synthetic PO dates/prices from XLSX. Seed rotates deterministic cycling through empirical lead values, multiplied by explicit stress then rounded up to weeks. No random distribution sampling. |
| Decisions/contracts | D0 all A and locked minimum 15,600; D1 exactly 15,600 A + 10,400 B in every scenario; D2 all B and one USD 25,000 fee only for locked renewal. A base 12, separate 14% premium; B 12.6 from XLSX. |
| Weekly costs | Holding = average available/ending x rate; lost sales x lost margin. Aggregate each cost over 104 weeks, then half-even USD; sum five rounded lines for TCO. Revenue uses fulfilled demand x explicit price; zero revenue gives grossMargin=null/INVALID_REVENUE_ZERO. Cash excludes stockout opportunity loss. |
| Validation | Weekly inventory/order/in-transit conservation. Seed/input/raw and engine SHA identify preview; fixed manifest SHA and row-by-row original CSV replay prevent shuffled-demand P2 attacks. Traces retain chosen PO index/planned arrival. Independent response_validation recomputes future v1 deltas, screening, ties and complete violations, rejecting tampering or fabricated zero risk. |
| Review bridge | Unreviewed preview is PENDING_HUMAN_REVIEW. Reviewed internal computation requires Wang's verify_bundle, real scope/dependencies, contract and dataVersion. Empty directory rejected. Reviewed synthetic terms do not approve model inputs or release API. |
| Shared API | Actual v1 DTO -> typed 422/503 failure. Valid requests remain simulation_failed, never replay static costs/fake probability/P90 or label uncomputed runs no-feasible. Eleven TS/Pydantic DTO fields cross-checked. |

## Explicit unapproved assumptions

[Test policy](examples/UNAPPROVED_TEST_POLICY.json) starts 104 weeks at renewal 2026-11-18. The 1,840-unit decision-date CSV is not renewal inventory. Assumed bridge 1,200, selling price 20, lost contribution 5, holding .05/unit/week, safety 100 and target 1,800 are mandatory explicit inputs, never inferred facts.

Policy uses mean weekly forecast x supplier-weighted mean lead + safety; spreads committed procurement across the cycle without arbitrary advance buying; books purchase/cash on ordering, including paid outstanding orders at week 104; holding uses average available/ending; integer USD rounding is half-even. Lead stress supports mandatory `A_only|all_suppliers`. A-only matches scenario wording but differs from the TS all-sampled-leads comment and static D2 stress changes. Both are implemented/tested; the three owners must agree meaning and update versions/mock/contracts together.

Locked-at-renewal forecast 26,000 is synthetic, distinct from observed 25,936. Renewal lock requires clause, dates/deadline AND synthetic notice=false, not merely the phrase auto-renew. No repeated exit fee or double counting.

## Reproduction

From the test package's `causora/`, with a new UNAPPROVED output path:

```bash
python -m pip install -r simulation_day1/requirements-test.txt "pytest>=8,<10"
python -m pytest -q simulation_day1/tests simulation_day2/tests
python -m simulation_day2.export_schemas
python -m simulation_day2.cli preview \
  --project-root . \
  --request simulation_day1/examples/simulate_request.json \
  --policy simulation_day2/examples/UNAPPROVED_TEST_POLICY.json \
  --out /tmp/new-day2-UNAPPROVED.json
```

[Internal preview](examples/day2_preview_UNAPPROVED.json) has internalSchemaVersion, referencedContractVersion, previewId, seed, raw/manifest SHA, 104 x 9 rows, five costs, MC runs 0 and decisionReady=false. It is not SimulateSuccess and has no public schemaVersion, stockoutProbability, cashOutflowP90, risk Delta or recommendedOptionId. [Failure example](examples/simulate_error_PENDING_REVIEW.json) validates as v1 ApiFailure/503; no HTTP service is started. Independent hand-written micro-oracle expectations for zero demand/holding over 104 weeks: D0=213408, D1=344448, D2=25013 USD. Expected values do not come from engine output; Day 1 workbook is unchanged.

Historical fresh extraction: Day 2 21 + Day 1 16 tests = 37 passed, 25 subtests. This package does not rerun absent Wang/frontend modules; earlier external results are historical references. Eleven review rows were pending and dataset_success.json was not generated.

## Outstanding work

1. Wang personally reviews six clauses and five assumptions; [notes](REVIEW_FINDINGS_FOR_WANG.md). No fabricated reviewer, confirmedValue or premature EV-020 approval.
2. Jointly approve inventory bridge, price/loss/holding/stock policy, lead-stress scope, order/cash timing and commitment schedule. Otherwise keep internal preview only.
3. Day 3 adds true sampling, per-run probability/P90, risk screening and independent oracle under agreed sources/formulas; then jointly release API/UI/trace version. Missing statistics are not no-feasible.
4. After Wang review, use `python -m simulation_day2.cli reviewed-preview --project-root . --request ... --policy ... --reviewed-bundle /path/to/NEW_reviewed_dataset --out /path/to/NEW-UNAPPROVED.json`. This remains an unapproved non-decision preview. No reviewed bundle existed for Day 2 end-to-end validation; G2 was unsigned.
