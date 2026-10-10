# Deng Jinzhu Day 3: Stochastic Simulation Handoff (Historical)

Original owner scope: only simulation_day3/ is new Deng code; simulation_day1/2 are prior Deng modules. lib/, demo_data/, golden/, public/demo/ and API_CONTRACT.md are Ding's unchanged read-only test fixtures, not Wang integration, contract changes or frontend deployment. Specification: Causora.pdf pp.7,10,11,22. This historical handoff predates the integrated backend; see current root TECHNICAL_FIX_REPORT.md for later review/API work.

## Implementation and limits

| PDF item | Implementation | Limit |
| --- | --- | --- |
| MC/seeds | Independent N x104-week inventory paths: empirical weekly demand, sampled lead times, arrivals/lost sales, order-time cash/costs; numpy.PCG64(seed), common random worlds across decisions/scenarios; deterministic replay | Synthetic data/unapproved policy, not human contract review. |
| Sampling sources | 104 demand weeks total 25,936; A 36 empirical POs; B 12 below PDF's30, explicit unapproved triangular10/14/17 days | B fallback is a test assumption, not reviewed estimation from 12 observations. |
| 3x3 decisions | baseline/demand-drop/lead-stress x D0 all A, D1 60A/40B, D2 exitA/all B. D1 per-trial 15,600/10,400; D0 respects locked floor; D2 one exit fee | Lock/26,000 are frozen synthetic assumptions, not legal conclusions. |
| Risk/cost | stockoutProbability = trials with any shortage / N; service=all fulfilled/all demand; cash P90 nearest rank ceil(.9N); TCO=base purchase+holding+loss+separate premium+one exit | Loss is opportunity cost, not cash; holding averages available/ending. |
| Deltas/screening | Option minus D0; percentage points; risk/budget equality passes; preview eligible IDs/violations only, no winner | Public selected/no-feasible/null-winner output waits for approved adaptation; no approvable Brief. |
| Trace/oracle | Nine sample paths x104 weeks with demand/lead/inventory/orders/costs; aggregate counts/rank/raw means; code-calculated revenue/profit/margin (zero revenue INVALID); half-even displayed USD; independent hand-entered spreadsheet/four paths/literal tests | Public v1 lacks weekly/gross-margin DTO; do not append internal fields to MetricCell. |
| API | Shared request/failure DTO, typed503 pending review/policy; internal preview lacks public response/identity/winner/envelope and fails SimulateSuccess validation | Original module has no HTTP200/GoldenLive/formalG3. |

## Inputs and replay

Whole Day1 manifest SHA, all104 original CSV rows, five raw-source hashes and mock SHA are rechecked. Each preview records manifest/source/Day3 code/sample-index hashes, NumPy/PCG64 versions, seed,1000/10000 runs,104weeks and data/formula versions. Same NumPy reproduces exact bytes.

UNAPPROVED_MC_POLICY.json explicitly assumes renewal2026-11-18 inventory1200 (not decision CSV1840), sale20, lost margin5, holding.05/week, target1800,safety100,B triangle10/14/17,A_only stress. Prices come from frozen supplier XLSX. Missing policy/fallback must reject.

Demand draws from104 observations then scales by scenario.demandUnits24m/25936 and rounds to nearest integer; each trial total may differ from26,000/22,100. Forecast is the synthetic distribution center. Lead draws from A empirical days/Bassumed triangle, then scenario multiplier and ceil weeks. Reorder uses scenario mean weekly forecast x raw A 36-PO mean/B theoretical triangle mean, decision-weighted, plus safety. Do not derive policy from random trial sample means. Stress changes lead/reorder together, so risk need not be mathematically monotonic.

D0/D2 order totals vary by path. Public integer units and frontend purchase reconciliation require half-even rounding of mean units, then recomputed purchase/premium. rawMeanCostsUsd retains true unrounded sample means and discretization difference. D1 fixed units need no averaging. Confirm this display meaning before formal success; displayed costs are not asserted identical to raw means.

Cash P90 uses per-trial 104-week purchase+holding+premium+applicable one exit, each full-horizon line half-even rounded, sorted to ceil(.9N); no stockout loss/weekly duplicate charge. Independent Excel uses SMALL(...,ROUNDUP(.9*N,0)).

## Reproduce original module

Install simulation_day1/requirements-test.txt and simulation_day3/requirements-test.txt from causora/:

```bash
python -m pytest -q simulation_day1/tests simulation_day2/tests simulation_day3/tests
python -m simulation_day3.cli preview --project-root . --request simulation_day1/examples/simulate_request.json --policy simulation_day3/examples/UNAPPROVED_MC_POLICY.json --out simulation_day3/examples/new_trial_UNAPPROVED.json
```

CLI refuses overwrites. Use --runs10000 as separate tokens (`--runs 10000`) and a new filename for10k. Delivered previews are labelled UNAPPROVED. computedMatrix/decisionDeltas match v1 field shapes; constraintScreening is internal and winner-free. No schemaVersion/data/requestId/simulationId/recommendedOptionId envelope. Negative ApiSuccess(data=preview) tests prove shared SimulateSuccess rejection; original api_boundary has no 200 branch. Shape comparisons do not establish live E2E. Later authenticated success requires review/approval and Ding's validator.

## Independent oracle and historical results

Workbook examples/day3_independent_oracle.xlsx uses constants/formulas independently from engine. Zero-demand 104-week expectations: D0 213,408,D1 344,448,D2 25,013 USD. Four-path case: one first-week demand 10, opening 0,D2 orders 2; other paths zero -> risk .25,P90 cash 25,025,mean loss 12.5 half-even 12,display TCO 25,037. LibreOffice caches PASS; separate literal tests pin values.

Same-seed 1000 output exactly repeats. Adjacent seeds over 10,000 runs had max observed nine-cell risk difference .71 percentage points, an empirical result not theoretical bound. Second 10k run ~1.31 s in Sandbox, excludes HTTP/browser. Original Day 3 tests 14, Day 1 16, Day 2 21; original Ding frontend 31 separately passed, live E2E incomplete. Fresh-extraction check required at delivery.

Historical G3 prerequisites: Wang personally reviews six clauses/five assumptions and verifiable bundle; team confirms bridge, price/loss/holding, procurement, B fallback, A-only stress and mean-unit rounding per G3_DECISIONS_PENDING.md; then implement authenticated actual POST 200, numeric guardrails and frontend E2E. This standalone internal preview alone is not signed PDF G3 or procurement approval. Current integration adds subsequent work without rewriting these historical claims.
