# Causora / Deng Jinzhu Day 1 Handoff: Simulation and Data

**Historical Day 1 delivery.** This module supplies historical fixtures, schemas, an independent oracle, interface boundaries and static examples. It does not implement the real 104-week engine, Monte Carlo, HTTP `/api/simulate` or an actual simulation recommendation. Later integration status is documented in the Day 3 integrated package.

## 1. Shared interface examples for Ding Xiangfeng and Wang Hao

- [Complete request](examples/simulate_request.json): `schemaVersion=causora.contract.v1`, `datasetId=ds-001`, three scenarios, D0/D1/D2, `seed=1042026`, `riskThreshold=0.12`, `budgetCeilingUsd=480000`.
- [Success-shaped LOCAL MOCK](examples/simulate_response_LOCAL_MOCK.json): `{schemaVersion, dataVersion, requestId, data:{simulation, deltas, selections}}`. `simulationId=sim-day1-mock-0001`, `dataVersion=demo-2026.10.04-v4`, `formulaVersion=tco-v1`, `weeks=104`, `monteCarloRuns=0`. The nine cells are copied unchanged from the baseline. Only deltas and constraint screening are computed from those static cells. D1 is selected in each default scenario for illustration. This is not engine output.
- [No-feasible request](examples/simulate_request_no_feasible.json) and [paired LOCAL MOCK response](examples/simulate_response_no_feasible_LOCAL_MOCK.json) use the same cells with a USD 1 cash ceiling. All scenarios have `status=no_feasible_option` and `recommendedOptionId=null`. Violations follow D0/D1/D2 order, then infeasible, stockout_threshold, cash_ceiling. Do not pair this response with the default request.
- [Not-computed error](examples/simulate_error_not_computed.json) uses shared `simulation_failed` with 503, never `no_feasible_option` for a run that has not been computed.
- [JSON Schema](schemas/simulate_v1.schema.json), [Pydantic v2 DTOs](wire_models.py) and [Python boundary](interfaces.py) mirror the camelCase fields, hierarchy and version in `lib/contracts.ts`. Schemas check shape. Python additionally checks cross-field semantics. No separate frontend DTO or unsigned baseline change is introduced.

The `baseline/D1` cell has A/B units 15,600/10,400. Purchase 318,240. Renewal premium 26,208. Holding 41,500. Stockout loss 25,052. Termination fee 0. TCO 411,000 USD. Relative to baseline D0, delta TCO is -9,000 USD, stockout delta -4 **percentage points**, cash P90 delta -21,000 USD. `demandShock=-15` means -15 percent, not -0.15. Probability 0.07 means 7 percent.

### Schema coverage

- [Internal input snapshot](demo_inputs_v1.json), [schema](schemas/demo_inputs_v1.schema.json) and [source models](source_models.py) cover 104 weeks, 48 deliveries, opening inventory, synthetic notice records and forecast assumptions, with source SHA-256 values. [Generator](build_day1_schemas.py) checks five frozen source hashes and refuses regeneration under the same `dataVersion` after a source change. This is internal preparation, not a new public dataset payload. Preserve `humanReviewed=false` and synthetic provenance.
- [MockData schema](schemas/mock_data_v1.schema.json) covers `meta/intake/evidence/contract/variables/scenarios/options/simulation/boardroom/critic/brief`. A successful local MockData object is not forced into the API no-feasible union.
- Request/success schemas for simulation, dataset success, Boardroom request/success, Evidence, Health, Golden and API failure are generated from [one Pydantic model set](wire_models.py). Request and nine-cell schemas cross-check each other. Dataset upload remains multipart as defined by `API_CONTRACT.md`. It is not a JSON request.
- API `SimulateRequest.riskThreshold=0.12` is a fraction. Legacy local Golden `request.riskThreshold=12` is a slider percentage. Preserve both original meanings, data and versions. Schemas are Day 1 draft mirrors, not evidence that HTTP endpoints exist or the team has signed them.

