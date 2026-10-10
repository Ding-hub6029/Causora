import type { GoldenRun, MockData } from "./types";
import type { DecisionBriefRef, ScenarioSelection } from "./contracts";

type Obj = Record<string, unknown>;
function object(value: unknown, path: string): Obj {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${path}: expected object`);
  return value as Obj;
}
function array(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) throw new Error(`${path}: expected array`);
  return value;
}
function text(value: unknown, path: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${path}: expected nonempty string`);
  return value;
}
function number(value: unknown, path: string, min = 0, max = Infinity, integer = false): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < min || value > max || (integer && !Number.isInteger(value))) throw new Error(`${path}: invalid number`);
  return value;
}
function bool(value: unknown, path: string): boolean {
  if (typeof value !== "boolean") throw new Error(`${path}: expected boolean`);
  return value;
}
function strings(value: unknown, path: string): string[] { return array(value, path).map((v) => text(v, path)); }
function fields(value: Obj, keys: string[], path: string) { for (const key of keys) text(value[key], `${path}.${key}`); }
function unique(values: string[], path: string) { if (new Set(values).size !== values.length) throw new Error(`${path}: duplicate IDs`); }
function equal(actual: unknown, expected: unknown, path: string) { if (actual !== expected) throw new Error(`${path}: inconsistent value`); }
function date(value: unknown, path: string): number {
  const s = text(value, path), n = Date.parse(`${s}T00:00:00Z`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s) || !Number.isFinite(n) || new Date(n).toISOString().slice(0, 10) !== s) throw new Error(`${path}: invalid ISO date`);
  return n;
}

