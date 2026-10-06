import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const stage = read("components/stage-views.tsx");
const shell = read("components/app-shell.tsx");
const page = read("app/page.tsx");
const mock = JSON.parse(read("demo_data/causora_day1_mock.json"));

test("Day2 names the prototype as static and discloses that controls do not calculate", () => {
  assert.match(shell, /DAY 2 \/ 07/);
  assert.match(shell, /No simulation, AI, or HTTP calls/);
  assert.match(stage, /DAY 2 · STATIC MOCK/);
  assert.match(stage, /no simulation engine, AI provider, or HTTP request is called/i);
  assert.match(stage, /Matrix values do not recalculate/i);
  assert.match(stage, /MOCK VALUES · NOT COMPUTED/);
  assert.match(stage, /DECISION BRIEF \/ \{currentScenario.label.toUpperCase\(\)\} MOCK RUN/);
  assert.doesNotMatch(page, /\bfetch\s*\(|\/api\/(simulate|boardroom)/i);
});

test("Scenario and option meanings and all fixed option descriptions remain visible", () => {
  assert.match(stage, /SCENARIO · OUTSIDE YOUR CONTROL/);
  assert.match(stage, /DECISION OPTION · YOUR CHOICE/);
  assert.match(stage, /Select mock scenario/);
  assert.match(stage, /Decision options · controllable choices/);
  assert.deepEqual(mock.options.map((option) => option.id), ["D0", "D1", "D2"]);
  assert.deepEqual(mock.options.map((option) => option.shareA), [1, 0.6, 0]);
  assert.deepEqual(mock.options.map((option) => option.terminateA), [false, false, true]);
  assert.match(stage, /Keep the current allocation with Supplier A/);
  assert.match(stage, /Keep \$\{minShare\} with A/);
  assert.match(stage, /Exit the renewed A agreement/);
});

test("Risk edits are still draft-only and approval remains blocked until assumptions are restored", () => {
  assert.match(stage, /Stockout risk cap/);
  assert.match(stage, /risk cap has not been evaluated/);
  assert.match(stage, /Restore preset inputs to enable approval/);
  assert.match(stage, /disabled=\{isDraft\}/);
  assert.match(stage, /Evidence → Business Variables/);
  assert.match(stage, /Open source quote/);
  assert.match(stage, /Change assumptions/);
});

test("Day2 presentation changes preserve the shared v4.1 contract, units, and fixed identifiers", () => {
  assert.equal(mock.meta.schemaVersion, "causora.contract.v1");
  assert.equal(mock.meta.dataVersion, "demo-2026.10.04-v4");
  assert.equal(mock.simulation.formulaVersion, "tco-v1");
  assert.deepEqual(mock.scenarios.map((scenario) => scenario.id), ["baseline", "demand-drop", "lead-stress"]);
  assert.equal(mock.scenarios.find((scenario) => scenario.id === "demand-drop").demandShock, -15);
  assert.equal(mock.contract.minPurchaseShareA, 0.6);
  assert.equal(mock.contract.terminationFeeUsd, 25000);
  assert.match(read("API_CONTRACT.md"), /none of these HTTP endpoints exists yet/i);
});
