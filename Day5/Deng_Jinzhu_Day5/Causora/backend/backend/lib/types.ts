import type { AgentOutput, ApiSuccess, BusinessVariable, ContractConstraint, CriticIssue, SelectedDecisionBriefRef, DecisionOption, EvidenceRecord, OptionId, Scenario, SimulateRequest, SimulateResponse, SimulationResult } from "./contracts";

export type AppState = "ready" | "loading" | "empty" | "error" | "golden" | "no-feasible";

export type StageId = "intake" | "scenario" | "matrix" | "boardroom" | "brief";

export type Evidence = EvidenceRecord;

export type IntakeFile = { id: string; label: string; type: string; detail: string; size: string; status: string; icon: string; path: string };

/** The complete frontend data contract. The Golden Run stores one frozen copy of this shape. */
export type MockData = {
  meta: { schemaVersion: string; product: string; version: string; dataVersion: string; status: string; seed: number; notice: string };
  intake: IntakeFile[];
  evidence: EvidenceRecord[];
  contract: ContractConstraint;
  variables: BusinessVariable[];
  scenarios: Scenario[];
  options: DecisionOption[];
  simulation: SimulationResult;
  boardroom: AgentOutput[];
  critic: CriticIssue;
  brief: SelectedDecisionBriefRef;
};

export type GoldenRun = {
  label: string;
  verifiedAt: string;
  verifiedAtNote: string;
  dataVersion: string;
  seed: number;
  snapshotHash: string;
  request: { scenario: string; options: OptionId[]; riskThreshold: number };
  response: { recommendedOptionId: OptionId; status: string };
  snapshot: MockData;
  notice: string;
};

export type LiveSimulation = {
  request: SimulateRequest;
  response: ApiSuccess<SimulateResponse>;
  receivedAt: string;
};

export type ModalState =
  | { kind: "closed" }
  | { kind: "evidence"; evidence: Evidence }
  | { kind: "stack" }
  | { kind: "formula"; scenarioId: string; optionId: OptionId };
