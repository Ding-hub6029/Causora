import type { ApiSuccess, DecisionOption, MetricCell, OptionId, Scenario, SimulateRequest, SimulateResponse } from "./contracts";
import type { LiveIntegrationMode } from "./contracts-v2-dev";

import type { V2SimulationDetails, V2FormulaTrace, ReviewedSimulationDetails } from "./contracts-v2";
import type { DevSimulationDetails } from "./contracts-v2-dev";

const SCHEMA_VERSION = "causora.contract.v1" as const;
const OPTION_ORDER: OptionId[] = ["D0", "D1", "D2"];
const VIOLATION_ORDER = ["infeasible", "stockout_threshold", "cash_ceiling"] as const;
const SCHEMA_VERSION_V2 = "causora.contract.v2" as const;
const DEV_MODE_SENTINEL = "UNREVIEWED_DEV_ONLY";
const REQUEST_TIMEOUT_MS = 120_000;

type Obj = Record<string, unknown>;
export type SimulationApiResult = {
  response: ApiSuccess<SimulateResponse>;
  integrationMode: LiveIntegrationMode;
  development?: V2SimulationDetails;
};

function obj(value: unknown, path: string): Obj {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${path}: expected object`);
  return value as Obj;
}
function arr(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) throw new Error(`${path}: expected array`);
  return value;
}
function text(value: unknown, path: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${path}: expected non-empty string`);
  return value;
}
function num(value: unknown, path: string, min = 0, max = Infinity, integer = false): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < min || value > max || (integer && !Number.isInteger(value))) throw new Error(`${path}: invalid number`);
  return value;
}
function bool(value: unknown, path: string): boolean {
  if (typeof value !== "boolean") throw new Error(`${path}: expected boolean`);
  return value;
}
function sameNumber(actual: number, expected: number, path: string): void {
  if (Math.abs(actual - expected) > 1e-8) throw new Error(`${path}: inconsistent value`);
}
function compareIds(actual: string[], expected: string[], path: string): void {
  if (actual.length !== expected.length || new Set(actual).size !== actual.length || [...actual].sort().join("|") !== [...expected].sort().join("|")) throw new Error(`${path}: IDs do not match the request`);
}
function optionFor(options: DecisionOption[], id: OptionId): DecisionOption {
  const option = options.find((item) => item.id === id);
  if (!option) throw new Error(`options: missing ${id}`);
  return option;
}

export type SimulateInput = {
  datasetId: string;
  scenarios: Scenario[];
  options: DecisionOption[];
  selectedScenarioId: string;
  demandShift: number;
  riskThresholdPct: number;
  budgetCeilingUsd: number;
  seed: number;
};

/** Builds the shared v1 request without mutating the frozen Day 2 scenario/option data. */
export function buildSimulateRequest(input: SimulateInput): SimulateRequest {
  const datasetId = text(input.datasetId, "datasetId");
  if (!Array.isArray(input.scenarios) || !input.scenarios.length) throw new Error("scenarios: at least one scenario is required");
  if (!input.scenarios.some((scenario) => scenario.id === input.selectedScenarioId)) throw new Error("selectedScenarioId: unknown scenario");
  if (!Number.isFinite(input.demandShift) || input.demandShift < -100 || input.demandShift > 1000) throw new Error("demandShift: outside supported range");
  if (!Number.isFinite(input.riskThresholdPct) || input.riskThresholdPct < 0 || input.riskThresholdPct > 100) throw new Error("riskThresholdPct: outside [0, 100]");
  if (!Number.isInteger(input.budgetCeilingUsd) || input.budgetCeilingUsd < 0) throw new Error("budgetCeilingUsd: expected a non-negative whole USD amount");
  if (!Number.isInteger(input.seed) || input.seed < 0) throw new Error("seed: expected a non-negative integer");
  const scenarios = input.scenarios.map((scenario) => {
    if (scenario.id !== input.selectedScenarioId) return { ...scenario };
    const oldFactor = 1 + scenario.demandShock / 100;
    const newFactor = 1 + input.demandShift / 100;
    if (oldFactor <= 0) throw new Error("scenario demandShock: cannot rescale a zero-demand scenario");
    return { ...scenario, demandShock: input.demandShift, demandUnits24m: Math.max(0, Math.round(scenario.demandUnits24m * newFactor / oldFactor)) };
  });
  return {
    schemaVersion: SCHEMA_VERSION,
    datasetId,
    scenarios,
    options: input.options.map((option) => ({ ...option })),
    seed: input.seed,
    riskThreshold: input.riskThresholdPct / 100,
    budgetCeilingUsd: input.budgetCeilingUsd
  };
}

