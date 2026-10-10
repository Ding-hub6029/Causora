# Historical component document

This incoming document is preserved as history and is superseded by the root README.md and DAY4_FINAL_ACCEPTANCE.md. Its original bytes are retained under provenance/historical-integrated-reports/.

---

# Causora — Integration API Contract, Draft v1

**Status:** Review-ready, unsigned Day 1 **interface proposal** for Day 2 module owners. The Day 1 website is a static local mock: none of these HTTP endpoints exists yet. This document describes the exact shapes that a future FastAPI backend should implement. A successful prototype is **not** a claim that this backend has been built, tested or connected.

**Owners:** Xiangfeng Ding (integration), Jinzhu Deng (simulation/data), Wu Wang (evidence/agents). Freeze changes through a reviewed change to this file, `lib/contracts.ts`, `lib/types.ts`, `demo_data/causora_day1_mock.json`, `golden/golden_run.json` and contract tests together. Do not add free-form numeric values in Agent prose.

## 1. Transport and version

- JSON over HTTPS; multipart/form-data only for `POST /api/datasets`. Request/response encoding UTF-8. All successful JSON responses include `schemaVersion: "causora.contract.v1"`, `dataVersion`, `requestId` and a typed `data` value. The bundled-data validator rejects any unknown `schemaVersion` and the UI displays an explicit unavailable-approval error. Future HTTP adapters must reject unknown response versions before consuming them; an intact validated Golden snapshot may be offered as an explicitly labelled fallback.
- Dataset versions are immutable snapshots (`dataVersion`), formula versions use `tco-v1`, and the deterministic seed is an integer. A schema-breaking change increments `schemaVersion`; display-only text changes may retain it but increment `dataVersion` when the mock is re-frozen.
- Cache key: `dataVersion + SHA-256(canonical scenario JSON) + ordered option IDs + seed + formulaVersion + modelVersion`. Never label a modified input as the same verified Golden snapshot.
- The 24-month horizon is **104 weekly steps**. `monteCarloRuns: 0` means static Day 1 mock cells; production simulation must report an actual positive run count.
- Canonical field names are the TypeScript camelCase names in [`lib/contracts.ts`](lib/contracts.ts). Backends must serialize those names exactly. `OptionId = D0 | D1 | D2`; scenario IDs `baseline | demand-drop | lead-stress` for the demo.

## 2. Units and numeric discipline

| Field family | Wire unit and example | Rendering / rule |
| --- | --- | --- |
| Currency (`expectedTco`, breakdown lines, `cashOutflowP90`, `terminationFeeUsd`) | Integer **USD**, e.g. `419000` | UI may format `$419k`. Never send `$419k` as a metric. |
| Probability / allocation (`stockoutProbability`, `serviceLevel`, `shareA`, `minPurchaseShareA`) | Decimal fraction in `[0,1]`, e.g. `0.07` | UI shows `7%`. No mixing `7` and `0.07`. |
| Scenario demand shock | Whole percent, e.g. `-15` | UI shows `−15%`. Scenario is external; option is controllable. |
| Cost deltas | Signed integer USD / percentage points | `option − baseline` (negative TCO means a saving). |
| Demand / purchase quantity | Whole units, e.g. `15600` | Do not confuse forecast, realised demand and ordered units. |
| Dates / timestamps | `YYYY-MM-DD` / ISO-8601 UTC `Z` | Compute deadlines from dates; status also needs the `noticeSent` input. |
| Evidence match score | Fraction `[0,1]`; `1.0` is exact | `quoteMatched` is a quote match, not proof of the business fact. |

**TCO accounting (v1):** `expectedTco = purchase + holding + stockoutLoss + renewalPremium + terminationFee`. Purchase is **at base unit prices**; the Supplier A uplift appears **only in `renewalPremium`** (`unitsFromA × basePriceA × 0.14`). Equivalently one could include it in an effective unit price and set the premium line to zero; do **not** use both. This contract fixes the former convention. Each cell's five numeric components must sum **exactly** to `expectedTco` after whole-USD rounding. `cashOutflowP90` is a separately estimated risk metric, not another TCO component. D2 incurs the termination fee once when the renewed contract is exited.

**Forecast commitment (demo assumption):** Supplier A's `60%` minimum is measured against a **26,000-unit forecast locked at renewal**, not the lower realised forecast in a demand shock. Thus the absolute floor is `15,600` units. Under `demand-drop`, projected realised demand is `22,100` units; `15,600 − 0.60 × 22,100 = 2,340` committed units above a rolling-minimum benchmark. **D1 keeps the spec's fixed 60/40 purchased-unit split in every scenario:** `15,600 A + 10,400 B = 26,000` even when realised demand drops to `22,100` (3,900 units above realised demand). Do not represent the 60/40 figure as merely a target while a formula cell silently buys a different ratio. This is an illustrative synthetic mechanism, not an audited real contract interpretation. Holding-cost deltas across scenarios are separate illustrative mock inputs; they are **not** all causally attributed to the contract (especially D2 after termination). The live simulator must derive both purchases and cost components from source data.

