import test from "node:test";
import assert from "node:assert/strict";
import process from "node:process";
import ts from "typescript";
import fs from "node:fs";
import path from "node:path";
import { Buffer } from "node:buffer";

const root = path.resolve(import.meta.dirname, "..");
const source = fs.readFileSync(path.join(root, "lib/golden-health.ts"), "utf8");
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const healthApi = await import(`data:text/javascript;base64,${Buffer.from(code).toString("base64")}`);
const good = {
  schemaVersion: "causora.contract.v1",
  dataVersion: "UNREVIEWED_DEV_ONLY",
  requestId: "req-health-test",
  data: {
    service: "ready",
    simulation: "unreviewed_development_only",
    evidence: "not_reviewed_development_only",
    missingReasons: ["human_review_pending", "simulation_policy_unapproved", "trace_contract_unconfirmed"],
    banner: "UNREVIEWED — DEVELOPMENT ONLY. NOT DECISION-READY."
  }
};

test("health endpoint follows the configured API origin and defaults to same-origin proxy", () => {
  const previous = process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL;
  try {
    process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL = "https://api.example.test/root///";
    assert.equal(healthApi.getHealthEndpoint(), "https://api.example.test/root/health");
    delete process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL;
    assert.equal(healthApi.getHealthEndpoint(), "/health");
  } finally {
    if (previous === undefined) delete process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL;
    else process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL = previous;
  }
});

test("health probe is a credential-free no-store GET and accepts reachability without promoting pending gates", async () => {
  const previous = process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL;
  process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL = "http://localhost:8000";
  let observed;
  const result = await healthApi.probeBackendHealth(async (url, init) => {
    observed = { url, init };
    return new Response(JSON.stringify(good), { status: 200, headers: { "content-type": "application/json" } });
  });
  assert.equal(observed.url, "http://localhost:8000/health");
  assert.equal(observed.init.method, "GET");
  assert.equal(observed.init.cache, "no-store");
  assert.equal(observed.init.credentials, "omit");
  assert.equal(observed.init.headers.accept, "application/json");
  assert.equal(result.simulation, "unreviewed_development_only");
  assert.deepEqual(result.missingReasons, good.data.missingReasons);
  assert.match(result.banner, /NOT DECISION-READY/);
  if (previous === undefined) delete process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL;
  else process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL = previous;
});

test("health probe rejects non-ready and malformed responses", async () => {
  await assert.rejects(
    () => healthApi.probeBackendHealth(async () => new Response(JSON.stringify({ ...good, data: { ...good.data, service: "source_files_unavailable" } }), { status: 200 })),
    (error) => error.code === "invalid_response"
  );
  await assert.rejects(
    () => healthApi.probeBackendHealth(async () => new Response("{}", { status: 503 })),
    (error) => error.code === "unavailable" && /HTTP 503/.test(error.message)
  );
});

test("health probe reports a short timeout and aborts its request", async () => {
  let aborted = false;
  await assert.rejects(
    () => healthApi.probeBackendHealth((_url, init) => new Promise((_resolve, reject) => {
      init.signal.addEventListener("abort", () => { aborted = true; reject(new Error("aborted")); }, { once: true });
    }), 15),
    (error) => error.code === "timeout"
  );
  assert.equal(aborted, true);
});
