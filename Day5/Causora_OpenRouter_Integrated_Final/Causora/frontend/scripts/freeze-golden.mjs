// Freezes the current frontend data contract into golden/golden_run.json.
// Usage: node scripts/freeze-golden.mjs [--verified-at 2026-10-04T13:45:00Z]
// The snapshot is a complete, independent copy: later edits to demo_data do not change it.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const root = path.resolve(import.meta.dirname, "..");
const args = process.argv.slice(2);
const verifiedAtIndex = args.indexOf("--verified-at");
const verifiedAt = verifiedAtIndex >= 0 ? args[verifiedAtIndex + 1] : new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
if (typeof verifiedAt !== "string" || !verifiedAt.endsWith("Z") || !Number.isFinite(Date.parse(verifiedAt)) || Date.parse(verifiedAt) > Date.now()) throw new Error("verifiedAt must be a valid UTC timestamp that is not in the future");

const snapshot = JSON.parse(fs.readFileSync(path.join(root, "demo_data/causora_day1_mock.json"), "utf8"));
const snapshotJson = JSON.stringify(snapshot);
const snapshotHash = crypto.createHash("sha256").update(snapshotJson).digest("hex");

const golden = {
  label: "CACHED · VERIFIED GOLDEN RUN",
  verifiedAt,
  verifiedAtNote: "UTC time when the local mock snapshot was frozen. This script hashes and copies the data but does not run tests; test results are documented separately in TESTING.md. This is not a live backend run.",
  dataVersion: snapshot.meta.dataVersion,
  seed: snapshot.meta.seed,
  snapshotHash,
  request: { scenario: "baseline", options: snapshot.options.map((option) => option.id), riskThreshold: 12 },
  response: { recommendedOptionId: snapshot.brief.recommendedOptionId, status: "local-mock" },
  snapshot,
  notice: "This snapshot is intentionally local mock data for Day 1. The UI renders only this frozen copy while the Golden Run is active."
};

fs.writeFileSync(path.join(root, "golden/golden_run.json"), `${JSON.stringify(golden, null, 2)}\n`);
console.log(`golden_run.json frozen · verifiedAt=${verifiedAt} · sha256=${snapshotHash.slice(0, 16)}…`);