**Renewal lock (demo assumption):** `decisionDate = 2026-10-04`, `renewalDate = 2026-11-18`, `noticeDeadline = 2026-09-19` and `daysToRenewal = 45` are structured inputs. Renewal is treated as locked only because `45 < 60` **and `noticeSent = false` in the synthetic notice record**. An earlier valid written notice would change this outcome even inside the 60-day window. Real deployment must ingest and verify the notice register; the absence of a real-world notice is not established by this demo.

## 3. Shared entities

| Type | Fields that must cross the boundary | Main invariants |
| --- | --- | --- |
| `Scenario` | `id`, `label`, `demandShock`, `demandUnits24m`, `leadTimeMultiplier`, `leadTime`, `description` | External variables; never pack an option into a scenario. |
| `DecisionOption` | `id`, `shareA`, `terminateA`, `allocation`, `label`, `description` | IDs D0/D1/D2 unique. Every cell's `unitsFromA / (unitsFromA + unitsFromB)` equals `shareA` (D1 = 60/40 exactly); if locked, A units also meet the absolute floor unless `terminateA=true` and the exit fee is paid. |
| `ContractConstraint` | All renewal dates, `noticeSent`, forecast basis and locked units, uplift, floor, exit fee, `evidenceIds` | Derived values must be traceable to explicit inputs and source/assumption provenance. |
| `BusinessVariable` | `key`, `name`, `value`, `unit`, `source`, `meaning`, `inputs[]` | Each `source` resolves to an `EvidenceRecord`; EV-019 maps to renewal term. |
| `EvidenceRecord` | `id`, `sourceFile`, `page`, `quote`, `locatorBbox`, `extractedField`, `extractedValue`, `matchMethod`, `matchScore`, `quoteMatched` | Match critical value against the preserved quote. `locatorBbox=null` means not located, not a fabricated page rectangle. |
| `SimulationResult` | `simulationId`, `seed`, `dataVersion`, `formulaVersion`, `weeks`, `monteCarloRuns`, `unitPricesUsd`, `matrix` | One unique `MetricCell` per option per scenario; numeric wire units, exact A/B procurement ratio and exact breakdown sum. |
| `DecisionDelta` | `scenarioId`, `optionId`, `baselineOptionId`, `deltaTco`, `deltaStockoutPp`, `deltaServicePp`, `deltaCashP90` | Computed in code, `option − baseline`; never written by an LLM. |
| `AgentOutput` | `role`, `headline`, `body`, `metrics[]`, `status` | Numeric claims only from vetted metric/evidence refs. Day 1 body uses guarded `{{token}}` templates. |
| `CriticIssue` | `severity`, `headline`, `body`, `evidenceIds`, `mechanism` | Cross-agent compound risk; cannot alter metric cells. |
| `DecisionBriefRef` | `recommendedOptionId`, `recommendation`, `rationale`, `metricRefs`, `formulaVersion`, `guardrail` | Recommendation must resolve to an existing feasible option ID. UI inserts actual numbers from `SimulationResult`. |

Complete compile-time types are in `lib/contracts.ts`; the complete **example response data** is `demo_data/causora_day1_mock.json`. `golden/golden_run.json` includes a frozen independent copy of this full data shape, not a reference back to the main mock file.

## 4. Endpoints — to implement on Day 2+

Responses use envelope `{ "schemaVersion": "causora.contract.v1", "dataVersion": "demo-2026.10.04-v4", "requestId": "req-...", "data": { ... } }`. Error responses use `{ "schemaVersion": "causora.contract.v1", "requestId": "req-...", "error": { "code": "validation_error", "message": "...", "details": { ... }, "requestId": "req-..." } }`; allowed `error.code`: `validation_error` (400/422), `not_found` (404), `provider_timeout` (504), `simulation_failed` (503), `internal_error` (500). No secrets or private source content in error messages.

### `POST /api/datasets`

Multipart fields: `historical_demand` CSV, `supplier_delivery` XLSX, `opening_inventory` CSV, `supplier_agreement` PDF; optional `notice_register` CSV. Reject missing files, malformed types, unsafe sizes and ambiguous duplicate fields (`validation_error`). Synthetic notice status is an explicit mock input, not a side effect of uploading a PDF.

**200 `data` (synchronous v1 only):** `{ "datasetId": "ds-001", "preprocessStatus": "ready", "dataVersion": "demo-2026.10.04-v4", "intake": [...], "evidence": [EvidenceRecord], "contract": ContractConstraint, "variables": [BusinessVariable] }`. The request remains pending while preprocessing; frontend shows loading. Return 200 only after quote validation and preprocessing finish, or a documented error. v1 does not return 202/processing. An asynchronous job/status protocol requires a separately agreed revision.

### `POST /api/simulate`