/** Validate the complete successful local adapter before any view consumes it. */
export function validateMockData(input: unknown): asserts input is MockData {
  const d = object(input, "dataset"), meta = object(d.meta, "meta");
  equal(meta.schemaVersion, "causora.contract.v1", "schemaVersion");
  fields(meta, ["product", "version", "dataVersion", "status", "notice"], "meta"); number(meta.seed, "seed", 0, Infinity, true);
  const intake = array(d.intake, "intake");
  if (intake.length !== 4) throw new Error("intake: four source artifacts required");
  equal(intake.map((f) => text(object(f, "file").id, "file.id")).sort().join(","), "contract,delivery,demand,inventory", "intake IDs");
  for (const raw of intake) { const f = object(raw, "intake file"); fields(f, ["id", "label", "type", "detail", "size", "status", "icon", "path"], "intake"); if (!/^\/demo\/[a-zA-Z0-9_.-]+$/.test(text(f.path, "path"))) throw new Error("intake: unsafe local path"); }
  const evidence = array(d.evidence, "evidence").map((r) => object(r, "evidence"));
  const eids = evidence.map((e) => text(e.id, "evidence.id")); unique(eids, "evidence");
  equal([...eids].sort().join(","), "EV-014,EV-019,EV-021,EV-024,EV-027", "local evidence IDs");
  for (const e of evidence) {
    fields(e, ["sourceFile", "quote", "extractedField", "extractedValue"], "evidence");
    if (!/^[a-zA-Z0-9_.-]+\.pdf$/.test(text(e.sourceFile, "sourceFile"))) throw new Error("evidence: unsafe source filename");
    number(e.page, "page", 1, Infinity, true); number(e.matchScore, "matchScore", 0, 1); bool(e.quoteMatched, "quoteMatched");
    if (!/^EV-\d+$/.test(text(e.id, "id")) || !["exact", "fuzzy"].includes(text(e.matchMethod, "matchMethod"))) throw new Error("evidence: invalid ID/method");
    if (e.locatorBbox !== null) { const b = array(e.locatorBbox, "bbox"); if (b.length !== 4) throw new Error("bbox: four coordinates required"); b.forEach((v) => number(v, "bbox")); if (Number(b[2]) <= Number(b[0]) || Number(b[3]) <= Number(b[1])) throw new Error("bbox: inverted bounds"); }
    if (e.quoteMatched && !text(e.quote, "quote").includes(text(e.extractedValue, "value"))) throw new Error("evidence: matched quote omits critical value");
  }
  const c = object(d.contract, "contract");
  fields(c, ["noticeRecordSource", "forecastBasis"], "contract");
  if (!["locked-at-renewal", "rolling"].includes(text(c.forecastBasis, "forecastBasis"))) throw new Error("forecastBasis: unknown basis");
  for (const k of ["daysToRenewal", "renewalNoticeDays", "renewalTermMonths", "lockedForecastUnits24m", "minPurchaseUnitsA", "terminationFeeUsd"]) number(c[k], k, 0, Infinity, true);
  for (const k of ["renewalPriceIncreasePct", "minPurchaseShareA"]) number(c[k], k, 0, 1);
  bool(c.noticeSent, "noticeSent"); bool(c.renewalLocked, "renewalLocked");
  const decision = date(c.decisionDate, "decisionDate"), renewal = date(c.renewalDate, "renewalDate"), deadline = date(c.noticeDeadline, "noticeDeadline");
  equal((renewal - decision) / 86400000, c.daysToRenewal, "daysToRenewal"); equal(renewal - Number(c.renewalNoticeDays) * 86400000, deadline, "noticeDeadline");
  equal(c.renewalLocked, decision > deadline && !c.noticeSent, "renewalLocked");
  equal(c.minPurchaseUnitsA, Math.round(Number(c.lockedForecastUnits24m) * Number(c.minPurchaseShareA)), "minimum units");
  for (const id of strings(c.evidenceIds, "contract.evidenceIds")) if (!eids.includes(id)) throw new Error("contract: unknown evidence");
  const variables = array(d.variables, "variables").map((r) => object(r, "variable")); unique(variables.map((v) => text(v.key, "variable.key")), "variables");
  equal(variables.map((v) => v.source).sort().join(","), [...eids].sort().join(","), "complete evidence mapping");
  for (const v of variables) { fields(v, ["key", "name", "value", "unit", "source", "meaning"], "variable"); if (!eids.includes(text(v.source, "source"))) throw new Error("variable: unknown evidence"); for (const i of array(v.inputs, "inputs")) fields(object(i, "input"), ["name", "value", "source"], "input"); }
  const scenarios = array(d.scenarios, "scenarios").map((r) => object(r, "scenario"));
  if (!scenarios.length) throw new Error("scenarios: empty"); unique(scenarios.map((s) => text(s.id, "scenario.id")), "scenarios");
  equal(scenarios.map((s) => s.id).sort().join(","), "baseline,demand-drop,lead-stress", "local scenario IDs");
  for (const s of scenarios) { fields(s, ["label", "tag", "leadTime", "description"], "scenario"); number(s.demandShock, "demandShock", -100, 1000); number(s.demandUnits24m, "demandUnits24m", 0, Infinity, true); number(s.leadTimeMultiplier, "leadTimeMultiplier", 0.001); }
  const options = array(d.options, "options").map((r) => object(r, "option"));
  equal(options.map((o) => text(o.id, "option.id")).sort().join(","), "D0,D1,D2", "option IDs");
  for (const o of options) { fields(o, ["label", "allocation", "short", "description"], "option"); number(o.shareA, "shareA", 0, 1); bool(o.terminateA, "terminateA"); }
  const sim = object(d.simulation, "simulation"); fields(sim, ["simulationId", "formulaVersion", "dataVersion"], "simulation");
  equal(sim.dataVersion, meta.dataVersion, "simulation dataVersion"); equal(sim.seed, meta.seed, "simulation seed");
  for (const k of ["seed", "weeks", "monteCarloRuns"]) number(sim[k], k, 0, Infinity, true);
  const prices = object(sim.unitPricesUsd, "unitPricesUsd"); number(prices.A, "price A"); number(prices.B, "price B");
  const matrix = object(sim.matrix, "matrix"); equal(Object.keys(matrix).sort().join(","), scenarios.map((s) => s.id).sort().join(","), "matrix scenarios");
  for (const s of scenarios) {
    const rows = array(matrix[text(s.id, "scenario.id")], "matrix rows").map((r) => object(r, "cell"));
    equal(rows.map((r) => text(r.optionId, "optionId")).sort().join(","), "D0,D1,D2", "matrix option IDs");
    if (rows.filter((r) => r.tone === "recommended").length > 1) throw new Error("matrix: multiple recommended cells");
    for (const r of rows) {
      bool(r.feasible, "feasible"); if (!["neutral", "recommended", "risk"].includes(text(r.tone, "tone"))) throw new Error("cell: invalid tone");
      for (const k of ["expectedTco", "cashOutflowP90", "unitsFromA", "unitsFromB"]) number(r[k], k, 0, Infinity, true);
      number(r.stockoutProbability, "stockoutProbability", 0, 1); number(r.serviceLevel, "serviceLevel", 0, 1);
      const b = object(r.breakdown, "breakdown"), keys = ["purchase", "holding", "stockoutLoss", "renewalPremium", "terminationFee"];
      equal(keys.reduce((sum, k) => sum + number(b[k], k, 0, Infinity, true), 0), r.expectedTco, "TCO sum");
      equal(b.purchase, Math.round(Number(r.unitsFromA) * Number(prices.A) + Number(r.unitsFromB) * Number(prices.B)), "purchase");
      equal(b.renewalPremium, Math.round(Number(r.unitsFromA) * Number(prices.A) * Number(c.renewalPriceIncreasePct)), "premium");
      const option = options.find((o) => o.id === r.optionId)!;
      equal(b.terminationFee, option.terminateA ? c.terminationFeeUsd : 0, "exit fee");
      const total = Number(r.unitsFromA) + Number(r.unitsFromB);
      if (total > 0 && Math.abs(Number(r.unitsFromA) / total - Number(option.shareA)) > 1e-9) throw new Error("cell: allocation mismatch");
      if (r.feasible && c.renewalLocked && !option.terminateA && Number(r.unitsFromA) < Number(c.minPurchaseUnitsA)) throw new Error("cell: minimum purchase violated");
    }
  }
  const agents = array(d.boardroom, "boardroom").map((r) => object(r, "agent")); equal(agents.map((r) => r.role).sort().join(","), "CFO,COO,Risk", "roles");
  for (const a of agents) { fields(a, ["accent", "focus", "headline", "body", "status"], "agent"); strings(a.metrics, "metrics"); if (!["Aligned", "Watch"].includes(text(a.status, "status"))) throw new Error("agent: invalid status"); }
  const critic = object(d.critic, "critic"); fields(critic, ["severity", "headline", "body"], "critic"); for (const id of strings(critic.evidenceIds, "critic.evidenceIds")) if (!eids.includes(id)) throw new Error("critic: unknown evidence");
  const mechanism = object(critic.mechanism, "mechanism");
  const compound = scenarios.find((s) => s.id === mechanism.scenarioId); if (!compound) throw new Error("critic: unknown scenario");
  equal(mechanism.forecastBasis, c.forecastBasis, "critic basis"); equal(mechanism.lockedForecastUnits24m, c.lockedForecastUnits24m, "critic forecast"); equal(mechanism.minPurchaseUnitsA, c.minPurchaseUnitsA, "critic floor"); equal(mechanism.scenarioDemandUnits24m, compound.demandUnits24m, "critic demand");
  equal(mechanism.committedExcessUnits, Number(c.minPurchaseUnitsA) - Math.round(Number(c.minPurchaseShareA) * Number(compound.demandUnits24m)), "rolling benchmark");
  const holding = object(mechanism.holdingCostDeltaUsd, "holding deltas"); for (const id of ["D0", "D1", "D2"]) number(holding[id], "holding delta", -Infinity);
  const brief = object(d.brief, "brief"); fields(brief, ["recommendedOptionId", "recommendation", "rationale", "formula", "formulaVersion", "guardrail"], "brief"); strings(brief.metricRefs, "metricRefs"); strings(brief.formulaNotes, "formulaNotes");
  if (!options.some((o) => o.id === brief.recommendedOptionId)) throw new Error("brief: unknown option"); equal(brief.formulaVersion, sim.formulaVersion, "brief formula version");
  for (const s of scenarios) if (!array(matrix[text(s.id, "scenario")], "rows").some((r) => { const row = object(r, "cell"); return row.optionId === brief.recommendedOptionId && row.feasible; })) throw new Error("local brief: recommended option must be feasible in every bundled preset");
}

