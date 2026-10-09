import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { Buffer } from "node:buffer";
import { TextEncoder } from "node:util";
import process from "node:process";
import ts from "typescript";

const root = path.resolve(import.meta.dirname, "..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const fixture = JSON.parse(read("tests/fixtures/reviewed-v2-TEST_FIXTURE_ONLY.json"));

function dataUrl(code) {
  return `data:text/javascript;base64,${Buffer.from(code).toString("base64")}`;
}
function transpile(file, replacements = {}) {
  let code = ts.transpileModule(read(file), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
  for (const [source, target] of Object.entries(replacements)) {
    code = code.replaceAll(`from "${source}"`, `from "${target}"`).replaceAll(`from '${source}'`, `from '${target}'`);
  }
  return code;
}

const metricsUrl = dataUrl(transpile("lib/metrics.ts"));
const boardroomTemplateUrl = dataUrl(transpile("lib/boardroom-template.ts", { "./metrics": metricsUrl }));
const boardroomUrl = dataUrl(transpile("lib/boardroom-api.ts", { "./boardroom-template": boardroomTemplateUrl }));
const simulateUrl = dataUrl(transpile("lib/simulate-api.ts"));
const evidenceUrl = dataUrl(transpile("lib/evidence-api.ts", { "./boardroom-api": boardroomUrl }));
const locators = await import(dataUrl(transpile("lib/evidence-locators.ts")));
const boardroom = await import(boardroomUrl);
const boardroomTemplate = await import(boardroomTemplateUrl);
const metrics = await import(metricsUrl);
const simulate = await import(simulateUrl);
const evidence = await import(evidenceUrl);
const goldenUrl = dataUrl(transpile("lib/golden-cache.ts", {
  "./boardroom-api": boardroomUrl,
  "./simulate-api": simulateUrl,
  "./evidence-api": evidenceUrl
}));
const golden = await import(goldenUrl);

const liveResult = simulate.validateReviewedV2Success(fixture.response, fixture.request, new Headers(fixture.headers));
const liveRun = {
  request: fixture.request,
  response: liveResult.response,
  integrationMode: liveResult.integrationMode,
  development: liveResult.development,
  receivedAt: "2026-10-08T00:00:00.000Z"
};

function matchingBoardroomResponse(run, requestId = "br-req-test") {
  const scenarioId = "baseline";
  const selection = run.response.data.selections[scenarioId];
  assert.equal(selection?.status, "selected", "fixture scenario must have a selection");
  const rows = run.response.data.simulation.matrix[scenarioId];
  const baselineHolding = rows.find((row) => row.optionId === "D0").breakdown.holding;
  const holdingCostDeltaUsd = Object.fromEntries(rows.map((row) => [row.optionId, row.breakdown.holding - baselineHolding]));
  const scenario = run.request.scenarios.find((item) => item.id === scenarioId);
  return {
    schemaVersion: "causora.contract.v1",
    dataVersion: run.response.data.simulation.dataVersion,
    requestId,
    data: {
      scenarioId,
      agentOutputs: ["CFO", "COO", "Risk"].map((role) => ({
        role,
        accent: `role-${role.toLowerCase()}`,
        focus: `${role} lens`,
        headline: `${role} test-only headline`,
        body: `${role} template text with no unbound numeric claim.`,
        metrics: ["delta_tco"],
        status: "Aligned"
      })),
      criticIssues: [{
        severity: "Watch",
        headline: "Test-only evidence challenge",
        body: "The fixture preserves the exact scenario identity.",
        evidenceIds: ["EV-021", "EV-024"],
        mechanism: {
          scenarioId,
          forecastBasis: "locked-at-renewal",
          lockedForecastUnits24m: 26000,
          minPurchaseUnitsA: 15600,
          scenarioDemandUnits24m: scenario.demandUnits24m,
          committedExcessUnits: 0,
          holdingCostDeltaUsd
        }
      }],
      brief: {
        scenarioId,
        status: "selected",
        recommendedOptionId: selection.recommendedOptionId,
        recommendation: "Test-only recommendation bound to the selected option.",
        rationale: "Synthetic test fixture only; no model result is represented.",
        metricRefs: ["delta_tco", "stockout_probability", "cash_outflow_p90"],
        formula: "expected TCO = purchase + holding + stockout loss + renewal premium + termination fee",
        formulaVersion: run.response.data.simulation.formulaVersion,
        formulaNotes: ["Test fixture only"],
        guardrail: "Test-only numerical guardrail fixture."
      },
      numericGuardrail: { passed: true, rejectedClaims: [] }
    }
  };
}

const boardroomRequestId = "br-req-test";
function responseHeaders(requestId = boardroomRequestId, provider = "primary", critic = "complete") {
  return new Headers({
    "x-request-id": requestId,
    "x-causora-provider-mode": provider,
    "x-causora-critic-status": critic,
    "cache-control": "no-store"
  });
}
const boardroomResponse = matchingBoardroomResponse(liveRun, boardroomRequestId);
const request = boardroom.boardroomRequestFor(liveRun, "baseline");
const validatedBoardroom = boardroom.validateBoardroomSuccess(boardroomResponse, request, liveRun, responseHeaders(), boardroomRequestId);

function evidenceRecord(overrides = {}) {
  return {
    id: "EV-021",
    sourceFile: "supplier_a_agreement.pdf",
    page: 3,
    quote: "Annual renewal terms and minimum purchase requirements apply.",
    locatorBbox: null,
    extractedField: "renewal_terms",
    extractedValue: "annual renewal",
    matchMethod: "exact",
    matchScore: 1,
    quoteMatched: true,
    ...overrides
  };
}
function evidenceEnvelope(record = evidenceRecord(), dataVersion = liveRun.response.data.simulation.dataVersion, requestId = "ev-req-test") {
  return { schemaVersion: "causora.contract.v1", dataVersion, requestId, data: { evidence: record } };
}

const simulationHeaders = new Headers(fixture.headers);

// These test fixtures are explicitly synthetic and are never accepted as evidence of a real team run.
test("Boardroom success requires reviewed v2, exact run identity, correlated request id, three roles, Critic and Numeric Guardrail", () => {
  assert.equal(validatedBoardroom.providerMode, "primary");
  assert.equal(validatedBoardroom.criticStatus, "complete");
  assert.equal(validatedBoardroom.identity.simulationId, liveRun.response.data.simulation.simulationId);
  assert.equal(validatedBoardroom.identity.simulationRequestId, liveRun.response.requestId);

  const fallback = boardroom.validateBoardroomSuccess(boardroomResponse, request, liveRun, responseHeaders(boardroomRequestId, "same-family-fallback"), boardroomRequestId);
  assert.equal(fallback.providerMode, "same-family-fallback");

  const wrongRequest = structuredClone(boardroomResponse);
  wrongRequest.requestId = "some-other-request";
  assert.throws(() => boardroom.validateBoardroomSuccess(wrongRequest, request, liveRun, responseHeaders(), boardroomRequestId), (error) => error.code === "stale_response");

  const wrongScenario = structuredClone(boardroomResponse);
  wrongScenario.data.scenarioId = "lead-stress";
  assert.throws(() => boardroom.validateBoardroomSuccess(wrongScenario, request, liveRun, responseHeaders(), boardroomRequestId), (error) => error.code === "stale_response");

  const rejected = structuredClone(boardroomResponse);
  rejected.data.numericGuardrail = { passed: false, rejectedClaims: ["unbound amount"] };
  assert.throws(() => boardroom.validateBoardroomSuccess(rejected, request, liveRun, responseHeaders(), boardroomRequestId), (error) => error.code === "numeric_guardrail_rejected");

  const incomplete = structuredClone(boardroomResponse);
  incomplete.data.agentOutputs.pop();
  assert.throws(() => boardroom.validateBoardroomSuccess(incomplete, request, liveRun, responseHeaders(), boardroomRequestId), (error) => error.code === "malformed_response");

  assert.throws(() => boardroom.validateBoardroomSuccess(boardroomResponse, request, { ...liveRun, integrationMode: "unreviewed-v2-dev", development: { ...liveRun.development, executionContext: { ...liveRun.development.executionContext, decisionReady: false } } }, responseHeaders(), boardroomRequestId), (error) => error.code === "review_pending");
});

test("Boardroom metric templates are declared and rendered from the matching Simulation", () => {
  const templated = structuredClone(boardroomResponse);
  templated.data.agentOutputs[0].body = "Expected change {{delta_tco}}.";
  const validated = boardroom.validateBoardroomSuccess(templated, request, liveRun, responseHeaders(), boardroomRequestId);
  const values = boardroomTemplate.boardroomMetricValues(liveRun, "baseline");
  const optionId = liveRun.response.data.selections.baseline.recommendedOptionId;
  const delta = liveRun.response.data.deltas.find((item) => item.scenarioId === "baseline" && item.optionId === optionId);
  assert.ok(delta);
  assert.equal(values.delta_tco, metrics.signedMoney(delta.deltaTco));
  assert.equal(boardroomTemplate.renderBoardroomBody(validated.response.data.agentOutputs[0].body, values), `Expected change ${metrics.signedMoney(delta.deltaTco)}.`);

  const undeclared = structuredClone(templated);
  undeclared.data.agentOutputs[0].metrics = ["stockout_probability"];
  assert.throws(() => boardroom.validateBoardroomSuccess(undeclared, request, liveRun, responseHeaders(), boardroomRequestId), (error) => error.code === "malformed_response" && /without declaring it in metrics/.test(error.message));
  const unsupported = structuredClone(templated);
  unsupported.data.agentOutputs[0].body = "Expected change {{unit_margin}}.";
  assert.throws(() => boardroom.validateBoardroomSuccess(unsupported, request, liveRun, responseHeaders(), boardroomRequestId), (error) => error.code === "malformed_response" && /unsupported metric token/.test(error.message));
});

test("Boardroom client posts only v1 identity with no credentials, no-store, explicit request id, and classifies missing endpoint", async () => {
  const previous = process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL;
  process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL = "http://localhost:8000/";
  try {
    assert.equal(boardroom.getBoardroomEndpoint(), "http://localhost:8000/api/boardroom");
    let observed;
    const result = await boardroom.postBoardroom(liveRun, "baseline", async (url, init) => {
      observed = { url, init };
      return new Response(JSON.stringify(boardroomResponse), { status: 200, headers: responseHeaders() });
    }, undefined, boardroomRequestId);
    assert.equal(result.requestId, boardroomRequestId);
    assert.equal(observed.url, "http://localhost:8000/api/boardroom");
    assert.equal(observed.init.method, "POST");
    assert.equal(observed.init.cache, "no-store");
    assert.equal(observed.init.credentials, "omit");
    assert.equal(observed.init.headers["X-Request-Id"], boardroomRequestId);
    assert.deepEqual(JSON.parse(observed.init.body), request);

    await assert.rejects(
      () => boardroom.postBoardroom(liveRun, "baseline", async () => new Response(JSON.stringify({ error: { code: "not_found", message: "missing" } }), { status: 404 }), undefined, boardroomRequestId),
      (error) => error.code === "endpoint_missing" && error.retryable === false
    );
    await assert.rejects(
      () => boardroom.postBoardroom({ ...liveRun, integrationMode: "unreviewed-v2-dev" }, "baseline", async () => { throw new Error("must not fetch"); }),
      (error) => error.code === "review_pending"
    );
  } finally {
    if (previous === undefined) delete process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL;
    else process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL = previous;
  }
});

test("Critic-unavailable and provider failures preserve retry classification without altering simulation", async () => {
  await assert.rejects(
    () => boardroom.postBoardroom(liveRun, "baseline", async () => new Response(JSON.stringify({ schemaVersion: "causora.contract.v1", dataVersion: liveRun.response.data.simulation.dataVersion, requestId: boardroomRequestId, data: boardroomResponse.data }), { status: 200, headers: responseHeaders(boardroomRequestId, "primary", "unavailable") }), undefined, boardroomRequestId),
    (error) => error.code === "critic_unavailable" && error.retryable === true
  );
  await assert.rejects(
    () => boardroom.postBoardroom(liveRun, "baseline", async () => new Response(JSON.stringify({ error: { code: "provider_timeout", message: "timeout" } }), { status: 504, headers: { "x-request-id": boardroomRequestId } }), undefined, boardroomRequestId),
    (error) => error.code === "provider_timeout" && error.retryable === true
  );
  assert.equal(liveRun.response.data.simulation.simulationId, fixture.response.data.simulation.simulationId, "downstream errors must not mutate the validated simulation");
});

test("Evidence validator rejects stale ids, traversal, invalid pages and malformed PDF bboxes", () => {
  const version = liveRun.response.data.simulation.dataVersion;
  const valid = evidence.validateEvidenceSuccess(evidenceEnvelope(), "EV-021", version);
  assert.equal(valid.data.evidence.page, 3);
  assert.equal(valid.data.evidence.locatorBbox, null);
  assert.equal(evidence.evidenceSourceHref(valid.data.evidence), "/demo/supplier_a_agreement.pdf#page=3&zoom=page-width");
  assert.equal(evidence.evidenceSourceHref(evidenceRecord({ sourceFile: "../../private.pdf" })), null);
  assert.throws(() => evidence.validateEvidenceSuccess(evidenceEnvelope(), "EV-024", version), (error) => error.code === "stale_response");
  assert.throws(() => evidence.validateEvidenceSuccess(evidenceEnvelope(evidenceRecord({ sourceFile: "../supplier_a_agreement.pdf" })), "EV-021", version), (error) => error.code === "source_unavailable");
  assert.throws(() => evidence.validateEvidenceSuccess(evidenceEnvelope(evidenceRecord({ page: 0 })), "EV-021", version), (error) => error.code === "locator_invalid");
  assert.throws(() => evidence.validateEvidenceSuccess(evidenceEnvelope(evidenceRecord({ locatorBbox: [50, 50, 20, 20] })), "EV-021", version), (error) => error.code === "locator_invalid");
  assert.throws(() => evidence.validateEvidenceSuccess(evidenceEnvelope(), "EV-021", "other-data-version"), (error) => error.code === "stale_response");
});

test("Evidence client performs GET with omitted credentials and no-store, and maps a missing source to non-retryable", async () => {
  const version = liveRun.response.data.simulation.dataVersion;
  let observed;
  const result = await evidence.fetchEvidenceRecord("EV-021", version, async (url, init) => {
    observed = { url, init };
    const payload = evidenceEnvelope();
    payload.requestId = init.headers["X-Request-Id"];
    return new Response(JSON.stringify(payload), { status: 200, headers: { "x-request-id": payload.requestId } });
  });
  assert.equal(result.evidence.id, "EV-021");
  assert.equal(observed.url, "/api/evidence/EV-021");
  assert.equal(observed.init.method, "GET");
  assert.equal(observed.init.cache, "no-store");
  assert.equal(observed.init.credentials, "omit");
  await assert.rejects(
    () => evidence.fetchEvidenceRecord("EV-021", version, async () => new Response(JSON.stringify({ error: { code: "not_found", message: "missing" } }), { status: 404 })),
    (error) => error.code === "not_found" && error.retryable === false
  );
});

test("PDF locator highlights only an API bbox or an exact quote on the cited page", () => {
  const viewport = { width: 600, height: 800, convertToViewportPoint: (x, y) => [x, 800 - y] };
  const item = { str: "Supplier minimum purchase commitment", transform: [1, 0, 0, 1, 10, 100], width: 220, height: 12 };
  const exact = locators.resolveEvidenceLocator([item], "minimum purchase commitment", null, viewport);
  assert.equal(exact?.source, "exact-source-text");
  assert.ok(exact?.box.width > 0);
  const apiBox = locators.resolveEvidenceLocator([], "unused", [30, 40, 90, 55], viewport);
  assert.equal(apiBox?.source, "api-bbox");
  assert.equal(locators.resolveEvidenceLocator([item], "a quote not in this PDF page", null, viewport), null);
  assert.equal(locators.resolveEvidenceLocator([], "unused", [90, 40, 30, 55], viewport), null);
});

test("Golden cache refuses TEST_FIXTURE_ONLY data and hash-mismatched stored runs", async () => {
  const evidenceRecords = ["EV-021", "EV-024"].map((id) => ({ requestId: `evidence-${id}`, evidence: evidenceRecord({ id }) }));
  const decision = {
    decision: "Approved",
    recordedAt: "2026-10-08T00:00:00.000Z",
    scope: "browser-local-only",
    identity: validatedBoardroom.identity,
    optionId: liveRun.response.data.selections.baseline.recommendedOptionId
  };
  const storage = {
    value: null,
    getItem() { return this.value; },
    setItem(_key, value) { this.value = value; },
    removeItem() { this.value = null; }
  };
  await assert.rejects(
    () => golden.saveVerifiedGoldenRun(liveRun, validatedBoardroom, simulationHeaders, evidenceRecords, decision, storage),
    /TEST_FIXTURE_ONLY data cannot be cached/
  );

  const corrupted = {
    schema: "causora.verified-golden.v1",
    createdAt: "2026-10-08T00:00:00.000Z",
    simulationRequest: fixture.request,
    simulationResponse: fixture.response,
    simulationHeaders: fixture.headers,
    scenarioId: "baseline",
    boardroomRequestId,
    boardroomResponse,
    boardroomHeaders: { "x-causora-provider-mode": "primary", "x-causora-critic-status": "complete" },
    evidenceRecords,
    humanDecision: decision,
    sha256: "0".repeat(64)
  };
  storage.value = JSON.stringify(corrupted);
  await assert.rejects(() => golden.loadVerifiedGoldenRun(storage), /SHA-256 integrity check failed/);
});

test("Unmatched Evidence stays viewable but cannot satisfy Verified Golden creation or reload", async () => {
  const version = liveRun.response.data.simulation.dataVersion;
  const unmatched = evidenceRecord({ quoteMatched: false, matchScore: 0 });
  assert.equal(evidence.validateEvidenceSuccess(evidenceEnvelope(unmatched), "EV-021", version).data.evidence.quoteMatched, false);
  const evidenceRecords = [
    { requestId: "evidence-EV-021", evidence: unmatched },
    { requestId: "evidence-EV-024", evidence: evidenceRecord({ id: "EV-024" }) }
  ];
  const decision = {
    decision: "Approved",
    recordedAt: "2026-10-08T00:00:00.000Z",
    scope: "browser-local-only",
    identity: validatedBoardroom.identity,
    optionId: liveRun.response.data.selections.baseline.recommendedOptionId
  };
  const rejectedStorage = { value: null, getItem() { return this.value; }, setItem(_key, value) { this.value = value; }, removeItem() { this.value = null; } };
  await assert.rejects(() => golden.saveVerifiedGoldenRun(liveRun, validatedBoardroom, simulationHeaders, evidenceRecords, decision, rejectedStorage), /quote was not matched/);

  const cleanFixture = JSON.parse(JSON.stringify(fixture, (_key, value) => typeof value === "string" ? value.replaceAll("TEST_FIXTURE_ONLY", "SYNTHETIC_TEST_ONLY") : value));
  const cleanSimulation = simulate.validateReviewedV2Success(cleanFixture.response, cleanFixture.request, new Headers(cleanFixture.headers));
  const cleanRun = { request: cleanFixture.request, response: cleanSimulation.response, integrationMode: cleanSimulation.integrationMode, development: cleanSimulation.development, receivedAt: "2026-10-08T00:00:00.000Z" };
  const cleanBoardroomResponse = matchingBoardroomResponse(cleanRun, boardroomRequestId);
  const cleanBoardroomRequest = boardroom.boardroomRequestFor(cleanRun, "baseline");
  const cleanBoardroom = boardroom.validateBoardroomSuccess(cleanBoardroomResponse, cleanBoardroomRequest, cleanRun, responseHeaders(), boardroomRequestId);
  const cleanDecision = { ...decision, identity: cleanBoardroom.identity, optionId: cleanRun.response.data.selections.baseline.recommendedOptionId };
  const matchedRecords = ["EV-021", "EV-024"].map((id) => ({ requestId: `evidence-${id}`, evidence: evidenceRecord({ id }) }));
  const storage = { value: null, getItem() { return this.value; }, setItem(_key, value) { this.value = value; }, removeItem() { this.value = null; } };
  await golden.saveVerifiedGoldenRun(cleanRun, cleanBoardroom, new Headers(cleanFixture.headers), matchedRecords, cleanDecision, storage);

  const stored = JSON.parse(storage.value);
  stored.evidenceRecords[0].evidence.quoteMatched = false;
  stored.evidenceRecords[0].evidence.matchScore = 0;
  const canonical = (value) => {
    if (value === null || typeof value !== "object") return JSON.stringify(value);
    if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
    return `{${Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => `${JSON.stringify(key)}:${canonical(child)}`).join(",")}}`;
  };
  const bytes = new TextEncoder().encode(canonical(Object.fromEntries(Object.entries(stored).filter(([key]) => key !== "sha256"))));
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  stored.sha256 = [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  storage.value = JSON.stringify(stored);
  await assert.rejects(() => golden.loadVerifiedGoldenRun(storage), /quote was not matched/);
});

test("Boardroom identity matcher rejects another simulation, request, dataVersion or scenario", () => {
  assert.equal(boardroom.isCurrentBoardroomRun(validatedBoardroom, liveRun, "baseline"), true);
  assert.equal(boardroom.isCurrentBoardroomRun(validatedBoardroom, liveRun, "lead-stress"), false);
  assert.equal(boardroom.isCurrentBoardroomRun(validatedBoardroom, { ...liveRun, response: { ...liveRun.response, requestId: "other" } }, "baseline"), false);
  assert.equal(boardroom.isCurrentBoardroomRun(validatedBoardroom, { ...liveRun, integrationMode: "unreviewed-v2-dev" }, "baseline"), false);
});
