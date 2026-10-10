/**
 * Causora frozen integration contract — Day 1 draft v1.
 *
 * Every cross-module object named in the build specification is declared here:
 * Scenario, DecisionOption, ContractConstraint, BusinessVariable, SimulationResult,
 * DecisionDelta, EvidenceRecord, AgentOutput, CriticIssue, DecisionBriefRef.
 *
 * Unit conventions (fixed for the whole project):
 * - Money: integer US dollars (`number`), never pre-formatted strings. UI formats as `$420k`.
 * - Probabilities and shares: decimal fractions in [0, 1] (`0.09` = 9%). UI formats as `9%`.
 * - Percent changes supplied by scenarios: whole percent (`-15` = −15%).
 * - Units: integer units. Durations: integer days or months, as named by the field.
 * - Dates: ISO-8601 `YYYY-MM-DD`. Timestamps: ISO-8601 UTC with `Z`.
 * - Identifiers: option IDs `D0|D1|D2`; evidence IDs `EV-###`; scenario IDs kebab-case.
 *
 * Versioning: `schemaVersion` changes only with a breaking shape change; `dataVersion`
 * identifies a frozen dataset; `formulaVersion` identifies the cost formula convention.
 * A response is valid only if its `schemaVersion` equals the one compiled into the frontend.
 */

export const SCHEMA_VERSION = "causora.contract.v1" as const;

export type OptionId = "D0" | "D1" | "D2";

export type Scenario = {
  id: string;
  label: string;
  tag: string;
  /** Whole-percent demand multiplier change relative to the historical distribution, e.g. -15. */
  demandShock: number;
  /** Realised 24-month demand units implied by the scenario (mock: deterministic). */
  demandUnits24m: number;
  leadTime: string;
  /** Lead-time variability multiplier applied to sampled lead times (1 = historical). */
  leadTimeMultiplier: number;
  description: string;
};

export type DecisionOption = {
  id: OptionId;
  label: string;
  /** Actual share of total purchased units routed to Supplier A in each scenario. D1 stays exactly 60/40. */
  shareA: number;
  /** Whether the option terminates the renewed Supplier A agreement. */
  terminateA: boolean;
  allocation: string;
  short: string;
  description: string;
};

export type EvidenceRecord = {
  id: string;
  sourceFile: string;
  page: number;
  quote: string;
  /** Optional PDF bounding box [x0, y0, x1, y1] in PDF points; null when not yet located. */
  locatorBbox: [number, number, number, number] | null;
  extractedField: string;
  extractedValue: string;
  matchMethod: "exact" | "fuzzy";
  /** Match score as a decimal fraction in [0, 1]. */
  matchScore: number;
  quoteMatched: boolean;
};

export type ContractConstraint = {
  decisionDate: string;
  renewalDate: string;
  daysToRenewal: number;
  renewalNoticeDays: number;
  /** ISO date by which written notice had to be received. */
  noticeDeadline: string;
  /** Whether a written notice record exists before the deadline (mock input, not inferred). */
  noticeSent: boolean;
  noticeRecordSource: string;
  renewalLocked: boolean;
  renewalTermMonths: number;
  renewalPriceIncreasePct: number;
  minPurchaseShareA: number;
  /** Which demand forecast the minimum purchase commitment is measured against. */
  forecastBasis: "locked-at-renewal" | "rolling";
  lockedForecastUnits24m: number;
  minPurchaseUnitsA: number;
  terminationFeeUsd: number;
  evidenceIds: string[];
};

export type BusinessVariable = {
  key: string;
  name: string;
  value: string;
  unit: string;
  source: string;
  meaning: string;
  /** Named inputs that produced the variable, for the Formula/variable trace. */
  inputs: Array<{ name: string; value: string; source: string }>;
};

export type CostBreakdown = {
  purchase: number;
  holding: number;
  stockoutLoss: number;
  renewalPremium: number;
  terminationFee: number;
};

export type MetricCell = {
  optionId: OptionId;
  feasible: boolean;
  /** Expected 24-month total cost of ownership, USD. Equals the sum of `breakdown`. */
  expectedTco: number;
  stockoutProbability: number;
  serviceLevel: number;
  cashOutflowP90: number;
  breakdown: CostBreakdown;
  /** Supplier A units purchased at base price before the premium uplift. */
  unitsFromA: number;
  /** Together with unitsFromA, this can exceed realised demand under a fixed commitment. */
  unitsFromB: number;
  tone: "neutral" | "recommended" | "risk";
};

