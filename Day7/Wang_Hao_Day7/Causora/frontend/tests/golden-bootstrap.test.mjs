import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { Buffer } from "node:buffer";
import ts from "typescript";

const frontend = path.resolve(import.meta.dirname, "..");
const urls = new Map();
function moduleUrl(file) {
  file = path.resolve(file);
  if (urls.has(file)) return urls.get(file);
  let code = ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 }
  }).outputText;
  code = code.replace(/from\s+["'](\.[^"']+)["']/g, (_, relative) => {
    const target = path.resolve(path.dirname(file), `${relative}.ts`);
    if (!target.startsWith(frontend + path.sep)) throw new Error("Module outside frontend");
    return `from "${moduleUrl(target)}"`;
  });
  const url = `data:text/javascript;base64,${Buffer.from(code).toString("base64")}`;
  urls.set(file, url);
  return url;
}

const { loadAvailableVerifiedGoldenRun, VERIFIED_GOLDEN_ASSET_PATH } = await import(moduleUrl(path.join(frontend, "lib/golden-bootstrap.ts")));
const { VERIFIED_GOLDEN_STORAGE_KEY } = await import(moduleUrl(path.join(frontend, "lib/golden-cache.ts")));
const goldenPath = path.resolve(frontend, "../verification/g4-final/verified_golden_e2e.json");
const goldenJson = fs.readFileSync(goldenPath, "utf8");
assert.equal(fs.readFileSync(path.join(frontend, "public/golden/verified_golden_e2e.json"), "utf8"), goldenJson, "published static Golden must be the complete genuine source record");
const goldenRecord = JSON.parse(goldenJson);
function responseFor(json = goldenJson, status = 200, contentType = "application/json") {
  return new Response(json, { status, headers: { "content-type": contentType } });
}

// This fixture is a captured real Day4 run and its browser-local decision is an automated UI-test artifact,
// not a new provider call, new user test, or business/release approval.
test("a fresh browser with empty storage loads the complete same-origin static Golden and validates it", async () => {
  let calls = 0;
  let request;
  const result = await loadAvailableVerifiedGoldenRun(null, async (input, init) => {
    calls += 1;
    request = { input, init };
    return responseFor();
  });
  assert.equal(calls, 1);
  assert.equal(request.input, VERIFIED_GOLDEN_ASSET_PATH);
  assert.equal(request.init.credentials, "same-origin");
  assert.equal(request.init.cache, "force-cache");
  assert.equal(result.source, "static-bundle");
  assert.equal(result.json, goldenJson);
  assert.equal(result.run.liveRun.response.data.simulation.simulationId, goldenRecord.simulationResponse.data.simulation.simulationId);
  assert.equal(result.run.evidenceRecords.length, goldenRecord.evidenceRecords.length);
  assert.equal(result.run.humanDecision.decision, "Rejected");
  assert.equal(result.run.humanDecision.scope, "browser-local-only");
});

test("a valid browser cache takes precedence and does not make a network request", async () => {
  let calls = 0;
  const storage = { getItem: (key) => key === VERIFIED_GOLDEN_STORAGE_KEY ? goldenJson : null, setItem() {}, removeItem() {} };
  const result = await loadAvailableVerifiedGoldenRun(storage, async () => { calls += 1; return responseFor(); });
  assert.equal(calls, 0);
  assert.equal(result.source, "browser-cache");
  assert.equal(result.json, goldenJson);
});

test("a tampered local cache falls back to the immutable static record", async () => {
  let calls = 0;
  const tampered = JSON.stringify({ ...goldenRecord, sha256: "0".repeat(64) });
  const storage = { getItem: (key) => key === VERIFIED_GOLDEN_STORAGE_KEY ? tampered : null, setItem() {}, removeItem() {} };
  const result = await loadAvailableVerifiedGoldenRun(storage, async () => { calls += 1; return responseFor(); });
  assert.equal(calls, 1);
  assert.equal(result.source, "static-bundle");
  assert.equal(result.run.sha256, goldenRecord.sha256);
});

test("an invalid bundled record or non-JSON response is rejected rather than shown as verified", async () => {
  const tampered = JSON.stringify({ ...goldenRecord, sha256: "0".repeat(64) });
  await assert.rejects(() => loadAvailableVerifiedGoldenRun(null, async () => responseFor(tampered)), /failed production validation/i);
  await assert.rejects(() => loadAvailableVerifiedGoldenRun(null, async () => responseFor(goldenJson, 200, "application/octet-stream")), /application\/json/i);
});

test("the bundled Golden loader rejects non-same-origin URLs before fetching", async () => {
  let calls = 0;
  await assert.rejects(() => loadAvailableVerifiedGoldenRun(null, async () => { calls += 1; return responseFor(); }, "//attacker.example/golden.json"), /same-origin/i);
  assert.equal(calls, 0);
});
