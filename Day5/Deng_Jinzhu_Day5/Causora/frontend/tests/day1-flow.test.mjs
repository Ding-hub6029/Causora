import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { Buffer } from "node:buffer";
import ts from "typescript";
import { getDocument } from "pdfjs-dist/legacy/build/pdf.mjs";

const root = path.resolve(import.meta.dirname, "..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const mock = JSON.parse(read("demo_data/causora_day1_mock.json"));
const golden = JSON.parse(read("golden/golden_run.json"));
const ids = ["D0", "D1", "D2"];
const metricsJs = ts.transpileModule(read("lib/metrics.ts"), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const metrics = await import(`data:text/javascript;base64,${Buffer.from(metricsJs).toString("base64")}`);
const validationJs = ts.transpileModule(read("lib/validation.ts"), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const validation = await import(`data:text/javascript;base64,${Buffer.from(validationJs).toString("base64")}`);

const utcDate = (value) => Date.parse(`${value}T00:00:00Z`);
const wholeDays = (a, b) => (utcDate(b) - utcDate(a)) / 86400000;

// Most checks exercise typed-data behavior; the few source checks below guard UI wiring,
// complemented by the real-browser regression instructions in TESTING.md.
test("Contract version and all five stages have the required data", () => {
  assert.equal(mock.meta.schemaVersion, "causora.contract.v1");
  assert.equal(mock.intake.length, 4);
  assert.equal(mock.evidence.length, 5);
  assert.equal(mock.variables.length, 5);
  assert.equal(mock.scenarios.length, 3);
  assert.deepEqual(mock.options.map((o) => o.id), ids);
  assert.equal(mock.simulation.weeks, 104);
  assert.equal(mock.simulation.monteCarloRuns, 0);
  assert.equal(mock.brief.recommendedOptionId, "D1");
  assert.equal(mock.brief.formulaVersion, mock.simulation.formulaVersion);
});

test("Four synthetic source files and the notice register are real packaged artifacts", () => {
  for (const entry of mock.intake) {
    assert.ok(entry.path.startsWith("/demo/"));
    const local = path.join(root, "public", entry.path.slice(1));
    assert.ok(fs.statSync(local).size > 50, `Missing source file: ${entry.path}`);
  }
  assert.equal(read("public/demo/historical_demand.csv").trim().split("\n").length, 105);
  assert.equal(read("public/demo/opening_inventory.csv").trim().split("\n").length, 2);
  assert.equal(fs.readFileSync(path.join(root, "public/demo/supplier_a_agreement.pdf")).subarray(0, 4).toString(), "%PDF");
  assert.equal(fs.readFileSync(path.join(root, "public/demo/supplier_delivery_history.xlsx")).subarray(0, 2).toString(), "PK");
  assert.equal(read("public/demo/supplier_correspondence_log.csv"), read("demo_data/supplier_correspondence_log.csv"));
});

test("All evidence quotes contain their critical values; EV-019 maps to a variable", () => {
  for (const evidence of mock.evidence) {
    assert.equal(evidence.matchMethod, "exact");
    assert.equal(evidence.matchScore, 1);
    assert.equal(evidence.quoteMatched, true);
    assert.ok(evidence.quote.replaceAll(",", "").includes(evidence.extractedValue.replaceAll(",", "")), `${evidence.id} value absent from quote`);
    assert.ok(mock.variables.some((variable) => variable.source === evidence.id && variable.inputs.some((input) => input.name === evidence.extractedField)), `${evidence.id} has no mapped variable input`);
    assert.ok(evidence.page >= 1 && Number.isInteger(evidence.page));
    assert.equal(evidence.locatorBbox, null, "No fake PDF rectangle is permitted in Day 1");
  }
  const renewal = mock.variables.find((v) => v.source === "EV-019");
  assert.equal(renewal.key, "renewal_term_months");
  assert.equal(renewal.value, "24 months");
});

test("All five EvidenceRecord quotes match their cited PDF page; wrong quote and page fail", async () => {
  const task = getDocument({
    data: new Uint8Array(fs.readFileSync(path.join(root, "public/demo/supplier_a_agreement.pdf"))),
    useSystemFonts: true,
    disableFontFace: true
  });
  try {
    const pdf = await task.promise;
    assert.equal(pdf.numPages, 6);
    const textByPage = new Map();
    for (const evidence of mock.evidence) {
      if (!textByPage.has(evidence.page)) {
        const content = await (await pdf.getPage(evidence.page)).getTextContent();
        textByPage.set(evidence.page, content.items.map((item) => item.str).join(" ").replace(/\s+/g, " "));
      }
      assert.ok(textByPage.get(evidence.page).includes(evidence.quote), `${evidence.id} quote is absent from its cited PDF page`);
    }
    const wrongPage = (await (await pdf.getPage(3)).getTextContent()).items.map((item) => item.str).join(" ");
    assert.ok(!wrongPage.includes(mock.evidence[0].quote), "A quote must not be accepted on the wrong page");
    assert.ok(!textByPage.get(4).includes(mock.evidence[0].quote.replace("60 days", "61 days")), "A changed value must not be accepted as an exact quote");
  } finally {
    await task.destroy();
  }
});

test("Renewal lock requires a real date inequality AND an explicit notice input", () => {
  const c = mock.contract;
  assert.equal(wholeDays(c.decisionDate, c.renewalDate), c.daysToRenewal);
  assert.equal(wholeDays(c.noticeDeadline, c.renewalDate), c.renewalNoticeDays);
  assert.equal(c.renewalLocked, c.daysToRenewal < c.renewalNoticeDays && !c.noticeSent);
  assert.equal(c.noticeSent, false);
  assert.ok(c.noticeRecordSource.includes("supplier_correspondence_log.csv"));
  assert.ok(read("demo_data/supplier_correspondence_log.csv").includes("synthetic"));
  const renewalVariable = mock.variables.find((v) => v.key === "renewal_locked");
  assert.ok(renewalVariable.inputs.some((i) => i.name === "notice_sent_before_deadline" && i.value === "No"));
  assert.equal(c.renewalTermMonths, 24);
});

test("Locked forecast mechanism is explicit and the Critic uses matching inputs", () => {
  const c = mock.contract;
  const m = mock.critic.mechanism;
  const stress = mock.scenarios.find((scenario) => scenario.id === m.scenarioId);
  assert.equal(c.forecastBasis, "locked-at-renewal");
  assert.equal(c.minPurchaseUnitsA, c.lockedForecastUnits24m * c.minPurchaseShareA);
  assert.equal(m.minPurchaseUnitsA, c.minPurchaseUnitsA);
  assert.equal(m.scenarioDemandUnits24m, stress.demandUnits24m);
  assert.equal(stress.demandUnits24m, c.lockedForecastUnits24m * (1 + stress.demandShock / 100));
  assert.equal(m.committedExcessUnits, m.minPurchaseUnitsA - stress.demandUnits24m * c.minPurchaseShareA);
  for (const id of ids) {
    const baseline = metrics.cell(mock, "baseline", id);
    const stressed = metrics.cell(mock, "demand-drop", id);
    assert.equal(m.holdingCostDeltaUsd[id], stressed.breakdown.holding - baseline.breakdown.holding);
  }
});

test("Every matrix has each fixed option exactly once and at most one recommended cell", () => {
  for (const scenario of mock.scenarios) {
    const rows = mock.simulation.matrix[scenario.id];
    assert.equal(rows.length, ids.length);
    assert.deepEqual(rows.map((row) => row.optionId).sort(), ids);
    assert.equal(new Set(rows.map((row) => row.optionId)).size, ids.length);
    assert.equal(rows.filter((row) => row.tone === "recommended").length, 1);
    assert.equal(rows.find((row) => row.tone === "recommended").optionId, mock.brief.recommendedOptionId);
  }
  assert.deepEqual(Object.keys(mock.simulation.matrix).sort(), mock.scenarios.map((s) => s.id).sort());
});

test("All 9 formula traces add exactly to their cells without a double-counted uplift", () => {
  const baseA = 12;
  const baseB = 12.6;
  for (const scenario of mock.scenarios) for (const row of mock.simulation.matrix[scenario.id]) {
    assert.equal(metrics.sumBreakdown(row.breakdown), row.expectedTco, `${scenario.id}/${row.optionId} does not add up`);
    assert.ok(Math.abs(row.breakdown.purchase - row.unitsFromA * baseA - row.unitsFromB * baseB) <= 1);
    assert.equal(row.breakdown.renewalPremium, Math.round(row.unitsFromA * baseA * mock.contract.renewalPriceIncreasePct));
    const option = mock.options.find((item) => item.id === row.optionId);
    const bought = row.unitsFromA + row.unitsFromB;
    assert.ok(bought > 0);
    assert.ok(Math.abs(row.unitsFromA / bought - option.shareA) < 1e-9, `${scenario.id}/${row.optionId} violates its declared allocation`);
    assert.equal(row.breakdown.terminationFee, option.terminateA ? mock.contract.terminationFeeUsd : 0);
    if (!option.terminateA) assert.ok(row.unitsFromA >= mock.contract.minPurchaseUnitsA);
    assert.ok(row.stockoutProbability >= 0 && row.stockoutProbability <= 1);
    assert.ok(row.serviceLevel >= 0 && row.serviceLevel <= 1);
    assert.ok(row.cashOutflowP90 >= 0);
  }
  assert.equal(mock.simulation.unitPricesUsd.A, baseA);
  assert.equal(mock.simulation.unitPricesUsd.B, baseB);
  assert.equal(metrics.cell(mock, "demand-drop", "D1").unitsFromB, 10400);
});

test("Decision Delta is calculated from each selected scenario, not a hard-coded baseline", () => {
  for (const scenario of mock.scenarios) {
    const delta = metrics.decisionDelta(mock, scenario.id, "D1", "D0");
    assert.equal(delta.deltaTco, metrics.cell(mock, scenario.id, "D1").expectedTco - metrics.cell(mock, scenario.id, "D0").expectedTco);
    assert.equal(delta.deltaStockoutPp, Math.round(100 * (metrics.cell(mock, scenario.id, "D1").stockoutProbability - metrics.cell(mock, scenario.id, "D0").stockoutProbability)));
    assert.equal(delta.deltaCashP90, metrics.cell(mock, scenario.id, "D1").cashOutflowP90 - metrics.cell(mock, scenario.id, "D0").cashOutflowP90);
  }
  assert.equal(metrics.decisionDelta(mock, "baseline", "D1").deltaTco, -9000);
  assert.equal(metrics.decisionDelta(mock, "demand-drop", "D1").deltaTco, -19000);
});

test("Agent and Critic numerical claims are guarded tokens resolved against the contract", () => {
  for (const template of [...mock.boardroom.map((a) => a.body), mock.critic.body]) {
    assert.doesNotMatch(metrics.stripTokens(template).replace(/\bD[012]\b/g, ""), /\d/, "Free-form digits may not bypass the numeric guardrail (option IDs are allowed)");
    assert.doesNotMatch(metrics.renderGuarded(template, mock), /\[unresolved token\]/);
  }
  assert.match(metrics.renderGuarded(mock.boardroom[0].body, mock), /\$9k/);
  assert.match(metrics.renderGuarded(mock.boardroom[0].body, mock), /\$19k/);
  assert.match(metrics.renderGuarded(mock.boardroom[1].body, mock), /20% to 10%/);
  assert.match(metrics.renderGuarded(mock.critic.body, mock), /15,600 units/);
  assert.equal(metrics.signedMoney(mock.critic.mechanism.holdingCostDeltaUsd.D1), "+$6,500");
  for (const variable of mock.variables) assert.doesNotMatch(metrics.renderGuarded(variable.meaning, mock), /\[unresolved token\]/);
  for (const note of mock.brief.formulaNotes) assert.doesNotMatch(metrics.renderGuarded(note, mock), /\[unresolved token\]/);
  assert.match(metrics.renderGuarded(mock.brief.formulaNotes[1], mock), /26,000 units/);
  assert.doesNotMatch(mock.variables.find((v) => v.key === "min_purchase_share_A").meaning, /15,600/);
  assert.doesNotMatch(mock.brief.formulaNotes.join(" "), /26,000|14%|60%/);
});

test("Golden Run is a complete independently serialised snapshot with a valid audit timestamp", () => {
  assert.equal(golden.response.status, "local-mock");
  assert.equal(golden.dataVersion, golden.snapshot.meta.dataVersion);
  assert.equal(golden.seed, golden.snapshot.simulation.seed);
  assert.equal(golden.response.recommendedOptionId, golden.snapshot.brief.recommendedOptionId);
  assert.deepEqual(golden.request.options, golden.snapshot.options.map((o) => o.id));
  assert.deepEqual(Object.keys(golden.snapshot), Object.keys(mock));
  const hash = crypto.createHash("sha256").update(JSON.stringify(golden.snapshot)).digest("hex");
  assert.equal(hash, golden.snapshotHash);
  assert.ok(Date.parse(golden.verifiedAt) <= Date.now(), "Verification timestamp is in the future");
  assert.ok(golden.verifiedAtNote.includes("local mock"));
  assert.equal(golden.snapshot.contract.minPurchaseUnitsA, 15600);
  const changedMain = JSON.parse(JSON.stringify(mock));
  changedMain.simulation.matrix.baseline[1].expectedTco = 1;
  assert.equal(golden.snapshot.simulation.matrix.baseline[1].expectedTco, 411000);
});

test("Frozen workflow preserves Golden, labels unsimulated drafts and blocks stale live approval", () => {
  const page = read("app/page.tsx");
  const stage = read("components/stage-views.tsx");
  assert.match(page, /runState === "golden" \? goldenRun\.snapshot : mockData/);
  for (const name of ["selectScenario", "changeDemandShift", "changeRiskThreshold", "changeBudgetCeiling"]) {
    const block = page.slice(page.indexOf(`function ${name}`), page.indexOf(`function ${name}`) + 240);
    assert.ok(block.includes("leaveGoldenIfNeeded()"), `${name} must remove a stale Golden label`);
  }
  assert.ok(stage.includes("brief-draft-warning"));
  assert.ok(stage.includes('disabled title="A live reviewed Simulation and matching Boardroom response are required"'), "The saved Day 2 example never records an approval");
  assert.ok(stage.includes("Approve and Reject remain unavailable"), "saved-example decision buttons stay disabled");
  assert.ok(stage.includes("Restore preset request inputs"));
  assert.ok(stage.includes("SAVED VALUES · NOT COMPUTED"), "a saved matrix must not be labelled as a live calculation");
  assert.ok(stage.includes('props.liveRun && props.stage === "boardroom"') && stage.includes("LiveBoardroomView") && stage.includes("LiveBriefView"), "Day2 Boardroom/Brief samples must not be attached to a live run");
  assert.ok(page.includes("postSimulate(request"), "the page must invoke the shared API client with its abort controller");
  assert.ok(page.includes('const canRecordDecision = !cachedGoldenActive && !isDraft && currentLiveRun?.integrationMode === "reviewed-v2"'), "only a matching reviewed run can enable a decision");
  assert.ok(page.includes('if (!run || run.integrationMode !== "reviewed-v2"') && page.includes("matching validated Boardroom response are required"), "programmatic approval is blocked without the exact validated Boardroom response");
  assert.ok(stage.includes("onPreviewState={onPreviewState}"));
  assert.ok(stage.includes("Evidence stack · {data.evidence.length}"));
});

test("Formula modal identifies a scenario and option; dialog manages Tab, Escape and focus restore", () => {
  const page = read("app/page.tsx");
  const modal = read("components/detail-modal.tsx");
  assert.match(page, /kind: "formula", scenarioId: formulaScenarioId, optionId:/);
  for (const s of ["sumBreakdown(metrics.breakdown)", "metrics.expectedTco", 'event.key === "Escape"', 'event.key !== "Tab"', "restoreRef.current?.focus", "aria-modal=\"true\""]) assert.ok(modal.includes(s), `Missing ${s}`);
});

test("Static start command and mobile status display work without a live backend", () => {
  const pkg = JSON.parse(read("package.json"));
  assert.equal(pkg.scripts.start, "node scripts/serve-static.mjs");
  assert.match(read("app/layout.tsx"), /Causora decision intelligence with reviewed simulations/);
  assert.doesNotMatch(read("app/layout.tsx"), /Day 1 decision-intelligence prototype/);
  const css = read("app/globals.css");
  assert.match(css, /Audit remediation: state badges must remain readable/);
  assert.match(css, /\.topbar-actions \.status-chip \{\s*display:inline-flex/);
  assert.match(read("components/app-shell.tsx"), /<ProofEngine data={data}/);
});

test("Runtime validation rejects unknown versions, malformed types and inconsistent accounting", () => {
  validation.validateMockData(mock); validation.validateGoldenRun(golden);
  const mutations = [
    d => { d.meta.schemaVersion = "causora.contract.v99"; },
    d => { d.simulation.matrix.baseline[1].expectedTco = "411000"; },
    d => { d.simulation.matrix.baseline[1].stockoutProbability = 1.1; },
    d => { d.simulation.matrix.baseline[1].breakdown.purchase++; },
    d => { d.variables[0].source = "EV-999"; },
    d => { d.contract.decisionDate = "2026-02-30"; },
    d => { d.simulation.matrix.baseline.push(d.simulation.matrix.baseline[0]); },
    d => { d.contract.noticeSent = true; },
    d => { d.brief.recommendedOptionId = "D3"; },
    d => { d.scenarios = []; },
    d => { d.intake[0].id = "unknown"; },
    d => { d.evidence = []; },
    d => { d.evidence[0].sourceFile = "../outside.pdf"; },
  ];
  for (const mutate of mutations) { const bad = structuredClone(mock); mutate(bad); assert.throws(() => validation.validateMockData(bad)); }
});

test("Fractional probability differences keep precision; money preserves non-round values", () => {
  const fractional = structuredClone(mock); fractional.simulation.matrix.baseline[1].stockoutProbability = .071;
  assert.equal(metrics.decisionDelta(fractional, "baseline", "D1").deltaStockoutPp, -1.9);
  assert.equal(metrics.signedPp(-1.9), "−1.9 pp");
  assert.equal(metrics.money(411250), "$411,250");
});

test("Guarded text handles cost increases, equality and unbound numbers", () => {
  for (const template of [mock.brief.formula, ...mock.brief.formulaNotes, ...mock.variables.map(v => v.meaning), ...mock.boardroom.map(a => a.body), mock.critic.body]) {
    assert.doesNotMatch(metrics.renderGuarded(template, mock), /\[unverified numeric claim\]|\[unresolved token\]/);
  }
  const changed = structuredClone(mock); changed.simulation.matrix.baseline[1].expectedTco = 430000;
  assert.match(metrics.renderGuarded(changed.boardroom[0].body, changed), /D1 \$10k above D0/);
  changed.simulation.matrix.baseline[1].expectedTco = 420000;
  assert.match(metrics.renderGuarded(changed.boardroom[0].body, changed), /D1 the same cost as D0/);
  assert.equal(metrics.renderGuarded("Invented cost $999999", mock), "[unverified numeric claim]");
  assert.equal(metrics.renderGuarded("{{evidence:EV-999}}", mock), "[unresolved token]");
  assert.match(metrics.renderGuarded(mock.critic.body, mock), /demand changes by −15%/);
});

test("Per-scenario selection, inclusive limits, deterministic ties and no-feasible Brief", () => {
  assert.equal(metrics.selectScenarioOption(mock, "baseline", .12, 480000).recommendedOptionId, "D1");
  assert.equal(metrics.selectScenarioOption(mock, "baseline", .05, 430000).recommendedOptionId, "D1");
  const blocked = metrics.selectScenarioOption(mock, "baseline", .001, 480000);
  assert.equal(blocked.status, "no_feasible_option"); assert.equal(blocked.recommendedOptionId, null);
  const brief = { ...blocked, message: "No option passed constraints." };
  validation.validateDecisionBrief(brief, blocked);
  assert.throws(() => validation.validateDecisionBrief({ ...brief, recommendedOptionId: "D1" }, blocked));
  assert.throws(() => validation.validateDecisionBrief({ ...brief, scenarioId: "demand-drop" }, blocked));
  const changed = structuredClone(mock); changed.simulation.matrix.baseline[1].expectedTco = 500000;
  assert.equal(metrics.selectScenarioOption(changed, "baseline", .12, 480000).recommendedOptionId, "D0");
  assert.equal(metrics.selectScenarioOption(changed, "demand-drop", .12, 480000).recommendedOptionId, "D1");
  changed.simulation.matrix.baseline[1].expectedTco = 420000;
  assert.equal(metrics.selectScenarioOption(changed, "baseline", .12, 480000).recommendedOptionId, "D0");
  assert.throws(() => metrics.selectScenarioOption(mock, "baseline", 12, 480000));
});

test("Golden integrity verification rejects tampering", async () => {
  await validation.verifyGoldenHash(golden);
  const bad = structuredClone(golden); bad.snapshot.meta.notice += " tampered";
  await assert.rejects(validation.verifyGoldenHash(bad), /integrity/);
});

test("Synthetic forecast provenance and rolling benchmark remain distinct from total excess", () => {
  assert.equal(read("public/demo/historical_demand.csv").trim().split(/\r?\n/).slice(1).reduce((sum, line) => sum + Number(line.split(",")[1]), 0), 25936);
  const forecast = mock.variables.flatMap(v => v.inputs).find(i => i.name === "locked_forecast_units_24m");
  assert.match(forecast.source, /synthetic/); assert.doesNotMatch(forecast.source, /^historical_demand/);
  const cell = metrics.cell(mock, "demand-drop", "D1");
  assert.equal(cell.unitsFromA + cell.unitsFromB - mock.critic.mechanism.scenarioDemandUnits24m, 3900);
  assert.equal(mock.critic.mechanism.committedExcessUnits, 2340);
  assert.doesNotMatch(read("components/context-deck.tsx"), /committed units above the scenario's need/);
});
