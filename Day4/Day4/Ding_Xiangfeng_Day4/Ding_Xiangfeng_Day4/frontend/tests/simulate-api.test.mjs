import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { Buffer } from "node:buffer";
import process from "node:process";
import ts from "typescript";

const root = path.resolve(import.meta.dirname, "..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const mock = JSON.parse(read("demo_data/causora_day1_mock.json"));
const metricsJs = ts.transpileModule(read("lib/metrics.ts"), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const metrics = await import(`data:text/javascript;base64,${Buffer.from(metricsJs).toString("base64")}`);
const apiJs = ts.transpileModule(read("lib/simulate-api.ts"), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const api = await import(`data:text/javascript;base64,${Buffer.from(apiJs).toString("base64")}`);

test("actual backend reviewed v2 wire response validates without development opt-in", async () => {
  const fixture = JSON.parse(read("tests/fixtures/reviewed-v2-TEST_FIXTURE_ONLY.json"));
  const headers = new globalThis.Headers(fixture.headers);
  const previous = process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE;
  try {
    delete process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE;
    const result = api.validateReviewedV2Success(fixture.response, fixture.request, headers);
    assert.equal(result.integrationMode, "reviewed-v2");
    assert.equal(result.development.executionContext.decisionReady, true);
    const transport = await api.postSimulate(fixture.request, async () => new globalThis.Response(JSON.stringify(fixture.response), { status: 200, headers }));
    assert.equal(transport.integrationMode, "reviewed-v2");
    for (const mutate of [
      (body) => { body.data.executionContext.policyStatus = "unapproved_development_only"; },
      (body) => { body.data.traces.baseline.D1.runIdentity.reviewRecordSha256 = "f".repeat(64); },
      (body) => { body.data.traces.baseline.D1.parameters.find((p) => p.key.startsWith("contract.")).provenance.kind = "unreviewed_development_contract"; },
      (body) => { body.data.traces.baseline.D1.stockoutProbability.denominatorRuns += 1; },
      (body) => { body.data.traces.baseline.D1.samplePath.weeks.pop(); }
    ]) {
      const bad = structuredClone(fixture.response); mutate(bad);
      assert.throws(() => api.validateReviewedV2Success(bad, fixture.request, headers));
    }
    assert.throws(() => api.validateReviewedV2Success(fixture.response, fixture.request, new globalThis.Headers()));
  } finally {
    if (previous === undefined) delete process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE;
    else process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE = previous;
  }
});

const makeRequest = (overrides = {}) => api.buildSimulateRequest({
  datasetId: "ds-001",
  scenarios: structuredClone(mock.scenarios),
  options: structuredClone(mock.options),
  selectedScenarioId: "baseline",
  demandShift: 0,
  riskThresholdPct: 12,
  budgetCeilingUsd: 480000,
  seed: mock.meta.seed,
  ...overrides
});

// This is a test-only contract fixture derived from saved cells; it is never a simulation result.
function testOnlySuccess(request) {
  const simulation = structuredClone(mock.simulation);
  simulation.simulationId = "sim-test-contract-only";
  simulation.seed = request.seed;
  simulation.dataVersion = mock.meta.dataVersion;
  simulation.formulaVersion = "tco-v1";
  simulation.weeks = 104;
  simulation.monteCarloRuns = 1;
  const deltas = request.scenarios.flatMap((scenario) => request.options.map((option) => metrics.decisionDelta({ ...mock, scenarios: request.scenarios, options: request.options, simulation }, scenario.id, option.id, "D0")));
  const selections = Object.fromEntries(request.scenarios.map((scenario) => [scenario.id, metrics.selectScenarioOption({ ...mock, scenarios: request.scenarios, options: request.options, simulation }, scenario.id, request.riskThreshold, request.budgetCeilingUsd)]));
  return { schemaVersion: "causora.contract.v1", dataVersion: mock.meta.dataVersion, requestId: "req-test-contract-only", data: { simulation, deltas, selections } };
}

// This generated object is a TEST_FIXTURE_ONLY wire-shape check, not a Monte Carlo response.
function unreviewedV2TestFixture(request) {
  const base = testOnlySuccess(request);
  const dataVersion = "test-UNREVIEWED_DEV_ONLY-fixture";
  const simulation = base.data.simulation;
  simulation.simulationId = "sim-unreviewed-test-fixture";
  simulation.dataVersion = dataVersion;
  simulation.monteCarloRuns = 1;
  for (const rows of Object.values(simulation.matrix)) for (const row of rows) { row.stockoutProbability = 0; row.serviceLevel = 1; }
  const modelData = { ...mock, scenarios: request.scenarios, options: request.options, simulation };
  const deltas = request.scenarios.flatMap((scenario) => request.options.map((option) => metrics.decisionDelta(modelData, scenario.id, option.id, "D0")));
  const selections = Object.fromEntries(request.scenarios.map((scenario) => [scenario.id, metrics.selectScenarioOption(modelData, scenario.id, request.riskThreshold, request.budgetCeilingUsd)]));
  const start = Date.parse("2026-10-04T00:00:00Z");
  const weeks = Array.from({ length: 104 }, (_, index) => ({
    week: index + 1, startDate: new Date(start + index * 7 * 86400000).toISOString().slice(0, 10),
    openingUnits: 100, arrivalsA: 0, arrivalsB: 0, demandUnits: 10, availableUnits: 100, fulfilledUnits: 10, lostUnits: 0, endingUnits: 90,
    onOrderUnitsBefore: 0, inventoryPositionBefore: 90, reorderPointUnits: 20, orderedA: 0, orderedB: 0,
    sampledLeadDaysA: null, sampledLeadDaysB: null, plannedArrivalWeekA: null, plannedArrivalWeekB: null, onOrderUnitsAfter: 0,
    holdingRawUsd: "0", stockoutLossRawUsd: "0", basePurchaseRawUsd: "0", renewalPremiumRawUsd: "0", terminationFeeRawUsd: "0"
  }));
  const traces = Object.fromEntries(request.scenarios.map((scenario) => [scenario.id, Object.fromEntries(request.options.map((option) => {
    const cell = simulation.matrix[scenario.id].find((row) => row.optionId === option.id);
    const components = Object.entries(cell.breakdown).map(([key, valueUsd]) => ({ key, formula: `TEST_FIXTURE_ONLY: ${key}`, inputKeys: ["dev.fixture"], valueUsd, roundingAudit: { rawMeanUsd: String(valueUsd), displayedValueUsd: valueUsd, displayedMinusRawMeanUsd: "0", method: "test fixture; no statistical claim" } }));
    return [option.id, {
      traceSchemaVersion: "causora.formula-trace.v1", simulationId: simulation.simulationId, dataVersion, formulaVersion: "tco-v1", scenarioId: scenario.id, optionId: option.id,
      runIdentity: { executionMode: "unreviewed_development_only", reviewRecordId: null, reviewRecordSha256: null, contractPayloadSha256: "a".repeat(64), policyApprovalReference: "TEST_FIXTURE_ONLY", policyConfigurationId: "TEST_FIXTURE_ONLY", policySha256: "b".repeat(64), contractApprovalReference: "TEST_FIXTURE_ONLY", contractReleaseRecordSha256: "c".repeat(64) },
      parameters: [{ key: "dev.fixture", value: 1, unit: "test-only", provenance: { kind: "unreviewed_development_assumption", status: "unreviewed_development_only", sourceId: "TEST_FIXTURE_ONLY", sourceFile: null, sourceSha256: null, evidenceIds: [], reviewRecordId: null, reviewRecordSha256: null, note: "Synthetic interface fixture only; never a calculation input." } }],
      components, expectedTcoUsd: cell.expectedTco,
      stockoutProbability: { value: 0, numeratorStockoutRuns: 0, denominatorRuns: 1, definition: "trials_with_at_least_one_lost_unit / monteCarloRuns" },
      serviceLevel: { value: 1, fulfilledUnitsAllRuns: 1, demandUnitsAllRuns: 1, definition: "fulfilled_units_all_runs / demand_units_all_runs" },
      cashOutflowP90: { valueUsd: cell.cashOutflowP90, method: "nearest_rank_ceil_0.90N", percentile: 0.9, rankOneBased: 1, denominatorRuns: 1, includedCashComponents: ["purchase", "holding", "renewalPremium", "terminationFee"], excludedNonCashComponents: ["stockoutLoss"], perRunRounding: "whole_usd_half_even" },
      summaryRoundingRule: "TEST_FIXTURE_ONLY", samplePath: { sampleRunIndex: 0, classification: "single_realised_trial_not_aggregate", note: "This test fixture is not an average, aggregate, or expectation.", weeks }
    }];
  }))]));
  return { schemaVersion: "causora.contract.v2", dataVersion, requestId: "req-unreviewed-test-fixture", data: { simulation, deltas, selections, traces, executionContext: { mode: "unreviewed_development_only", banner: "UNREVIEWED — DEVELOPMENT ONLY. NOT DECISION-READY.", humanReviewStatus: "not_reviewed_development_only", policyStatus: "unapproved_development_only", contractReleaseStatus: "not_released_development_only", decisionReady: false } } };
}

test("request builder preserves fixed options and maps shock, fractional risk, budget, seed and dataset", () => {
  const sourceScenarios = structuredClone(mock.scenarios);
  const request = makeRequest({ selectedScenarioId: "demand-drop", demandShift: -10, riskThresholdPct: 8.5, budgetCeilingUsd: 415000 });
  assert.equal(request.schemaVersion, "causora.contract.v1");
  assert.equal(request.datasetId, "ds-001");
  assert.equal(request.riskThreshold, 0.085);
  assert.equal(request.budgetCeilingUsd, 415000);
  assert.equal(request.seed, mock.meta.seed);
  assert.deepEqual(request.options, mock.options);
  const changed = request.scenarios.find((scenario) => scenario.id === "demand-drop");
  assert.equal(changed.demandShock, -10);
  assert.equal(changed.demandUnits24m, 23400);
  assert.deepEqual(mock.scenarios, sourceScenarios, "the imported frozen data must not be mutated");
  assert.throws(() => makeRequest({ budgetCeilingUsd: 1.5 }), /whole USD/);
  assert.throws(() => makeRequest({ riskThresholdPct: 101 }), /outside/);
});

test("test-only v1 fixture passes the strict envelope, matrix, accounting, delta and selection validator", () => {
  const request = makeRequest();
  const response = testOnlySuccess(request);
  assert.equal(response.data.simulation.monteCarloRuns, 1);
  assert.match(response.data.simulation.simulationId, /test-contract-only/);
  assert.doesNotThrow(() => api.validateSimulateSuccess(response, request));
});

test("v2 development response requires explicit opt-in/headers and a complete non-approved trace", () => {
  const request = makeRequest();
  const response = unreviewedV2TestFixture(request);
  const headers = new globalThis.Headers({ "x-causora-review-status": "unreviewed-development-only", "x-causora-execution-mode": "unreviewed-development-only" });
  const previous = process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE;
  try {
    delete process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE;
    assert.throws(() => api.validateUnreviewedV2Development(response, request, headers), /explicit UNREVIEWED_DEV_ONLY frontend opt-in/);
    process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE = "UNREVIEWED_DEV_ONLY";
    const result = api.validateUnreviewedV2Development(response, request, headers);
    assert.equal(result.integrationMode, "unreviewed-v2-dev");
    assert.equal(result.development.executionContext.decisionReady, false);
    assert.equal(Object.keys(result.development.traces).length, 3);
    assert.equal(result.development.traces.baseline.D0.samplePath.weeks.length, 104);
    assert.throws(() => api.validateUnreviewedV2Development(response, request, new globalThis.Headers()), /required execution\/review\/contract headers/);
    const decisionReady = structuredClone(response);
    decisionReady.data.executionContext.decisionReady = true;
    assert.throws(() => api.validateUnreviewedV2Development(decisionReady, request, headers), /decision-ready development status/);
    const incompleteTrace = structuredClone(response);
    incompleteTrace.data.traces.baseline.D0.samplePath.weeks[103].week = 103;
    assert.throws(() => api.validateUnreviewedV2Development(incompleteTrace, request, headers), /invalid sequence/);
  } finally {
    if (previous === undefined) delete process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE;
    else process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE = previous;
  }
});

test("validator rejects mock/zero-run/version/seed and inconsistent accounting, purchase, delta or winner", () => {
  const request = makeRequest();
  const mutations = [
    (r) => { r.schemaVersion = "causora.contract.v99"; },
    (r) => { r.data.simulation.simulationId = "saved-mock-snapshot"; },
    (r) => { r.data.simulation.monteCarloRuns = 0; },
    (r) => { r.data.simulation.seed += 1; },
    (r) => { r.data.simulation.formulaVersion = "unknown"; },
    (r) => { r.data.simulation.dataVersion = "other-version"; },
    (r) => { r.data.simulation.matrix.baseline[0].breakdown.holding += 1; },
    (r) => { r.data.simulation.matrix.baseline[0].breakdown.purchase += 2; },
    (r) => { r.data.deltas.find((d) => d.scenarioId === "baseline" && d.optionId === "D1").deltaTco += 1; },
    (r) => { r.data.selections.baseline.recommendedOptionId = "D2"; }
  ];
  for (const mutate of mutations) {
    const response = structuredClone(testOnlySuccess(request));
    mutate(response);
    assert.throws(() => api.validateSimulateSuccess(response, request));
  }
});

test("live Matrix recommendation styling derives from validated selections, not the response tone hint", () => {
  const request = makeRequest();
  const response = testOnlySuccess(request);
  const selection = response.data.selections.baseline;
  assert.equal(selection.status, "selected");
  const winnerId = selection.recommendedOptionId;
  const loserId = request.options.find((option) => option.id !== winnerId).id;
  const winnerCell = response.data.simulation.matrix.baseline.find((cell) => cell.optionId === winnerId);
  const loserCell = response.data.simulation.matrix.baseline.find((cell) => cell.optionId === loserId);
  winnerCell.tone = "neutral";
  loserCell.tone = "recommended";
  assert.doesNotThrow(() => api.validateSimulateSuccess(response, request), "tone remains a validated enum but is not winner authority");
  assert.equal(metrics.displayMatrixTone(winnerCell, selection), "recommended");
  assert.equal(metrics.displayMatrixTone(loserCell, selection), "neutral");
});

test("HTTP client posts only to the configured v1 endpoint and accepts only a valid success envelope", async () => {
  const request = makeRequest();
  const response = testOnlySuccess(request);
  const previousBase = process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL;
  process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL = "http://localhost:8000/";
  try {
    assert.equal(api.getSimulateEndpoint(), "http://localhost:8000/api/simulate");
    let observedUrl;
    let observedInit;
    const result = await api.postSimulate(request, async (url, init) => {
      observedUrl = url;
      observedInit = init;
      return { ok: true, status: 200, json: async () => response };
    });
    assert.equal(observedUrl, "http://localhost:8000/api/simulate");
    assert.equal(observedInit.method, "POST");
    assert.equal(observedInit.cache, "no-store");
    assert.deepEqual(JSON.parse(observedInit.body), request);
    assert.equal(result.integrationMode, "v1");
    assert.equal(result.response.requestId, "req-test-contract-only");
  } finally {
    if (previousBase === undefined) delete process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL;
    else process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL = previousBase;
  }
});

test("HTTP client opts into the marked v2 development adapter only when explicitly configured", async () => {
  const request = makeRequest();
  const response = unreviewedV2TestFixture(request);
  const previousBase = process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL;
  const previousMode = process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE;
  process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL = "http://localhost:8000";
  process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE = "UNREVIEWED_DEV_ONLY";
  try {
    const result = await api.postSimulate(request, async () => ({
      ok: true, status: 200,
      headers: new globalThis.Headers({ "x-causora-review-status": "unreviewed-development-only", "x-causora-execution-mode": "unreviewed-development-only" }),
      json: async () => response
    }));
    assert.equal(result.integrationMode, "unreviewed-v2-dev");
    assert.equal(result.response.schemaVersion, "causora.contract.v1", "the shared UI model is projected only after strict v2 dev validation");
    assert.equal(result.response.requestId, "req-unreviewed-test-fixture");
    assert.equal(result.development.executionContext.policyStatus, "unapproved_development_only");
  } finally {
    if (previousBase === undefined) delete process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL;
    else process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL = previousBase;
    if (previousMode === undefined) delete process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE;
    else process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE = previousMode;
  }
});

test("HTTP errors stay errors and retain the API request ID instead of applying a saved row as live", async () => {
  const request = makeRequest();
  await assert.rejects(api.postSimulate(request, async () => ({
    ok: false,
    status: 503,
    json: async () => ({ schemaVersion: "causora.contract.v1", requestId: "req-unreviewed", error: { code: "simulation_failed", message: "Monte Carlo backend is not ready.", requestId: "req-unreviewed" } })
  })), (error) => error.name === "SimulationApiError" && error.status === 503 && error.requestId === "req-unreviewed" && /not ready/.test(error.message));
});