### P2: reject changed simulation inputs in static examples

Default `validate_request()` compares all fields of three frozen scenarios and three frozen options by ID against v4.1. A self-consistent baseline change to shock -50 and demand 13,000, a lead multiplier of 9, or changed option labels raises `ContractInputError`. Array reordering alone is allowed. A future HTTP adapter should map this to shared `validation_error` 400/422, never return the old nine costs. `make_mock_response()` also requires the original mock content and SHA-256. Only risk threshold and budget may change to rescreen the same nine cells, still LOCAL MOCK with zero MC runs. Data/scenario/option changes require joint refreezing. Future `simulate_104_weeks` bypasses this static-only gate, but currently raises `NotImplementedError`.

Both Python test files explicitly read UTF-8. All 16 tests also passed on Linux with UTF-8 mode disabled and ASCII as the default encoding. This historical result is not a claim of testing on a Windows host.

## 2. Facts, inputs and assumptions

| Input | Value | Source and limitation |
| --- | --- | --- |
| Historical demand | 104 weekly rows, 2024-10-07 through 2026-09-28. Total 25,936. Mean 249.384615... | `public/demo/historical_demand.csv`. Seed 1042026 in `scripts/generate-demo-fixtures.py`. Entirely `synthetic_day1_fixture`. [Byte-identical CSV](source_snapshot/historical_demand.csv), [snapshot](historical_weekly_v1.json), [schema](schemas/historical_weekly_v1.schema.json). SHA-256 `654a22f3f5433e214611f3c5a69b625bedad2d11157dedfa9cd65bbb14d3499e`. |
| Inventory and deliveries | 1,840 units as of 2026-10-04. 48 synthetic POs, A 36/B 12. Prices USD 12/12.6 | `opening_inventory.csv`, `supplier_delivery_history.xlsx`. Synthetic, not actual operating records. |
| Contract wording | 60-day notice. 24-month renewal. 14% price increase. 60% forecast purchase floor. USD 25,000 early exit | Synthetic agreement PDF p.4, EV-014/019/021/024/027. Wang's source notes/interface mapping establish quote matches, not factual/legal validation. `manually_verified:false` at this delivery. |
| Renewal lock | Decision 2026-10-04, renewal 2026-11-18, deadline 2026-09-19. 45 days remaining. `noticeSent=false` | Synthetic structured input and correspondence CSV. PDF alone does not prove no real notice was sent. Missing notice records must cause an error. |
| Locked forecast/floor | 26,000 forecast. A floor 15,600 | Synthetic renewal assumption, not the historical total 25,936 or an automatic forecast. 0.6 x 26,000. |
| Downside | Demand 22,100. D1 still purchases A 15,600 + B 10,400 | Total excess is 3,900. The 2,340 difference between 15,600 and 60% of 22,100 is only the A-floor difference, not total excess. |
| Holding, stockout and P90 | Frozen aggregate examples | Missing rates, lost margin, replenishment and payment timing prevent reconstruction of real weekly traces. D2 holding changes cannot all be attributed to the exited A contract. |

The locked forecast and historical total are different concepts. D1 purchases remain exactly 60/40. Under `tco-v1`, purchase uses A/B base prices. A renewal premium is A units x A base price x 0.14, shown separately once. The USD 25,000 fee applies once only to D2 exiting a locked renewal. If valid timely notice prevents renewal, neither renewal cost applies. Five integer-USD lines must sum to TCO. Cash P90 is a separate risk measure and is not added to TCO.

## 3. Independent oracle and reproduction

[Workbook](oracle_day1_independent.xlsx) is built by [independent script](build_oracle.py), which imports neither `interfaces.py` nor mock expected values. Five hand-entered expected amounts are separate from formulas. LibreOffice recalculated 3,500, 3,342, 28,160, 419,000 and 438,000 USD, all zero differences. Independent screening selects lower-TCO D1 when D0/D1 qualify and returns no feasible option at risk 0.01. Risk/P90 values here are screening inputs, not Monte Carlo forecasts or proof of the mock cost mechanism.

