import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const root = path.resolve(import.meta.dirname, "..");
const requested = process.argv[2] ?? "both";
if (!["live", "static", "both"].includes(requested)) throw new Error("Use live, static or both.");
function run(script, env) {
  const result = spawnSync(process.execPath, [script, ...(script.endsWith("next") ? ["build"] : [])], { cwd: root, env, stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
function replaceDirectory(source, target) {
  const allowed = path.join(root, "builds") + path.sep;
  if (!path.resolve(target).startsWith(allowed)) throw new Error("Build target is outside frontend/builds.");
  fs.rmSync(target, { recursive: true, force: true });
  fs.cpSync(source, target, { recursive: true });
}
// Static first, live last: the ordinary out/ and npm start default stay live.
for (const mode of requested === "both" ? ["static", "live"] : [requested]) {
  const env = { ...process.env, NEXT_PUBLIC_CAUSORA_STATIC_ONLY: String(mode === "static"), CAUSORA_STATIC_ONLY: String(mode === "static"), CAUSORA_FRONTEND_MODE: mode };
  run(path.join(root, "scripts/copy-pdf-worker.mjs"), env);
  run(path.join(root, "node_modules/next/dist/bin/next"), env);
  fs.writeFileSync(path.join(root, "out/.causora-build.json"), JSON.stringify({ mode, schemaVersion: 1 }) + "\n");
  replaceDirectory(path.join(root, "out"), path.join(root, "builds", mode));
  console.log(`Verified build selection: ${mode} -> builds/${mode}`);
}
