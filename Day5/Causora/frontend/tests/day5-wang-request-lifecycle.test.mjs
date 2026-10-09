import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { Buffer } from "node:buffer";
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
const templateUrl = dataUrl(transpile("lib/boardroom-template.ts", { "./metrics": metricsUrl }));
const boardroomUrl = dataUrl(transpile("lib/boardroom-api.ts", { "./boardroom-template": templateUrl }));
const evidenceUrl = dataUrl(transpile("lib/evidence-api.ts", { "./boardroom-api": boardroomUrl }));
const simulateUrl = dataUrl(transpile("lib/simulate-api.ts"));
const boardroom = await import(boardroomUrl);
const evidence = await import(evidenceUrl);
const simulate = await import(simulateUrl);

const validated = simulate.validateReviewedV2Success(fixture.response, fixture.request, new Headers(fixture.headers));
const liveRun = {
  request: fixture.request,
  response: validated.response,
  integrationMode: validated.integrationMode,
  development: validated.development,
  receivedAt: "2026-10-10T00:00:00.000Z"
};

function boardroomEnvelope(requestId) {
  const scenarioId = "baseline";
  const selection = liveRun.response.data.selections[scenarioId];
  const rows = liveRun.response.data.simulation.matrix[scenarioId];
  const baselineHolding = rows.find((row) => row.optionId === "D0").breakdown.holding;
  return {
    schemaVersion: "causora.contract.v1",
    dataVersion: liveRun.response.data.simulation.dataVersion,
    requestId,
    data: {
      scenarioId,
      agentOutputs: ["CFO", "COO", "Risk"].map((role) => ({
        role, accent: role, focus: `${role} focus`, headline: `${role} fixture`,
        body: "Inspect the approved metric {{delta_tco}} before deciding.",
        metrics: ["delta_tco"], status: "Aligned"
      })),
      criticIssues: [{
        severity: "Watch", headline: "Fixture issue", body: "Fixture mechanism remains linked.", evidenceIds: ["EV-021"],
        mechanism: {
          scenarioId, forecastBasis: "locked-at-renewal", lockedForecastUnits24m: 26000,
          minPurchaseUnitsA: 15600,
          scenarioDemandUnits24m: liveRun.request.scenarios.find((item) => item.id === scenarioId).demandUnits24m,
          committedExcessUnits: 0,
          holdingCostDeltaUsd: Object.fromEntries(rows.map((row) => [row.optionId, row.breakdown.holding - baselineHolding]))
        }
      }],
      brief: {
        scenarioId, status: "selected", recommendedOptionId: selection.recommendedOptionId,
        recommendation: "Test fixture recommendation.", rationale: "Test fixture rationale.", metricRefs: ["delta_tco"],
        formula: "expected TCO = purchase + holding + stockout loss + renewal premium + termination fee",
        formulaVersion: liveRun.response.data.simulation.formulaVersion, formulaNotes: ["TEST_FIXTURE_ONLY"], guardrail: "Fixture guardrail."
      },
      numericGuardrail: { passed: true, rejectedClaims: [] }
    }
  };
}

function evidenceEnvelope(requestId) {
  return {
    schemaVersion: "causora.contract.v1",
    dataVersion: liveRun.response.data.simulation.dataVersion,
    requestId,
    data: { evidence: {
      id: "EV-021", sourceFile: "supplier_a_agreement.pdf", page: 3,
      quote: "Annual renewal terms and minimum purchase requirements apply.", locatorBbox: null,
      extractedField: "renewal_terms", extractedValue: "annual renewal", matchMethod: "exact", matchScore: 1, quoteMatched: true
    } }
  };
}

// These calls use only synthetic TEST_FIXTURE_ONLY envelopes and never contact a backend.
test("already-aborted Boardroom and Evidence signals fail closed before fetch is invoked", async () => {
  const boardroomAbort = new globalThis.AbortController();
  boardroomAbort.abort(new globalThis.DOMException("new simulation replaced this run", "AbortError"));
  let boardroomFetches = 0;
  await assert.rejects(
    () => boardroom.postBoardroom(liveRun, "baseline", async () => { boardroomFetches += 1; throw new Error("fetch must not run"); }, boardroomAbort.signal, "br-preaborted"),
    (error) => error.code === "stale_response" && error.requestId === "br-preaborted" && error.retryable === false
  );
  assert.equal(boardroomFetches, 0);

  const evidenceAbort = new globalThis.AbortController();
  evidenceAbort.abort(new globalThis.DOMException("new simulation replaced this run", "AbortError"));
  let evidenceFetches = 0;
  await assert.rejects(
    () => evidence.fetchEvidenceRecord("EV-021", liveRun.response.data.simulation.dataVersion, async () => { evidenceFetches += 1; throw new Error("fetch must not run"); }, evidenceAbort.signal),
    (error) => error.code === "stale_response" && error.retryable === false
  );
  assert.equal(evidenceFetches, 0);
});

test("Boardroom requires the response request-id header and envelope to exactly echo the outbound ID", async () => {
  let observed;
  await assert.rejects(
    () => boardroom.postBoardroom(liveRun, "baseline", async (_url, init) => {
      observed = init;
      return new Response(JSON.stringify(boardroomEnvelope("br-correlation")), {
        status: 200,
        headers: { "x-request-id": "other-request", "x-causora-provider-mode": "primary", "x-causora-critic-status": "complete" }
      });
    }, undefined, "br-correlation"),
    (error) => error.code === "stale_response" && error.requestId === "other-request"
  );
  assert.equal(observed.headers["X-Request-Id"], "br-correlation");
});

test("Evidence requires the response request-id header and envelope to exactly echo its outbound ID", async () => {
  let observed;
  await assert.rejects(
    () => evidence.fetchEvidenceRecord("EV-021", liveRun.response.data.simulation.dataVersion, async (_url, init) => {
      observed = init;
      return new Response(JSON.stringify(evidenceEnvelope("envelope-id")), { status: 200, headers: { "x-request-id": "other-request" } });
    }),
    (error) => error.code === "stale_response" && error.requestId === "other-request"
  );
  assert.match(observed.headers["X-Request-Id"], /^causora-ev-/);
});

test("syntactically valid but unsupported Evidence IDs remain a server-authoritative not-found response", async () => {
  let observedUrl;
  await assert.rejects(
    () => evidence.fetchEvidenceRecord("EV-999", liveRun.response.data.simulation.dataVersion, async (url) => {
      observedUrl = url;
      return new Response(JSON.stringify({ error: { code: "not_found", message: "unsupported server evidence ID" } }), { status: 404 });
    }),
    (error) => error.code === "not_found" && error.retryable === false
  );
  assert.equal(observedUrl, "/api/evidence/EV-999");
});

test("Evidence rejects a mutually consistent header/envelope that belongs to an older outbound request", async () => {
  await assert.rejects(
    () => evidence.fetchEvidenceRecord("EV-021", liveRun.response.data.simulation.dataVersion, async () =>
      new Response(JSON.stringify(evidenceEnvelope("older-ev-request")), { status: 200, headers: { "x-request-id": "older-ev-request" } })),
    (error) => error.code === "stale_response" && error.retryable === false
  );
});