/** Strictly validates the public success envelope and recomputes all code-bound deltas/selections. */
export function validateSimulateSuccess(input: unknown, request: SimulateRequest): asserts input is ApiSuccess<SimulateResponse> {
  const envelope = obj(input, "response");
  if (envelope.schemaVersion !== SCHEMA_VERSION) throw new Error("response.schemaVersion: unsupported contract version");
  const dataVersion = text(envelope.dataVersion, "response.dataVersion");
  text(envelope.requestId, "response.requestId");
  const data = obj(envelope.data, "response.data");
  const simulation = obj(data.simulation, "response.data.simulation");
  const simulationId = text(simulation.simulationId, "simulation.simulationId");
  if (simulationId.toLowerCase().includes("mock")) throw new Error("simulation.simulationId: mock snapshots are not live simulations");
  const simulationDataVersion = text(simulation.dataVersion, "simulation.dataVersion");
  if (simulationDataVersion !== dataVersion) throw new Error("simulation.dataVersion: does not match envelope");
  if (text(simulation.formulaVersion, "simulation.formulaVersion") !== "tco-v1") throw new Error("simulation.formulaVersion: unsupported formula version");
  if (simulation.seed !== request.seed) throw new Error("simulation.seed: does not match request");
  if (num(simulation.weeks, "simulation.weeks", 0, Infinity, true) !== 104) throw new Error("simulation.weeks: expected 104");
  const monteCarloRuns = num(simulation.monteCarloRuns, "simulation.monteCarloRuns", 1, Infinity, true);
  if (monteCarloRuns < 1) throw new Error("simulation.monteCarloRuns: live runs must be positive");
  const prices = obj(simulation.unitPricesUsd, "simulation.unitPricesUsd");
  const priceA = num(prices.A, "unitPricesUsd.A", 0);
  const priceB = num(prices.B, "unitPricesUsd.B", 0);
  const matrix = obj(simulation.matrix, "simulation.matrix");
  const scenarioIds = request.scenarios.map((scenario) => scenario.id);
  compareIds(Object.keys(matrix), scenarioIds, "simulation.matrix");
  const normalizedCells: Record<string, Map<OptionId, MetricCell>> = {};

  for (const scenario of request.scenarios) {
    const rows = arr(matrix[scenario.id], `matrix.${scenario.id}`).map((value, index) => obj(value, `matrix.${scenario.id}[${index}]`));
    compareIds(rows.map((row) => text(row.optionId, `matrix.${scenario.id}.optionId`)), OPTION_ORDER, `matrix.${scenario.id}.options`);
    const byOption = new Map<OptionId, MetricCell>();
    for (const [index, row] of rows.entries()) {
      const path = `matrix.${scenario.id}[${index}]`;
      const optionId = text(row.optionId, `${path}.optionId`) as OptionId;
      const feasible = bool(row.feasible, `${path}.feasible`);
      const expectedTco = num(row.expectedTco, `${path}.expectedTco`, 0, Infinity, true);
      const stockoutProbability = num(row.stockoutProbability, `${path}.stockoutProbability`, 0, 1);
      const serviceLevel = num(row.serviceLevel, `${path}.serviceLevel`, 0, 1);
      const cashOutflowP90 = num(row.cashOutflowP90, `${path}.cashOutflowP90`, 0, Infinity, true);
      const unitsFromA = num(row.unitsFromA, `${path}.unitsFromA`, 0, Infinity, true);
      const unitsFromB = num(row.unitsFromB, `${path}.unitsFromB`, 0, Infinity, true);
      if (!["neutral", "recommended", "risk"].includes(text(row.tone, `${path}.tone`))) throw new Error(`${path}.tone: invalid tone`);
      const breakdownRaw = obj(row.breakdown, `${path}.breakdown`);
      const breakdown = {
        purchase: num(breakdownRaw.purchase, `${path}.breakdown.purchase`, 0, Infinity, true),
        holding: num(breakdownRaw.holding, `${path}.breakdown.holding`, 0, Infinity, true),
        stockoutLoss: num(breakdownRaw.stockoutLoss, `${path}.breakdown.stockoutLoss`, 0, Infinity, true),
        renewalPremium: num(breakdownRaw.renewalPremium, `${path}.breakdown.renewalPremium`, 0, Infinity, true),
        terminationFee: num(breakdownRaw.terminationFee, `${path}.breakdown.terminationFee`, 0, Infinity, true)
      };
      if (Object.values(breakdown).reduce((sum, value) => sum + value, 0) !== expectedTco) throw new Error(`${path}: cost breakdown does not sum to TCO`);
      if (Math.abs(breakdown.purchase - (unitsFromA * priceA + unitsFromB * priceB)) > 0.50000001) throw new Error(`${path}: purchase does not reconcile to units and base prices`);
      const option = optionFor(request.options, optionId);
      const totalUnits = unitsFromA + unitsFromB;
      if (totalUnits <= 0) throw new Error(`${path}: no purchased units`);
      sameNumber(unitsFromA / totalUnits, option.shareA, `${path}: allocation`);
      byOption.set(optionId, { optionId, feasible, expectedTco, stockoutProbability, serviceLevel, cashOutflowP90, breakdown, unitsFromA, unitsFromB, tone: row.tone as MetricCell["tone"] });
    }
    normalizedCells[scenario.id] = byOption;
  }

  const deltas = arr(data.deltas, "response.data.deltas").map((value, index) => obj(value, `deltas[${index}]`));
  const expectedPairs = request.scenarios.flatMap((scenario) => OPTION_ORDER.map((optionId) => `${scenario.id}/${optionId}`));
  const actualPairs = deltas.map((delta) => `${text(delta.scenarioId, "delta.scenarioId")}/${text(delta.optionId, "delta.optionId")}`);
  compareIds(actualPairs, expectedPairs, "deltas");
  for (const delta of deltas) {
    const scenarioId = delta.scenarioId as string;
    const optionId = delta.optionId as OptionId;
    if (delta.baselineOptionId !== "D0") throw new Error("delta.baselineOptionId: v1 baseline must be D0");
    const cell = normalizedCells[scenarioId]?.get(optionId);
    const baseline = normalizedCells[scenarioId]?.get("D0");
    if (!cell || !baseline) throw new Error(`delta: missing matrix cell for ${scenarioId}/${optionId}`);
    sameNumber(num(delta.deltaTco, "delta.deltaTco", -Infinity, Infinity, true), cell.expectedTco - baseline.expectedTco, "delta.deltaTco");
    sameNumber(num(delta.deltaStockoutPp, "delta.deltaStockoutPp", -100, 100), Number(((cell.stockoutProbability - baseline.stockoutProbability) * 100).toFixed(10)), "delta.deltaStockoutPp");
    sameNumber(num(delta.deltaServicePp, "delta.deltaServicePp", -100, 100), Number(((cell.serviceLevel - baseline.serviceLevel) * 100).toFixed(10)), "delta.deltaServicePp");
    sameNumber(num(delta.deltaCashP90, "delta.deltaCashP90", -Infinity, Infinity, true), cell.cashOutflowP90 - baseline.cashOutflowP90, "delta.deltaCashP90");
  }

  const selections = obj(data.selections, "response.data.selections");
  compareIds(Object.keys(selections), scenarioIds, "selections");
  for (const scenario of request.scenarios) {
    const raw = obj(selections[scenario.id], `selections.${scenario.id}`);
    if (raw.scenarioId !== scenario.id) throw new Error(`selections.${scenario.id}.scenarioId: mismatch`);
    const rows = normalizedCells[scenario.id];
    const violations: Array<{ optionId: OptionId; code: typeof VIOLATION_ORDER[number] }> = [];
    const eligible: Array<{ optionId: OptionId; expectedTco: number }> = [];
    for (const optionId of OPTION_ORDER) {
      const cell = rows.get(optionId)!;
      const codes: typeof VIOLATION_ORDER[number][] = [];
      if (!cell.feasible) codes.push("infeasible");
      if (cell.stockoutProbability > request.riskThreshold) codes.push("stockout_threshold");
      if (cell.cashOutflowP90 > request.budgetCeilingUsd) codes.push("cash_ceiling");
      if (codes.length) codes.forEach((code) => violations.push({ optionId, code }));
      else eligible.push({ optionId, expectedTco: cell.expectedTco });
    }
    eligible.sort((a, b) => a.expectedTco - b.expectedTco || a.optionId.localeCompare(b.optionId));
    const actualViolations = arr(raw.constraintViolations, `selections.${scenario.id}.constraintViolations`).map((value, index) => {
      const violation = obj(value, `selections.${scenario.id}.constraintViolations[${index}]`);
      const optionId = text(violation.optionId, "constraintViolation.optionId") as OptionId;
      const code = text(violation.code, "constraintViolation.code");
      if (!OPTION_ORDER.includes(optionId) || !VIOLATION_ORDER.includes(code as typeof VIOLATION_ORDER[number])) throw new Error("constraintViolation: unknown option/code");
      return { optionId, code };
    });
    if (JSON.stringify(actualViolations) !== JSON.stringify(violations)) throw new Error(`selections.${scenario.id}: violations do not match the matrix and request constraints`);
    if (eligible.length) {
      if (raw.status !== "selected" || raw.recommendedOptionId !== eligible[0].optionId) throw new Error(`selections.${scenario.id}: winner does not follow the v1 constraint/TCO rule`);
    } else if (raw.status !== "no_feasible_option" || raw.recommendedOptionId !== null) {
      throw new Error(`selections.${scenario.id}: no-feasible result must not invent a winner`);
    }
  }
}

