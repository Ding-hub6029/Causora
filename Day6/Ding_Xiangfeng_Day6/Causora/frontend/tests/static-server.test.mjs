import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import net from "node:net";
import http from "node:http";
import process from "node:process";
import path from "node:path";

test("Production preview serves correct source types and keeps source files private", async () => {
  const probe = net.createServer();
  await new Promise(resolve => probe.listen(0, "127.0.0.1", resolve));
  const port = probe.address().port;
  await new Promise(resolve => probe.close(resolve));
  const child = spawn(process.execPath, ["scripts/serve-static.mjs"], { cwd: path.resolve(import.meta.dirname, ".."), env: { ...process.env, PORT: String(port), HOST: "127.0.0.1" }, stdio: ["ignore", "pipe", "pipe"] });
  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("Static server startup timed out")), 8000);
      child.stdout.once("data", () => { clearTimeout(timer); resolve(); });
      child.once("error", err => { clearTimeout(timer); reject(err); });
      child.once("exit", code => { clearTimeout(timer); if (code !== null) reject(new Error(`Static server exited ${code}`)); });
    });
    const base = `http://127.0.0.1:${port}`;
    const home = await fetch(base); assert.equal(home.status, 200); assert.match(await home.text(), /Causora/);
    for (const [file, type] of [["supplier_a_agreement.pdf", "application/pdf"], ["historical_demand.csv", "text/csv"], ["supplier_delivery_history.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]]) {
      const response = await fetch(`${base}/demo/${file}`); assert.equal(response.status, 200); assert.ok(response.headers.get("content-type").startsWith(type));
      const content = new Uint8Array(await response.arrayBuffer()); assert.ok(content.length > 100);
    }
    const worker = await fetch(`${base}/pdf.worker.min.mjs`); assert.equal(worker.status, 200);
    assert.match(worker.headers.get("content-type") ?? "", /^text\/javascript(?:;|$)/);
    assert.ok((await worker.arrayBuffer()).byteLength > 100);
    const pdf = await fetch(`${base}/demo/supplier_a_agreement.pdf`, { method: "HEAD" }); assert.equal(pdf.status, 200); assert.equal((await pdf.arrayBuffer()).byteLength, 0);
    assert.equal((await fetch(`${base}/package.json`)).status, 404);
    assert.equal((await fetch(`${base}/..%2fpackage.json`)).status, 403);
    assert.equal((await fetch(`${base}/%ZZ`)).status, 400);
  } finally { child.kill(); await new Promise(resolve => { if (child.exitCode !== null) resolve(); else child.once("exit", resolve); }); }
});

test("Same-origin preview forwards API bodies and gate headers; unavailable backend fails closed", async () => {
  const upstream = http.createServer(async (req, res) => {
    let body = "";
    for await (const chunk of req) body += chunk;
    res.writeHead(200, { "Content-Type": "application/json", "X-Causora-Review-Status": "reviewed", "X-Request-Id": "proxy-test" });
    res.end(JSON.stringify({ path: req.url, method: req.method, body: body ? JSON.parse(body) : null }));
  });
  await new Promise(resolve => upstream.listen(0, "127.0.0.1", resolve));
  const backendPort = upstream.address().port;
  const probe = net.createServer();
  await new Promise(resolve => probe.listen(0, "127.0.0.1", resolve));
  const port = probe.address().port;
  await new Promise(resolve => probe.close(resolve));
  const child = spawn(process.execPath, ["scripts/serve-static.mjs"], {
    cwd: path.resolve(import.meta.dirname, ".."),
    env: { ...process.env, PORT: String(port), HOST: "127.0.0.1", CAUSORA_FRONTEND_MODE: "live", CAUSORA_STATIC_ONLY: "false", NEXT_PUBLIC_CAUSORA_STATIC_ONLY: "false", CAUSORA_BACKEND_URL: `http://127.0.0.1:${backendPort}` },
    stdio: ["ignore", "pipe", "pipe"],
  });
  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("Preview startup timed out")), 8000);
      child.stdout.once("data", () => { clearTimeout(timer); resolve(); });
      child.once("error", error => { clearTimeout(timer); reject(error); });
    });
    const base = `http://127.0.0.1:${port}`;
    const response = await fetch(`${base}/api/simulate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ seed: 1042026 }) });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("x-causora-review-status"), "reviewed");
    assert.equal(response.headers.get("x-request-id"), "proxy-test");
    assert.deepEqual(await response.json(), { path: "/api/simulate", method: "POST", body: { seed: 1042026 } });
    assert.equal((await (await fetch(`${base}/health`)).json()).path, "/health");
    await new Promise(resolve => upstream.close(resolve));
    const failed = await fetch(`${base}/api/boardroom`, { method: "POST", body: "{}" });
    assert.equal(failed.status, 502);
    assert.equal((await failed.json()).error.code, "simulation_failed");
  } finally {
    if (upstream.listening) await new Promise(resolve => upstream.close(resolve));
    child.kill();
    await new Promise(resolve => { if (child.exitCode !== null) resolve(); else child.once("exit", resolve); });
  }
});

test("Static-only deployment blocks health/API proxying before reaching the configured backend", async () => {
  let upstreamRequests = 0;
  const upstream = http.createServer((_req, res) => { upstreamRequests += 1; res.writeHead(200); res.end("should not be reached"); });
  await new Promise(resolve => upstream.listen(0, "127.0.0.1", resolve));
  const backendPort = upstream.address().port;
  const probe = net.createServer();
  await new Promise(resolve => probe.listen(0, "127.0.0.1", resolve));
  const port = probe.address().port;
  await new Promise(resolve => probe.close(resolve));
  const child = spawn(process.execPath, ["scripts/serve-static.mjs"], {
    cwd: path.resolve(import.meta.dirname, ".."),
    env: { ...process.env, PORT: String(port), HOST: "127.0.0.1", CAUSORA_FRONTEND_MODE: "static", CAUSORA_STATIC_ONLY: "true", NEXT_PUBLIC_CAUSORA_STATIC_ONLY: "true", CAUSORA_BACKEND_URL: `http://127.0.0.1:${backendPort}` },
    stdio: ["ignore", "pipe", "pipe"],
  });
  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("Static-only preview startup timed out")), 8000);
      child.stdout.once("data", () => { clearTimeout(timer); resolve(); });
      child.once("error", error => { clearTimeout(timer); reject(error); });
    });
    const base = `http://127.0.0.1:${port}`;
    for (const [pathName, method] of [["/health", "GET"], ["/api/simulate", "POST"]]) {
      const response = await fetch(`${base}${pathName}`, { method, headers: method === "POST" ? { "Content-Type": "application/json" } : undefined, body: method === "POST" ? "{}" : undefined });
      assert.equal(response.status, 503);
      assert.equal(response.headers.get("x-causora-backend-status"), "not-configured");
      assert.equal((await response.json()).error.code, "backend_not_configured");
    }
    assert.equal(upstreamRequests, 0, "static-only routes must not contact the configured localhost backend");
  } finally {
    if (upstream.listening) await new Promise(resolve => upstream.close(resolve));
    child.kill();
    await new Promise(resolve => { if (child.exitCode !== null) resolve(); else child.once("exit", resolve); });
  }
});
