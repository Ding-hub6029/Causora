/**
 * Local adapter-only shapes for the explicitly unreviewed Day 3 v2 dev response.
 * This does not amend the shared v1 contract or authorize reviewed v2 release.
 */
import type { OptionId, SimulateResponse } from "./contracts";

export type DevExecutionContext = {
  mode: "unreviewed_development_only";
  banner: string;
  humanReviewStatus: "not_reviewed_development_only";
  policyStatus: "unapproved_development_only";
  contractReleaseStatus: "not_released_development_only";
  decisionReady: false;
};

export type DevTraceProvenance = {
  kind: "reviewed_contract" | "unreviewed_development_contract" | "approved_operating_assumption" | "unreviewed_development_assumption" | "observed_synthetic_dataset" | "derived_formula";
  status: "reviewed" | "unreviewed_development_only" | "approved" | "observed" | "derived";
  sourceId: string;
  sourceFile: string | null;
  sourceSha256: string | null;
  evidenceIds: string[];
  reviewRecordId: string | null;
  reviewRecordSha256: string | null;
  note: string;
};

export type DevTraceParameter = { key: string; value: string | number | boolean; unit: string; provenance: DevTraceProvenance };
export type DevRoundingAudit = { rawMeanUsd: string; displayedValueUsd: number; displayedMinusRawMeanUsd: string; method: string };
export type DevFormulaComponent = {
  key: "purchase" | "holding" | "stockoutLoss" | "renewalPremium" | "terminationFee";
  formula: string;
  inputKeys: string[];
  valueUsd: number;
  roundingAudit: DevRoundingAudit;
};

export type DevWeekTrace = {
  week: number;
  startDate: string;
  openingUnits: number;
  arrivalsA: number;
  arrivalsB: number;
  demandUnits: number;
  availableUnits: number;
  fulfilledUnits: number;
  lostUnits: number;
  endingUnits: number;
  onOrderUnitsBefore: number;
  inventoryPositionBefore: number;
  reorderPointUnits: number;
  orderedA: number;
  orderedB: number;
  sampledLeadDaysA: number | null;
  sampledLeadDaysB: number | null;
  plannedArrivalWeekA: number | null;
  plannedArrivalWeekB: number | null;
  onOrderUnitsAfter: number;
  holdingRawUsd: string;
  stockoutLossRawUsd: string;
  basePurchaseRawUsd: string;
  renewalPremiumRawUsd: string;
  terminationFeeRawUsd: string;
};

export type DevFormulaTrace = {
  traceSchemaVersion: "causora.formula-trace.v1";
  simulationId: string;
  dataVersion: string;
  formulaVersion: "tco-v1";
  scenarioId: string;
  optionId: OptionId;
  runIdentity: {
    executionMode: "unreviewed_development_only";
    reviewRecordId: null;
    reviewRecordSha256: null;
    contractPayloadSha256: string;
    policyApprovalReference: string;
    policyConfigurationId: string;
    policySha256: string;
    contractApprovalReference: string;
    contractReleaseRecordSha256: string;
  };
  parameters: DevTraceParameter[];
  components: DevFormulaComponent[];
  expectedTcoUsd: number;
  stockoutProbability: { value: number; numeratorStockoutRuns: number; denominatorRuns: number; definition: "trials_with_at_least_one_lost_unit / monteCarloRuns" };
  serviceLevel: { value: number; fulfilledUnitsAllRuns: number; demandUnitsAllRuns: number; definition: "fulfilled_units_all_runs / demand_units_all_runs" };
  cashOutflowP90: { valueUsd: number; method: "nearest_rank_ceil_0.90N"; percentile: 0.9; rankOneBased: number; denominatorRuns: number; includedCashComponents: string[]; excludedNonCashComponents: string[]; perRunRounding: "whole_usd_half_even" };
  summaryRoundingRule: string;
  samplePath: { sampleRunIndex: number; classification: "single_realised_trial_not_aggregate"; note: string; weeks: DevWeekTrace[] };
};

export type DevV2Payload = {
  schemaVersion: "causora.contract.v2";
  dataVersion: string;
  requestId: string;
  data: SimulateResponse & {
    traces: Record<string, Record<OptionId, DevFormulaTrace>>;
    executionContext: DevExecutionContext;
  };
};

export type LiveIntegrationMode = "v1" | "unreviewed-v2-dev" | "reviewed-v2";
export type DevSimulationDetails = Pick<DevV2Payload["data"], "traces" | "executionContext">;