/** Validate the complete v2 trace while keeping reviewed and development modes isolated. */
function validateV2(input: unknown, request: SimulateRequest, headers: Pick<Headers, "get">, reviewed: boolean): SimulationApiResult {
  if (!reviewed && process.env.NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE !== DEV_MODE_SENTINEL) throw new Error("v2 development response rejected: explicit UNREVIEWED_DEV_ONLY frontend opt-in is required");
  if (headers.get("x-causora-review-status") !== (reviewed ? "reviewed" : "unreviewed-development-only") || headers.get("x-causora-execution-mode") !== (reviewed ? "reviewed-release-gated" : "unreviewed-development-only") || (reviewed && headers.get("x-causora-trace-contract") !== SCHEMA_VERSION_V2)) throw new Error("v2 response rejected: required execution/review/contract headers are missing");
  const envelope = obj(input, "response");
  if (envelope.schemaVersion !== SCHEMA_VERSION_V2) throw new Error("response.schemaVersion: unsupported v2 version");
  const dataVersion = text(envelope.dataVersion, "response.dataVersion");
  const requestId = text(envelope.requestId, "response.requestId");
  if (!reviewed && !dataVersion.includes("UNREVIEWED_DEV_ONLY")) throw new Error("response.dataVersion: explicit development marker is required");
  const data = obj(envelope.data, "response.data");
  const rawContext = obj(data.executionContext, "response.data.executionContext");
  const context = {
    mode: text(rawContext.mode, "executionContext.mode"), banner: text(rawContext.banner, "executionContext.banner"),
    humanReviewStatus: text(rawContext.humanReviewStatus, "executionContext.humanReviewStatus"),
    policyStatus: text(rawContext.policyStatus, "executionContext.policyStatus"),
    contractReleaseStatus: text(rawContext.contractReleaseStatus, "executionContext.contractReleaseStatus"),
    decisionReady: bool(rawContext.decisionReady, "executionContext.decisionReady")
  };
  if (reviewed && (context.mode !== "reviewed_release_gated" || context.humanReviewStatus !== "reviewed" || context.policyStatus !== "approved" || context.contractReleaseStatus !== "released" || context.decisionReady !== true || /unreviewed|unapproved/i.test(context.banner + dataVersion))) throw new Error("executionContext: incomplete reviewed release status");
  if (!reviewed && (context.mode !== "unreviewed_development_only" || context.humanReviewStatus !== "not_reviewed_development_only" || context.policyStatus !== "unapproved_development_only" || context.contractReleaseStatus !== "not_released_development_only" || context.decisionReady !== false || !context.banner.toUpperCase().includes("UNREVIEWED"))) throw new Error("executionContext: inconsistent or decision-ready development status");
  const normalized: unknown = { schemaVersion: SCHEMA_VERSION, dataVersion, requestId, data: { simulation: data.simulation, deltas: data.deltas, selections: data.selections } };
  validateSimulateSuccess(normalized, request);
  const normalizedData = obj(obj(normalized, "response").data, "response.data");
  const simulation = obj(normalizedData.simulation, "response.data.simulation");
  const monteCarloRuns = num(simulation.monteCarloRuns, "simulation.monteCarloRuns", 1, Infinity, true);
  if (!reviewed && !text(simulation.simulationId, "simulation.simulationId").toLowerCase().includes("unreviewed")) throw new Error("simulation.simulationId: development identity marker is required");
  const matrix = obj(simulation.matrix, "simulation.matrix");
  const rawTraces = obj(data.traces, "response.data.traces");
  const scenarioIds = request.scenarios.map((scenario) => scenario.id);
  compareIds(Object.keys(rawTraces), scenarioIds, "response.data.traces");
  const componentKeys = ["purchase", "holding", "stockoutLoss", "renewalPremium", "terminationFee"] as const;
  const weekCountKeys = ["openingUnits", "arrivalsA", "arrivalsB", "demandUnits", "availableUnits", "fulfilledUnits", "lostUnits", "endingUnits", "onOrderUnitsBefore", "inventoryPositionBefore", "reorderPointUnits", "orderedA", "orderedB", "onOrderUnitsAfter"] as const;
  if (reviewed && /unreviewed/i.test(text(simulation.simulationId, "simulation.simulationId"))) throw new Error("reviewed simulation contains a development identity");
  let sharedIdentity: string | undefined;
  const traces: Record<string, Record<OptionId, V2FormulaTrace>> = {};
  for (const scenarioId of scenarioIds) {
    const scenarioTraces = obj(rawTraces[scenarioId], `traces.${scenarioId}`);
    compareIds(Object.keys(scenarioTraces), OPTION_ORDER, `traces.${scenarioId}`);
    const cells = arr(matrix[scenarioId], `matrix.${scenarioId}`).map((value, index) => obj(value, `matrix.${scenarioId}[${index}]`));
    const checked = {} as Record<OptionId, V2FormulaTrace>;
    for (const optionId of OPTION_ORDER) {
      const path = `traces.${scenarioId}.${optionId}`;
      const trace = obj(scenarioTraces[optionId], path);
      const cell = cells.find((row) => row.optionId === optionId);
      if (!cell) throw new Error(`${path}: matching matrix cell is missing`);
      if (trace.traceSchemaVersion !== "causora.formula-trace.v1" || trace.scenarioId !== scenarioId || trace.optionId !== optionId || trace.simulationId !== simulation.simulationId || trace.dataVersion !== dataVersion || trace.formulaVersion !== simulation.formulaVersion) throw new Error(`${path}: trace identity differs from the matrix run`);
      const identity = obj(trace.runIdentity, `${path}.runIdentity`);
      if (identity.executionMode !== context.mode || (!reviewed && (identity.reviewRecordId !== null || identity.reviewRecordSha256 !== null))) throw new Error(`${path}.runIdentity: a development trace must not claim human review`);
      for (const key of ["contractPayloadSha256", "policySha256", "contractReleaseRecordSha256"] as const) if (!/^[a-f0-9]{64}$/.test(text(identity[key], `${path}.runIdentity.${key}`))) throw new Error(`${path}.runIdentity.${key}: expected SHA-256`);
      text(identity.policyApprovalReference, `${path}.runIdentity.policyApprovalReference`);
      text(identity.policyConfigurationId, `${path}.runIdentity.policyConfigurationId`);
      text(identity.contractApprovalReference, `${path}.runIdentity.contractApprovalReference`);
      if (reviewed) {
        text(identity.reviewRecordId, `${path}.runIdentity.reviewRecordId`);
        if (!/^[a-f0-9]{64}$/.test(text(identity.reviewRecordSha256, `${path}.runIdentity.reviewRecordSha256`))) throw new Error(`${path}: missing reviewed record hash`);
      }
      const identityKey = JSON.stringify(Object.keys(identity).sort().map((key) => [key, identity[key]]));
      if (sharedIdentity && identityKey !== sharedIdentity) throw new Error(`${path}: traces do not share one release identity`);
      sharedIdentity = identityKey;
      const expectedTco = num(trace.expectedTcoUsd, `${path}.expectedTcoUsd`, 0, Infinity, true);
      if (expectedTco !== cell.expectedTco) throw new Error(`${path}: TCO differs from the matching matrix cell`);
      const breakdown = obj(cell.breakdown, `${path}.matrix.breakdown`);
      const components = arr(trace.components, `${path}.components`);
      compareIds(components.map((value, index) => text(obj(value, `${path}.components[${index}]`).key, `${path}.components[${index}].key`)), [...componentKeys], `${path}.components`);
      let sum = 0;
      for (const [index, value] of components.entries()) {
        const componentPath = `${path}.components[${index}]`;
        const component = obj(value, componentPath);
        const key = text(component.key, `${componentPath}.key`) as typeof componentKeys[number];
        text(component.formula, `${componentPath}.formula`);
        const inputs = arr(component.inputKeys, `${componentPath}.inputKeys`);
        if (!inputs.length) throw new Error(`${componentPath}.inputKeys: expected at least one input`);
        inputs.forEach((input, inputIndex) => text(input, `${componentPath}.inputKeys[${inputIndex}]`));
        const valueUsd = num(component.valueUsd, `${componentPath}.valueUsd`, 0, Infinity, true);
        if (valueUsd !== breakdown[key]) throw new Error(`${componentPath}: differs from the matrix breakdown`);
        const audit = obj(component.roundingAudit, `${componentPath}.roundingAudit`);
        const rawMean = Number(text(audit.rawMeanUsd, `${componentPath}.roundingAudit.rawMeanUsd`));
        const displayed = num(audit.displayedValueUsd, `${componentPath}.roundingAudit.displayedValueUsd`, 0, Infinity, true);
        const difference = Number(text(audit.displayedMinusRawMeanUsd, `${componentPath}.roundingAudit.displayedMinusRawMeanUsd`));
        text(audit.method, `${componentPath}.roundingAudit.method`);
        if (!Number.isFinite(rawMean) || !Number.isFinite(difference) || displayed !== valueUsd || Math.abs(displayed - rawMean - difference) > 1e-6) throw new Error(`${componentPath}.roundingAudit: displayed/raw amounts do not reconcile`);
        sum += valueUsd;
      }
      if (sum !== expectedTco) throw new Error(`${path}: formula components do not sum to TCO`);
      const stockout = obj(trace.stockoutProbability, `${path}.stockoutProbability`);
      const stockoutValue = num(stockout.value, `${path}.stockoutProbability.value`, 0, 1);
      const numerator = num(stockout.numeratorStockoutRuns, `${path}.stockoutProbability.numeratorStockoutRuns`, 0, Infinity, true);
      const denominator = num(stockout.denominatorRuns, `${path}.stockoutProbability.denominatorRuns`, 1, Infinity, true);
      if (stockout.definition !== "trials_with_at_least_one_lost_unit / monteCarloRuns" || denominator !== monteCarloRuns || numerator > denominator || Math.abs(stockoutValue - numerator / denominator) > 1e-12 || stockoutValue !== cell.stockoutProbability) throw new Error(`${path}.stockoutProbability: count basis mismatch`);
      const service = obj(trace.serviceLevel, `${path}.serviceLevel`);
      const serviceValue = num(service.value, `${path}.serviceLevel.value`, 0, 1);
      const fulfilled = num(service.fulfilledUnitsAllRuns, `${path}.serviceLevel.fulfilledUnitsAllRuns`, 0, Infinity, true);
      const demand = num(service.demandUnitsAllRuns, `${path}.serviceLevel.demandUnitsAllRuns`, 0, Infinity, true);
      if (service.definition !== "fulfilled_units_all_runs / demand_units_all_runs" || fulfilled > demand || Math.abs(serviceValue - (demand ? fulfilled / demand : 1)) > 1e-12 || serviceValue !== cell.serviceLevel) throw new Error(`${path}.serviceLevel: aggregate counts mismatch`);
      const cash = obj(trace.cashOutflowP90, `${path}.cashOutflowP90`);
      const cashValue = num(cash.valueUsd, `${path}.cashOutflowP90.valueUsd`, 0, Infinity, true);
      const runs = num(cash.denominatorRuns, `${path}.cashOutflowP90.denominatorRuns`, 1, Infinity, true);
      if (cash.method !== "nearest_rank_ceil_0.90N" || cash.percentile !== 0.9 || cash.rankOneBased !== Math.ceil(0.9 * runs) || runs !== denominator || cashValue !== cell.cashOutflowP90 || JSON.stringify(cash.includedCashComponents) !== JSON.stringify(["purchase", "holding", "renewalPremium", "terminationFee"]) || JSON.stringify(cash.excludedNonCashComponents) !== JSON.stringify(["stockoutLoss"]) || cash.perRunRounding !== "whole_usd_half_even") throw new Error(`${path}.cashOutflowP90: rank or cash basis mismatch`);
      const sample = obj(trace.samplePath, `${path}.samplePath`);
      if (sample.classification !== "single_realised_trial_not_aggregate") throw new Error(`${path}.samplePath: must be one realised trial`);
      const note = text(sample.note, `${path}.samplePath.note`).toLowerCase();
      if (!note.includes("not") || !["average", "aggregate", "expectation"].some((word) => note.includes(word))) throw new Error(`${path}.samplePath.note: missing non-aggregate warning`);
      if (num(sample.sampleRunIndex, `${path}.samplePath.sampleRunIndex`, 0, monteCarloRuns - 1, true) < 0) throw new Error(`${path}.samplePath: invalid run index`);
      const weeks = arr(sample.weeks, `${path}.samplePath.weeks`);
      if (weeks.length !== 104) throw new Error(`${path}.samplePath.weeks: expected 104 weeks`);
      for (const [index, value] of weeks.entries()) {
        const week = obj(value, `${path}.samplePath.weeks[${index}]`);
        if (num(week.week, `${path}.samplePath.weeks[${index}].week`, 1, 104, true) !== index + 1) throw new Error(`${path}.samplePath.weeks: invalid sequence`);
        text(week.startDate, `${path}.samplePath.weeks[${index}].startDate`);
        for (const key of weekCountKeys) num(week[key], `${path}.samplePath.weeks[${index}].${key}`, 0, Infinity, true);
        for (const key of ["sampledLeadDaysA", "sampledLeadDaysB", "plannedArrivalWeekA", "plannedArrivalWeekB"] as const) if (week[key] !== null) num(week[key], `${path}.samplePath.weeks[${index}].${key}`, 0, Infinity, true);
        for (const key of ["holdingRawUsd", "stockoutLossRawUsd", "basePurchaseRawUsd", "renewalPremiumRawUsd", "terminationFeeRawUsd"] as const) text(week[key], `${path}.samplePath.weeks[${index}].${key}`);
      }
      text(trace.summaryRoundingRule, `${path}.summaryRoundingRule`);
      const parameters = arr(trace.parameters, `${path}.parameters`);
      if (!parameters.length) throw new Error(`${path}.parameters: expected parameter provenance`);
      const parameterKeys = new Set<string>();
      for (const [index, value] of parameters.entries()) {
        const parameterPath = `${path}.parameters[${index}]`;
        const parameter = obj(value, parameterPath);
        const key = text(parameter.key, `${parameterPath}.key`);
        if (parameterKeys.has(key)) throw new Error(`${parameterPath}.key: duplicate key`);
        parameterKeys.add(key);
        text(parameter.unit, `${parameterPath}.unit`);
        if (!(typeof parameter.value === "string" || typeof parameter.value === "boolean" || (typeof parameter.value === "number" && Number.isFinite(parameter.value)))) throw new Error(`${parameterPath}.value: invalid typed value`);
        const provenance = obj(parameter.provenance, `${parameterPath}.provenance`);
        const kind = text(provenance.kind, `${parameterPath}.provenance.kind`);
        const status = text(provenance.status, `${parameterPath}.provenance.status`);
        const expectedStatus: Record<string, string> = { reviewed_contract: "reviewed", unreviewed_development_contract: "unreviewed_development_only", approved_operating_assumption: "approved", unreviewed_development_assumption: "unreviewed_development_only", observed_synthetic_dataset: "observed", derived_formula: "derived" };
        if (expectedStatus[kind] !== status) throw new Error(`${parameterPath}.provenance: kind/status mismatch`);
        text(provenance.sourceId, `${parameterPath}.provenance.sourceId`);
        text(provenance.note, `${parameterPath}.provenance.note`);
        if (reviewed && kind.startsWith("unreviewed")) throw new Error(`${parameterPath}: unreviewed provenance in a reviewed release`);
        if (key.startsWith("contract.") && kind !== (reviewed ? "reviewed_contract" : "unreviewed_development_contract")) throw new Error(`${parameterPath}: contract provenance does not match execution mode`);
        if (reviewed && kind === "reviewed_contract") {
          if (provenance.reviewRecordId !== identity.reviewRecordId || provenance.reviewRecordSha256 !== identity.reviewRecordSha256) throw new Error(`${parameterPath}: review identity mismatch`);
          if (!arr(provenance.evidenceIds, `${parameterPath}.evidenceIds`).length) throw new Error(`${parameterPath}: missing evidence identifiers`);
        } else if (provenance.reviewRecordId !== null || provenance.reviewRecordSha256 !== null) throw new Error(`${parameterPath}: provenance incorrectly claims human review`);
        if (["reviewed_contract", "approved_operating_assumption", "observed_synthetic_dataset"].includes(kind)) {
          if (kind !== "approved_operating_assumption" || provenance.sourceFile !== null) text(provenance.sourceFile, `${parameterPath}.sourceFile`);
          if (!/^[a-f0-9]{64}$/.test(text(provenance.sourceSha256, `${parameterPath}.sourceSha256`))) throw new Error(`${parameterPath}: missing source hash`);
        }
        if (kind === "approved_operating_assumption" && provenance.sourceSha256 !== identity.policySha256) throw new Error(`${parameterPath}: policy hash mismatch`);
      }
      for (const [index, value] of components.entries()) for (const input of arr(obj(value, `${path}.components[${index}]`).inputKeys, `${path}.components[${index}].inputKeys`)) if (!parameterKeys.has(String(input))) throw new Error(`${path}.components: unresolved input key ${String(input)}`);
      checked[optionId] = trace as unknown as V2FormulaTrace;
    }
    traces[scenarioId] = checked;
  }
  const details = { executionContext: context, traces };
  return reviewed
    ? { response: normalized as ApiSuccess<SimulateResponse>, integrationMode: "reviewed-v2", development: details as ReviewedSimulationDetails }
    : { response: normalized as ApiSuccess<SimulateResponse>, integrationMode: "unreviewed-v2-dev", development: details as DevSimulationDetails };
}

