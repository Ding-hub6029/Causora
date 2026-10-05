// Usage: node scripts/verify_v41.mjs /absolute/path/to/extracted/causora
// The original baseline ZIP is read-only; run after `npm ci` in its extracted copy.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { createRequire } from "node:module";
import { Buffer } from "node:buffer";

const base = path.resolve(process.argv[2] ?? "");
if (!process.argv[2] || !fs.existsSync(path.join(base, "lib/validation.ts"))) {
  console.error("Provide the extracted Xiangfeng v4.1 `causora` directory as argument.");
  process.exit(2);
}
const requireBase = createRequire(path.join(base, "package.json"));
const ts = requireBase("typescript");
const validationSource = fs.readFileSync(path.join(base, "lib/validation.ts"), "utf8");
const compiled = ts.transpileModule(validationSource, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 }
}).outputText;
const { validateMockData } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);
const here = path.resolve(import.meta.dirname, "..");
const dir = path.join(here, "demo_data/integration_v4.1");
const data = JSON.parse(fs.readFileSync(path.join(dir, "frontend_compatible_local_mock.json"), "utf8"));
const ledger = JSON.parse(fs.readFileSync(path.join(dir, "provenance_ledger.json"), "utf8"));
const baselineRaw = fs.readFileSync(path.join(dir, "causora_day1_mock_baseline.json"));
const pdf = fs.readFileSync(path.join(dir, "public/demo/supplier_a_agreement.pdf"));
validateMockData(data);
if (ledger.baselineMockSha256 !== crypto.createHash("sha256").update(baselineRaw).digest("hex")) throw new Error("baseline mock changed");
if (ledger.sourceSha256 !== crypto.createHash("sha256").update(pdf).digest("hex")) throw new Error("PDF digest changed");
const ids = data.evidence.map((e) => e.id);
if (ids.join(",") !== "EV-014,EV-019,EV-021,EV-024,EV-027") throw new Error("frontend IDs changed");
if (!data.meta.notice.includes("LOCAL MOCK") || !data.meta.status.includes("LOCAL MOCK")) throw new Error("mock label missing");
if (data.simulation.monteCarloRuns !== 0) throw new Error("frozen Day 1 fixture draw count changed");
if (ledger.wangPendingRecommendation !== null || ledger.humanSignoff !== "PENDING") throw new Error("false approval");
console.log(`PASS baseline v4.1 validateMockData: ${ids.length} frontend evidence records, ${Object.keys(data.simulation.matrix).length} scenarios × 3 options`);
console.log("PASS preserved PDF/baseline hashes, pending Wang recommendation and LOCAL MOCK label");
// SHAPE TEST ONLY: no calculation is performed, and these data stay fictional.
// The v4.1 validator should not deduce MOCK from zero stochastic draws alone.
const hypothetical = structuredClone(data);
hypothetical.meta.status = "DETERMINISTIC SHAPE CHECK ONLY";
hypothetical.meta.notice = "No calculation performed; schema acceptance demonstration only";
validateMockData(hypothetical);
console.log("PASS zero Monte Carlo draws accepted with a non-mock label (shape only; not a computed result)");
