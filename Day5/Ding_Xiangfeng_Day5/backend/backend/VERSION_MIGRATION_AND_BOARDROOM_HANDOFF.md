# Historical component document

This incoming document is preserved as history and is superseded by the root README.md and DAY4_FINAL_ACCEPTANCE.md. Its original bytes are retained under provenance/historical-integrated-reports/.

---

# Day 3 interface version migration and Boardroom handoff

## Fixed version combination

| HTTP outcome | Request schema | Response schema | Meaning |
| --- | --- | --- | --- |
| malformed request | `causora.contract.v1` | `causora.contract.v1` error envelope, HTTP 422 | Existing v1 wire validation failed |
| missing/stale review, policy or release | `causora.contract.v1` | `causora.contract.v1` error envelope, HTTP 503 | Pending/error; never apply mock data as a result |
| explicit unreviewed development launcher | `causora.contract.v1` | `causora.contract.v2`, HTTP 200 | UI/API shape test only; `executionContext.decisionReady=false` |
| reviewed calculation succeeds | `causora.contract.v1` | **`causora.contract.v2`**, HTTP 200 | Real reviewed Matrix + Delta + Selection + Trace response |

`POST /api/simulate` and its request body do **not** change. Only the verified-success envelope changes because `data.traces` is a required nested response structure rather than an optional display decoration. Day1/Day2 v1 mock, Golden, request DTO and original materials remain unchanged.

## v2 addition summary for confirmation

The v2 success body is exactly:

```text
{ schemaVersion, dataVersion, requestId,
  data: { simulation, deltas, selections, traces[scenarioId][optionId], executionContext } }
```

`simulation`, `deltas` and `selections` retain their v1 names, units and rules. Each of the nine traces adds:

- matching `simulationId`, `dataVersion`, `formulaVersion`, scenario and option identity;
- a run identity bound to **separate** review-record, contract-payload, policy-configuration and v2-release records;
- field-specific contract evidence provenance, distinct source-file hash and review-record hash;
- five formula components with resolved `inputKeys`, raw Monte Carlo mean, displayed whole-USD value and displayed-minus-raw difference;
- probability, service and P90 denominators/definitions; and
- one 104-week `sampleRunIndex=0` realised path marked not an average/expectation/aggregate.

Confirm this candidate with Deng, Ding and Wang before creating the trace release record. The canonical backend schema is `contracts/causora.contract.v2.schema.json`; the TypeScript recommendation is `contracts/causora.contract.v2.ts`.

## Boardroom handoff

No new Boardroom endpoint is added in this package. Once a reviewed v2 simulation succeeds, the future Boardroom request must take values **only** from the validated response:

```json
{
  "schemaVersion": "causora.contract.v1",
  "simulationId": "response.data.simulation.simulationId",
  "dataVersion": "response.data.simulation.dataVersion",
  "scenarioId": "the selected response scenario id"
}
```

Before Boardroom accepts it, verify `data.executionContext.mode === "reviewed_release_gated"` and `data.executionContext.decisionReady === true`, then verify the retained audit artifact named `<simulationId>.json` has the same `simulationId`, `dataVersion`, review record, policy configuration ID and contract-release record. Boardroom must reject `unreviewed_development_only` output and must not infer values from a mock, Golden snapshot, preview ID or a different scenario.

## Frontend migration boundary (owned by Ding)

Ding should update shared types and runtime validation atomically using the supplied TypeScript recommendation and JSON Schema. Do not upgrade only the backend: a frontend that still validates only v1 must continue to reject a v2 success rather than silently dropping traces. After the joint release record exists, switch the client success validator to v2 while retaining its v1 error parser for 422/503 responses.
