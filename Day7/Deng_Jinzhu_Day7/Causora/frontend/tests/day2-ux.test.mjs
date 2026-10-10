import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const stage = read("components/stage-views.tsx");
const shell = read("components/app-shell.tsx");
const page = read("app/page.tsx");
const modal = read("components/detail-modal.tsx");
const api = read("lib/simulate-api.ts");
const mock = JSON.parse(read("demo_data/causora_day1_mock.json"));

test("Day5 preserves validated live simulation while keeping the saved example explicitly labelled", () => {
  assert.match(shell, /DAY 5 \/ 07/);
  assert.match(page, /postSimulate\(request/);
  assert.match(api, /\/api\/simulate/);
  assert.match(api, /monteCarloRuns.*positive/);
  assert.match(api, /mock snapshots are not live simulations/);
  assert.match(stage, /SAVED VALUES · NOT COMPUTED/);
  assert.match(stage, /role="table"/);
  assert.match(stage, /props\.liveRun && props\.stage === "boardroom"/);
  assert.match(stage, /<LiveBoardroomView/);
  assert.match(stage, /<LiveBriefView/);
  assert.match(api, /validateUnreviewedV2Development/);
  assert.match(shell, /UNREVIEWED — DEVELOPMENT ONLY/);
  assert.match(modal, /Decision Delta/);
  assert.match(modal, /Weekly holding\/stockout drivers are not present in the shared v1 DTO\./);
  assert.match(modal, /Inspect 104-week sample path/);
  assert.doesNotMatch(api, /\/api\/boardroom/);
});

test("Scenario and option meanings and all fixed Day2 option definitions remain unchanged", () => {
  assert.match(stage, /SCENARIO · OUTSIDE YOUR CONTROL/);
  assert.match(stage, /DECISION OPTION · YOUR CHOICE/);
  assert.match(stage, /Select scenario/);
  assert.match(stage, /Decision options · controllable choices/);
  assert.deepEqual(mock.options.map((option) => option.id), ["D0", "D1", "D2"]);
  assert.deepEqual(mock.options.map((option) => option.shareA), [1, 0.6, 0]);
  assert.deepEqual(mock.options.map((option) => option.terminateA), [false, false, true]);
  assert.match(stage, /Keep the current allocation with Supplier A/);
  assert.match(stage, /Keep \$\{minShare\} with A/);
  assert.match(stage, /Exit the renewed A agreement/);
});

test("Risk and cash edits remain drafts until a new request; no stale approval is enabled", () => {
  assert.match(stage, /Stockout risk cap/);
  assert.match(stage, /risk cap/);
  assert.match(stage, /Restore preset request inputs/);
  assert.match(stage, /Approve and Reject remain unavailable/);
  assert.match(stage, /disabled title="A live reviewed Simulation and matching Boardroom response are required"/);
  assert.match(page, /const canRecordDecision = !cachedGoldenActive && !isDraft && currentLiveRun\?\.integrationMode === "reviewed-v2"/);
  assert.match(page, /matching validated Boardroom response are required/);
  assert.match(stage, /Evidence → Business Variables/);
  assert.match(stage, /Open source quote/);
  assert.match(stage, /Change assumptions/);
});

test("Matrix browsing and option inspection are view-only and preserve the validated live run", () => {
  const browseHandler = page.slice(page.indexOf("function viewMatrixScenario"), page.indexOf("function changeDemandShift"));
  const matrix = stage.slice(stage.indexOf("function MatrixView"), stage.indexOf("function BoardroomView"));
  assert.match(page, /matrixScenarioId, setMatrixScenarioId/);
  assert.match(page, /onScenarioView=\{viewMatrixScenario\}/);
  assert.match(browseHandler, /setMatrixScenarioId\(id\)/);
  assert.doesNotMatch(browseHandler, /invalidateSimulation|setScenarioId|setDemandShift|setRiskThreshold|setBudgetCeilingUsd/);
  assert.match(matrix, /onScenarioView\(scenario\.id\)/);
  assert.match(matrix, /onOptionSelect\(option\.id\)/);
  assert.doesNotMatch(matrix, /onScenarioChange|invalidateSimulation/);
  assert.match(matrix, /displayMatrixTone\(metrics, liveRun \? scenarioSelection : undefined\)/);
  assert.match(matrix, /onFormula\(selectedOption, matrixScenarioId\)/);
});

test("unreviewed v2 remains visibly non-decision-ready, has no winner styling, and traces weekly provenance", () => {
  const proof = read("components/proof-engine.tsx");
  assert.match(shell, /NOT DECISION-READY, not a formal recommendation and cannot be approved/);
  assert.match(stage, /const isUnreviewedDev = liveRun\?\.integrationMode === "unreviewed-v2-dev"/);
  assert.match(stage, /!isUnreviewedDev && scenarioSelection\?\.status === "selected"/);
  assert.match(stage, /Constraint screen · not a recommendation/);
  assert.match(proof, /No reviewed choice\./);
  assert.match(proof, /CONSTRAINT SCREEN · NO RECOMMENDATION/);
  assert.match(page, /currentLiveRun\?\.integrationMode === "unreviewed-v2-dev" \? "dev-live"/);
  assert.match(page, /const canRecordDecision = !cachedGoldenActive && !isDraft && currentLiveRun\?\.integrationMode === "reviewed-v2"/);
  assert.match(modal, /Formula inputs and provenance/);
  assert.match(modal, /Object\.entries\(week\)/);
  assert.match(modal, /one realised trial, not an average\/aggregate/);
  assert.match(modal, /sample path is one realised trial, not an aggregate/);
});

test("Day1/Day2 shared v1 contract, data version, formula and scenario identities remain intact", () => {
  assert.equal(mock.meta.schemaVersion, "causora.contract.v1");
  assert.equal(mock.meta.dataVersion, "demo-2026.10.04-v4");
  assert.equal(mock.simulation.formulaVersion, "tco-v1");
  assert.deepEqual(mock.scenarios.map((scenario) => scenario.id), ["baseline", "demand-drop", "lead-stress"]);
  assert.equal(mock.scenarios.find((scenario) => scenario.id === "demand-drop").demandShock, -15);
  assert.equal(mock.contract.minPurchaseShareA, 0.6);
  assert.equal(mock.contract.terminationFeeUsd, 25000);
  assert.match(read("API_CONTRACT.md"), /POST \/api\/simulate/);
  assert.match(read("API_CONTRACT.md"), /riskThreshold` is a fraction on the wire/);
});
