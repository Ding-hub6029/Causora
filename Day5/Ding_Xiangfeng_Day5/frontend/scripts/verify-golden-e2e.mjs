// Revalidate an exported real E2E snapshot with the production validators.
// This command never calls a network service or writes browser storage.
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { Buffer } from "node:buffer";
import ts from "typescript";

const frontend = path.resolve(import.meta.dirname, "..");
const input = path.resolve(process.argv[2] ?? path.join(frontend, "../verification/g4-final/verified_golden_e2e.json"));
const urls = new Map();
function moduleUrl(file) {
  file = path.resolve(file);
  if (urls.has(file)) return urls.get(file);
  let code = ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
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
const { loadVerifiedGoldenRun, VERIFIED_GOLDEN_STORAGE_KEY } = await import(moduleUrl(path.join(frontend, "lib/golden-cache.ts")));
const raw = fs.readFileSync(input, "utf8");
const storage = { getItem: key => key === VERIFIED_GOLDEN_STORAGE_KEY ? raw : null };
const run = await loadVerifiedGoldenRun(storage);
if (!run) throw new Error("Golden record missing");
const mutated = JSON.parse(raw);
mutated.scenarioId = "tampered-scenario";
let rejected = false;
try { await loadVerifiedGoldenRun({ getItem: () => JSON.stringify(mutated) }); }
catch { rejected = true; }
if (!rejected) throw new Error("Tampered Golden record was accepted");
console.log(JSON.stringify({ status: "PASS", simulationId: run.liveRun.response.data.simulation.simulationId,
  scenarioId: run.boardroomRun.identity.scenarioId, sha256: run.sha256,
  evidenceCount: run.evidenceRecords.length, tamperRejected: rejected,
  scope: "OFFLINE_REVALIDATION_OF_CAPTURED_REAL_E2E; NOT_A_NEW_MODEL_CALL_OR_BUSINESS_SIGNATURE" }, null, 2));
