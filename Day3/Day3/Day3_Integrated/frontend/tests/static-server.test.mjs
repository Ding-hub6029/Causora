import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import net from "node:net";
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
    const pdf = await fetch(`${base}/demo/supplier_a_agreement.pdf`, { method: "HEAD" }); assert.equal(pdf.status, 200); assert.equal((await pdf.arrayBuffer()).byteLength, 0);
    assert.equal((await fetch(`${base}/package.json`)).status, 404);
    assert.equal((await fetch(`${base}/..%2fpackage.json`)).status, 403);
    assert.equal((await fetch(`${base}/%ZZ`)).status, 400);
  } finally { child.kill(); await new Promise(resolve => { if (child.exitCode !== null) resolve(); else child.once("exit", resolve); }); }
});