export function validateGoldenRun(input: unknown): asserts input is GoldenRun {
  const g = object(input, "golden"); validateMockData(g.snapshot);
  fields(g, ["label", "verifiedAt", "verifiedAtNote", "dataVersion", "snapshotHash", "notice"], "golden");
  const stamp = Date.parse(text(g.verifiedAt, "verifiedAt")); if (!Number.isFinite(stamp) || stamp > Date.now() || !text(g.verifiedAt, "verifiedAt").endsWith("Z")) throw new Error("golden: invalid/future UTC timestamp");
  if (!/^[a-f0-9]{64}$/.test(text(g.snapshotHash, "hash"))) throw new Error("golden: invalid hash");
  equal(g.dataVersion, g.snapshot.meta.dataVersion, "golden version"); equal(g.seed, g.snapshot.simulation.seed, "golden seed");
  const req = object(g.request, "golden request"), response = object(g.response, "golden response");
  if (!g.snapshot.scenarios.some((s) => s.id === req.scenario)) throw new Error("golden: unknown scenario");
  equal(strings(req.options, "options").sort().join(","), "D0,D1,D2", "golden options"); number(req.riskThreshold, "riskThreshold", 0, 100);
  equal(response.recommendedOptionId, g.snapshot.brief.recommendedOptionId, "golden recommendation"); equal(response.status, "local-mock", "golden status");
}

export async function verifyGoldenHash(golden: GoldenRun): Promise<void> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(golden.snapshot)));
  const hash = Array.from(new Uint8Array(digest), (v) => v.toString(16).padStart(2, "0")).join("");
  if (hash !== golden.snapshotHash) throw new Error("Golden snapshot integrity check failed");
}

/** Validate the union before an HTTP adapter chooses a selected or no-feasible view. */
export function validateDecisionBrief(input: unknown, selection: ScenarioSelection): asserts input is DecisionBriefRef {
  const brief = object(input, "API brief");
  equal(brief.scenarioId, selection.scenarioId, "brief scenario");
  equal(brief.status, selection.status, "brief status");
  equal(brief.recommendedOptionId, selection.recommendedOptionId, "brief selection");
  if (selection.status === "no_feasible_option") {
    text(brief.message, "no-feasible message");
    equal(JSON.stringify(brief.constraintViolations), JSON.stringify(selection.constraintViolations), "brief violations");
  } else {
    fields(brief, ["recommendation", "rationale", "formula", "formulaVersion", "guardrail"], "brief");
    strings(brief.metricRefs, "brief metricRefs"); strings(brief.formulaNotes, "brief formulaNotes");
  }
}
