# Day 3 Front-End Integration Notes

## Request path

`app/page.tsx` builds the request from the preserved Day2 `Scenario[]` and `DecisionOption[]`, then `lib/simulate-api.ts` posts it to `POST /api/simulate`. The default URL is same-origin. `NEXT_PUBLIC_CAUSORA_API_BASE_URL` is an optional backend origin; `NEXT_PUBLIC_CAUSORA_DATASET_ID` defaults to `ds-001`.

The UI stockout control is displayed as whole percent and converted to a decimal fraction on the wire. Cash is sent as a non-negative integer USD amount. The input seed comes from the preserved fixture metadata and is displayed with the response. Only the active scenario's demand shock is edited; its 24-month demand units are rescaled by the ratio of the new and old shock factors. The frozen D0/D1/D2 definitions are sent unchanged.

## Success contract checks

A response is applied only if all of the following hold:

- `schemaVersion` is `causora.contract.v1`; envelope and simulation `dataVersion` agree.
- `formulaVersion` is `tco-v1`, seed matches the request, `weeks` is 104 and `monteCarloRuns` is positive.
- `simulationId` is present and is not a mock identifier.
- The matrix has exactly the requested scenario IDs and D0/D1/D2 exactly once for each.
- Each cost component is a non-negative integer; five components sum to `expectedTco`; purchase reconciles to units and returned A/B base prices within half a whole USD; unit allocation matches the requested option.
- Every option has one delta against D0; each integer delta and percentage-point delta reconciles to the returned matrix.
- Every scenario selection follows the inclusive risk/cash limits and feasibility filter, minimizes expected TCO with option-ID tie-break, and carries violations in D0/D1/D2 then infeasible/stockout/cash order. No-feasible remains an explicit null winner.

## Failure, stale and downstream states

- HTTP/API errors, timeouts, bad schemas, wrong seeds, zero-run previews, mock snapshots, inconsistent accounting/deltas/selections and stale responses are rejected. The saved example remains labelled as Day2 data.
- Editing scenario/demand/risk/budget invalidates the prior live result. Option selection and switching between scenarios with identical request-driving assumptions do not mutate the request.
- After a live simulation, Day2 Boardroom/Brief mock content is not shown. The UI returns the user to the live Matrix until a matching `/api/boardroom` response is implemented in its owner's scope.
- The v1 `SimulationResult` exposes aggregate holding and stockout-loss components, not weekly inventory/lost-unit traces. Formula Trace states that boundary rather than fabricating weekly drivers.

## Browser regression checklist

1. Start with no backend. Confirm the 3×3 grid is labelled **SAVED VALUES · NOT COMPUTED** and contains the unchanged Day2 fixture values.
2. Change demand, risk or budget and confirm the grid warns that its saved cells do not represent the draft.
3. Run without a reachable service. Confirm an error appears, the old values remain explicitly saved examples, and no stale live run is set.
4. Connect a v1-compatible backend and run. Inspect request body fields, fractional risk, dataset ID, seed and HTTP path in DevTools.
5. Confirm the 3×3 values and per-scenario selection update only after a valid positive-run response; click each cell and Formula Trace.
6. Verify Formula Trace component sum, purchase reconciliation, Decision Delta, run metadata and the v1 note for unavailable weekly traces.
7. Edit a request input after success and confirm live values are invalidated. Navigate to Boardroom/Brief and confirm the unrelated Day2 sample is gated; return to Matrix.
8. Open Golden Run and confirm its frozen local behavior remains intact and simulation is disabled until returning to the live workspace.

Contract-test responses under `tests/simulate-api.test.mjs` are local test fixtures only; they are not a backend or live Monte Carlo E2E.
