import type { ApiSuccess, BoardroomResponse, EvidenceRecord } from "./contracts";

export type BoardroomIdentity = {
  simulationId: string;
  dataVersion: string;
  scenarioId: string;
  simulationRequestId: string;
};

export type Day4FailureCode =
  | "review_pending"
  | "no_feasible_option"
  | "endpoint_missing"
  | "backend_unavailable"
  | "timeout"
  | "provider_timeout"
  | "provider_unavailable"
  | "critic_unavailable"
  | "numeric_guardrail_rejected"
  | "not_found"
  | "malformed_response"
  | "stale_response"
  | "source_unavailable"
  | "locator_invalid"
  | "unknown";

export type Day4Failure = {
  code: Day4FailureCode;
  message: string;
  requestId?: string;
  retryable: boolean;
};

export type BoardroomProviderMode = "primary" | "same-family-fallback";

export type ValidatedBoardroomRun = {
  identity: BoardroomIdentity;
  response: ApiSuccess<BoardroomResponse>;
  requestId: string;
  providerMode: BoardroomProviderMode;
  criticStatus: "complete";
  receivedAt: string;
};

export type BoardroomState =
  | { status: "idle" }
  | { status: "loading"; identity: BoardroomIdentity; requestId: string }
  | { status: "error"; identity: BoardroomIdentity; failure: Day4Failure }
  | { status: "ready"; run: ValidatedBoardroomRun };

export type LiveEvidenceModal =
  | { state: "loading"; evidenceId: string; identity: BoardroomIdentity }
  | { state: "error"; evidenceId: string; identity: BoardroomIdentity; failure: Day4Failure }
  | { state: "ready"; evidence: EvidenceRecord; identity: BoardroomIdentity; requestId: string; source: "live" | "verified-cache" };

export type SimulationModeLabel =
  | "idle"
  | "running"
  | "live"
  | "simulation-only"
  | "dev-live"
  | "error"
  | "ai-unavailable"
  | "same-family-review"
  | "cached-verified"
  | "saved-example";
