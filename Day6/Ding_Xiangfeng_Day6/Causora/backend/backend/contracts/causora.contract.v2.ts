/** Final candidate TypeScript types for the release-gated v2 success only.
 * Keep SimulateRequest and all pending/error envelopes on causora.contract.v1.
 */
import type { DecisionDelta, OptionId, ScenarioSelection, SimulationResult } from "./contracts-v1";
import type { WeekTrace } from "./week-trace";

export const SIMULATE_SUCCESS_SCHEMA_V2 = "causora.contract.v2" as const;
export const FORMULA_TRACE_SCHEMA_V1 = "causora.formula-trace.v1" as const;
export const REVIEWED_EXECUTION_MODE = "reviewed_release_gated" as const;
export const UNREVIEWED_DEVELOPMENT_MODE = "unreviewed_development_only" as const;
export type ExecutionMode = typeof REVIEWED_EXECUTION_MODE | typeof UNREVIEWED_DEVELOPMENT_MODE;

export type TraceProvenance = {
  kind: "reviewed_contract" | "unreviewed_development_contract" | "approved_operating_assumption" | "unreviewed_development_assumption" | "observed_synthetic_dataset" | "derived_formula";
  status: "reviewed" | "unreviewed_development_only" | "approved" | "observed" | "derived";
  sourceId: string;
  sourceFile: string | null;
  /** Hash of the referenced source artifact, never a review-record hash. */
  sourceSha256: string | null;
  evidenceIds: string[];
  reviewRecordId: string | null;
  reviewRecordSha256: string | null;
  note: string;
};
export type TraceParameter = { key: string; value: string | number | boolean; unit: string; provenance: TraceProvenance };
export type RoundingAudit = { rawMeanUsd: string; displayedValueUsd: number; displayedMinusRawMeanUsd: string; method: string };
export type FormulaComponent = {
  key: "purchase" | "holding" | "stockoutLoss" | "renewalPremium" | "terminationFee";
  formula: string; inputKeys: string[]; valueUsd: number; roundingAudit: RoundingAudit;
};
export type TraceRunIdentity = {
  executionMode: ExecutionMode;
  reviewRecordId: string | null; reviewRecordSha256: string | null; contractPayloadSha256: string;
  policyApprovalReference: string; policyConfigurationId: string; policySha256: string;
  contractApprovalReference: string; contractReleaseRecordSha256: string;
};
export type ExecutionContext = {
  mode: ExecutionMode;
  banner: string;
  humanReviewStatus: "reviewed" | "not_reviewed_development_only";
  policyStatus: "approved" | "unapproved_development_only";
  contractReleaseStatus: "released" | "not_released_development_only";
  /** Must be false in unreviewed development mode; do not render as a decision. */
  decisionReady: boolean;
};
export type FormulaTrace = {
  traceSchemaVersion: typeof FORMULA_TRACE_SCHEMA_V1;
  simulationId: string; dataVersion: string; formulaVersion: "tco-v1";
  scenarioId: string; optionId: OptionId; runIdentity: TraceRunIdentity;
  parameters: TraceParameter[]; components: FormulaComponent[]; expectedTcoUsd: number;
  stockoutProbability: { value: number; numeratorStockoutRuns: number; denominatorRuns: number; definition: "trials_with_at_least_one_lost_unit / monteCarloRuns" };
  serviceLevel: { value: number; fulfilledUnitsAllRuns: number; demandUnitsAllRuns: number; definition: "fulfilled_units_all_runs / demand_units_all_runs" };
  cashOutflowP90: { valueUsd: number; method: "nearest_rank_ceil_0.90N"; percentile: 0.9; rankOneBased: number; denominatorRuns: number; includedCashComponents: ["purchase", "holding", "renewalPremium", "terminationFee"]; excludedNonCashComponents: ["stockoutLoss"]; perRunRounding: "whole_usd_half_even" };
  summaryRoundingRule: string;
  samplePath: { sampleRunIndex: number; classification: "single_realised_trial_not_aggregate"; note: string; weeks: WeekTrace[] };
};
export type SimulateSuccessV2 = {
  schemaVersion: typeof SIMULATE_SUCCESS_SCHEMA_V2;
  dataVersion: string; requestId: string;
  data: { simulation: SimulationResult; deltas: DecisionDelta[]; selections: Record<string, ScenarioSelection>; traces: Record<string, Record<OptionId, FormulaTrace>>; executionContext: ExecutionContext };
};