From baseline `causora/`:

```bash
python3 -m pip install -r simulation_day1/requirements-test.txt
python3 -m simulation_day1.build_day1_schemas
python3 -m simulation_day1.interfaces
python3 simulation_day1/build_oracle.py
python3 -m unittest discover -s simulation_day1/tests -v
```

Workbook formula caches require LibreOffice recalculation.

## 4. Proposals requiring joint agreement before baseline changes

| Existing definition | Proposed clarification | Reason / affected modules |
| --- | --- | --- |
| 104 weeks. Decision 2026-10-04. Renewal 2026-11-18. Decision-date opening inventory | Define week 1 and the inventory/price/purchase bridge. Separate renewal's 104 weeks from the pre-renewal bridge | Charging 14% for all weeks beginning at the decision date may overcharge before renewal. Engine, input data, trace, period labels. |
| A floor 15,600, D1 total 26,000, inventory-position replenishment | Define enforcement, exact 60/40 under low demand, outstanding orders and cash recognition. Retain static meaning pending agreement | Stockout-driven ordering alone may miss the floor. Engine, constraints, cached data, oracle. |
| PDF p.8 allows alternative stockout events. P90 payment schedule unspecified | Sign one probability event and payment/quantile definition, preferably per-run total 104-week cash P90, before risk 0.12 | Event choice changes eligibility and recommendations. Engine, UI, Brief, tests. |
| Five costs but no rates/weekly trace DTO | Supply holding rate, lost contribution margin, safety/target stock, arrival/purchase timing. Negotiate trace DTO or v2 | Cannot derive holding/loss/P90 from static totals. Do not silently append v1 fields. |
| Whole-response cache key omits risk/budget | Include both thresholds or cache only physical simulation and rescreen per request | Metrics may stay fixed while selection/Brief changes. API/cache, frontend, Boardroom, tests. |
| Forecast floor is 60%, mock uses locked forecast | Identify locked-at-renewal as synthetic interpretation. Any rolling interpretation requires Wang/Ding/Deng joint changes | Downside rolling floor becomes 13,260. Update contract, TS types, mock, Golden and tests together. |
| Success supports selected/no-feasible only | Use 503 `simulation_failed` or not-run UI for incomplete computation | No-feasible requires computed results with all options failing. |
| Integer USD rounding lacks tie rule | Agree tie behavior and rounding each line before summing | Python half-even differs from Excel half-away at .5. Current oracle has no half-dollar ties. |

These are proposals, not approved contracts. Coordinate shared contract/mock/Golden/tests, increase `schemaVersion` for breaking structure and `dataVersion` for changed data. This independent Day 1 file cannot replace Wang's reviewed variables.

## 5. Historical checks and outstanding work

16 Python tests passed, including frozen-input/mock rejection, threshold rescreening, DTO/units/costs/deltas/oracle, full MockData/Golden, five-source hashes/version discipline and shared API schema shapes. All 16 also passed under a non-UTF-8 default. Five Excel cases recalculated with zero differences. Baseline frontend typecheck, 21 tests, lint and build passed.

Not implemented here: real deterministic inventory engine, MC/P90, weekly traces, HTTP server, human review, complete ingestion, live E2E or production Golden. `simulate_104_weeks()` raises `NotImplementedError`. Interface preparation alone does not establish Day 2/G1 completion.

Day 2 needs an independent untrusted-response validator: recompute four deltas against scenario D0 (risk/service in percentage points), eligibility and minimum TCO with ID tie order. Validate no-feasible and complete violations, scenario set, seed, data/formula versions and simulation identity. Use malicious-response tests rather than calling the response generator as its own validator.