export function validateUnreviewedV2Development(input: unknown, request: SimulateRequest, headers: Pick<Headers, "get">): SimulationApiResult {
  return validateV2(input, request, headers, false);
}
export function validateReviewedV2Success(input: unknown, request: SimulateRequest, headers: Pick<Headers, "get">): SimulationApiResult {
  return validateV2(input, request, headers, true);
}

export class SimulationApiError extends Error {
  readonly code: string;
  readonly requestId?: string;
  readonly status?: number;
  constructor(message: string, code = "simulation_failed", requestId?: string, status?: number) {
    super(message);
    this.name = "SimulationApiError";
    this.code = code;
    this.requestId = requestId;
    this.status = status;
  }
}

export function getSimulateEndpoint(): string {
  const base = typeof process !== "undefined" ? process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL?.trim() ?? "" : "";
  return base ? `${base.replace(/\/+$/, "")}/api/simulate` : "/api/simulate";
}

/** Sends one v1 request and rejects HTTP, version, accounting, delta or selection mismatches. */
export async function postSimulate(request: SimulateRequest, fetcher: typeof fetch = fetch): Promise<SimulationApiResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetcher(getSimulateEndpoint(), {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify(request),
      cache: "no-store",
      signal: controller.signal
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const body = payload && typeof payload === "object" && !Array.isArray(payload) ? payload as Obj : {};
      const error = body.error && typeof body.error === "object" && !Array.isArray(body.error) ? body.error as Obj : {};
      const message = typeof error.message === "string" && error.message.trim() ? error.message : `Simulation API returned HTTP ${response.status}.`;
      throw new SimulationApiError(message, typeof error.code === "string" ? error.code : "simulation_failed", typeof error.requestId === "string" ? error.requestId : undefined, response.status);
    }
    if (payload && typeof payload === "object" && !Array.isArray(payload) && (payload as Obj).schemaVersion === SCHEMA_VERSION_V2) return obj(obj(payload, "response").data, "response.data").executionContext && obj(obj(obj(payload, "response").data, "response.data").executionContext, "executionContext").mode === "reviewed_release_gated" ? validateReviewedV2Success(payload, request, response.headers) : validateUnreviewedV2Development(payload, request, response.headers);
    validateSimulateSuccess(payload, request);
    return { response: payload as ApiSuccess<SimulateResponse>, integrationMode: "v1" };
  } catch (error) {
    if (error instanceof SimulationApiError) throw error;
    if (controller.signal.aborted) throw new SimulationApiError("Simulation request timed out. The saved Day 2 example remains available; no draft result was applied.", "provider_timeout");
    const message = error instanceof Error ? error.message : "Unknown network error";
    throw new SimulationApiError(`Could not validate a live /api/simulate response: ${message}`, "simulation_failed");
  } finally {
    clearTimeout(timer);
  }
}