**JSON request:** `{ "schemaVersion": "causora.contract.v1", "datasetId": "ds-001", "scenarios": [Scenario], "options": [DecisionOption], "seed": 1042026, "riskThreshold": 0.12, "budgetCeilingUsd": 480000 }`. For v1, require exactly one of D0/D1/D2 each, unique scenario IDs, finite in-range fractions, a valid forecast basis and a nonnegative integer seed. `riskThreshold` is a fraction on the wire even though the UI slider displays whole percent.

**200 `data`:** `{ "simulation": SimulationResult, "deltas": [DecisionDelta], "selections": { "baseline": { "scenarioId": "baseline", "recommendedOptionId": "D1", "status": "selected", "constraintViolations": [] } } }`. The `SimulationResult.matrix` contains cell breakdowns as the formula trace. Return exactly one selection per requested scenario; no implicit cross-scenario winner. Within each scenario, if none passes feasibility, stockout threshold and cash ceiling, use `recommendedOptionId: null`, `status: "no_feasible_option"` and ordered violations; never fabricate a clean winner. A changed slider needs a new simulation request before its numbers become decision-ready.

### `POST /api/boardroom`

**JSON request:** `{ "schemaVersion": "causora.contract.v1", "simulationId": "sim-...", "dataVersion": "demo-2026.10.04-v4", "scenarioId": "baseline" }`.

**200 `data`:** `{ "scenarioId": "baseline", "agentOutputs": [AgentOutput], "criticIssues": [CriticIssue], "brief": DecisionBriefRef, "numericGuardrail": { "passed": true, "rejectedClaims": [] } }`. Validate every `metricRef` against the referenced `SimulationResult`; reject a recommendation not among its feasible options. Role-specific views and a Critic may write explanations, but never rewrite validated numbers.

### `GET /api/evidence/{id}`

**200 `data`:** `{ "evidence": EvidenceRecord }`; `404 not_found` for an unknown ID. `sourceFile`, one-based `page` and optional PDF `locatorBbox` identify the quote; the UI must not claim PDF-region highlighting when `locatorBbox` is `null`.

### `GET /health`

**200 `data`:** `{ "service": "ready", "simulation": "ready", "evidence": "ready", "provider": "ready" }`; unhealthy dependencies may respond **503** with component statuses. These statuses must be from actual checks rather than a hardcoded "ready". The static Day 1 frontend does not call `/health`.

### `GET /api/golden`

Optional backend mirror; the frontend bundles the frozen local `golden/golden_run.json`. **200 `data`:** the full `GoldenRun` object. Only a real, audited end-to-end result may be called a production verified run; the Day 1 bundled snapshot remains labelled **local mock**. The frontend must switch entirely to `golden.snapshot` while Golden is active and remove its label on any input edit.

## 5. Integration handoff and acceptance

1. Jinzhu implements simulation API / deterministic fixtures, including unique option cells, explicit units, every cost component and `no_feasible_option` behavior.
2. Wu implements `EvidenceRecord`, each `BusinessVariable` including EV-019, quote matching and structured Critic/Agent refs.
3. Xiangfeng swaps the frontend local data adapter for API responses. Reuse the bundled-data validation principles and add endpoint DTO validation; preserve loading/error/fallback flows, complete Golden snapshot and formula trace; never silently reuse a preset after draft assumptions change.
4. In a team review, lock this draft **before** either backend module changes field names. Run `npm run typecheck`, `npm run lint`, `npm test`, `npm run build` and one real E2E run. Day 1 alone is **not** a complete G1 sign-off.


## v4 boundary corrections

`ScenarioSelection`, `DecisionBriefRef`, endpoint requests/responses and envelopes are declared in `lib/contracts.ts`. A selected Brief has `scenarioId`, `status: "selected"` and an existing feasible option. A no-feasible Brief has `scenarioId`, `status: "no_feasible_option"`, `recommendedOptionId: null`, ordered `constraintViolations`, and `message`; no metric delta is computed and no approval is enabled. Boardroom must match the request scenario and immutable simulation selection. For no-feasible selection, return empty `agentOutputs` and `criticIssues`, the no-feasible Brief, and `numericGuardrail: {passed: true, rejectedClaims: []}`; do not call a model to invent a winner.

Selection is independently evaluated per scenario. Filter infeasible cells, stockout probability above the inclusive threshold, and cash P90 above the inclusive ceiling. Sort eligible cells by expected TCO ascending, then by option ID for deterministic ties. Violations are ordered D0/D1/D2, then infeasible/stockout_threshold/cash_ceiling. Any draft edit requires a new simulation. The local successful mock adapter remains `MockData`; API no-feasible results use the discriminated API DTO and the dedicated no-feasible UI, never a forced `MockData` cast. Runtime bundled-data validation is in `lib/validation.ts`; future HTTP adapters must validate endpoint DTOs before applying them.

The locked 26,000-unit forecast is an explicit synthetic assumption recorded on PDF page 4. Historical demand totals 25,936 units; no estimator that turns that history into 26,000 is claimed. The 2,340-unit difference is above the rolling A-floor benchmark; D1 total procurement exceeds realised demand by 3,900 units. Holding/stockout remain mock aggregates, not computed physical inventory costs.

