import type { DevFormulaTrace, DevSimulationDetails } from "./contracts-v2-dev";
import type { OptionId } from "./contracts";

export type ReviewedExecutionContext = {
  mode: "reviewed_release_gated"; banner: string;
  humanReviewStatus: "reviewed"; policyStatus: "approved";
  contractReleaseStatus: "released"; decisionReady: true;
};
export type ReviewedFormulaTrace = Omit<DevFormulaTrace, "runIdentity"> & {
  runIdentity: Omit<DevFormulaTrace["runIdentity"], "executionMode" | "reviewRecordId" | "reviewRecordSha256"> & {
    executionMode: "reviewed_release_gated"; reviewRecordId: string; reviewRecordSha256: string;
  };
};
export type ReviewedSimulationDetails = {
  executionContext: ReviewedExecutionContext;
  traces: Record<string, Record<OptionId, ReviewedFormulaTrace>>;
};
// `development` is retained as the legacy state property for compatibility;
// executionContext and integrationMode always distinguish the two transports.
export type V2SimulationDetails = DevSimulationDetails | ReviewedSimulationDetails;
export type V2FormulaTrace = DevFormulaTrace | ReviewedFormulaTrace;