export type SimulationResult = {
  simulationId: string;
  seed: number;
  dataVersion: string;
  formulaVersion: string;
  weeks: number;
  monteCarloRuns: number;
  unitPricesUsd: { A: number; B: number };
  /** scenarioId -> one cell per option. */
  matrix: Record<string, MetricCell[]>;
};

export type DecisionDelta = {
  scenarioId: string;
  optionId: OptionId;
  baselineOptionId: OptionId;
  deltaTco: number;
  deltaStockoutPp: number;
  deltaServicePp: number;
  deltaCashP90: number;
};

export type AgentOutput = {
  role: "CFO" | "COO" | "Risk";
  accent: string;
  focus: string;
  headline: string;
  /** Template text; numbers may appear only through `{{token}}` metric or evidence references. */
  body: string;
  metrics: string[];
  status: "Aligned" | "Watch";
};

export type CriticIssue = {
  severity: string;
  headline: string;
  body: string;
  evidenceIds: string[];
  /** Structured mechanism so simulation and Critic share one definition of the compound risk. */
  mechanism: {
    scenarioId: string;
    forecastBasis: ContractConstraint["forecastBasis"];
    lockedForecastUnits24m: number;
    minPurchaseUnitsA: number;
    scenarioDemandUnits24m: number;
    committedExcessUnits: number;
    holdingCostDeltaUsd: Record<OptionId, number>;
  };
};

export type SelectedDecisionBriefRef = {
  recommendedOptionId: OptionId;
  recommendation: string;
  rationale: string;
  metricRefs: string[];
  formula: string;
  formulaVersion: string;
  formulaNotes: string[];
  guardrail: string;
};

export type ApiError = {
  code: "validation_error" | "not_found" | "provider_timeout" | "simulation_failed" | "internal_error";
  message: string;
  details?: Record<string, unknown>;
  requestId: string;
};


/** Recommendations are local to one scenario; never an implicit multi-scenario winner. */
export type ConstraintViolation = { optionId: OptionId; code: "infeasible" | "stockout_threshold" | "cash_ceiling" };
export type ScenarioSelection =
  | { scenarioId: string; status: "selected"; recommendedOptionId: OptionId; constraintViolations: ConstraintViolation[] }
  | { scenarioId: string; status: "no_feasible_option"; recommendedOptionId: null; constraintViolations: ConstraintViolation[] };
export type NoFeasibleBrief = { scenarioId: string; status: "no_feasible_option"; recommendedOptionId: null; constraintViolations: ConstraintViolation[]; message: string };
export type DecisionBriefRef = (SelectedDecisionBriefRef & { scenarioId: string; status: "selected" }) | NoFeasibleBrief;
export type ApiSuccess<T> = { schemaVersion: typeof SCHEMA_VERSION; dataVersion: string; requestId: string; data: T };
export type ApiFailure = { schemaVersion: typeof SCHEMA_VERSION; requestId: string; error: ApiError };
export type DatasetRequestFields = "historical_demand" | "supplier_delivery" | "opening_inventory" | "supplier_agreement" | "notice_register";
export type IntakeFile = { id: string; label: string; type: string; detail: string; size: string; status: string; icon: string; path: string };
export type DatasetResult = { datasetId: string; preprocessStatus: "ready"; dataVersion: string; intake: IntakeFile[]; evidence: EvidenceRecord[]; contract: ContractConstraint; variables: BusinessVariable[] };
export type SimulateRequest = { schemaVersion: typeof SCHEMA_VERSION; datasetId: string; scenarios: Scenario[]; options: DecisionOption[]; seed: number; riskThreshold: number; budgetCeilingUsd: number };
export type SimulateResponse = { simulation: SimulationResult; deltas: DecisionDelta[]; selections: Record<string, ScenarioSelection> };
export type BoardroomRequest = { schemaVersion: typeof SCHEMA_VERSION; simulationId: string; dataVersion: string; scenarioId: string };
export type BoardroomResponse = { scenarioId: string; agentOutputs: AgentOutput[]; criticIssues: CriticIssue[]; brief: DecisionBriefRef; numericGuardrail: { passed: boolean; rejectedClaims: string[] } };
