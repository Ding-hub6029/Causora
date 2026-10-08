import type { ApiSuccess, BoardroomResponse, EvidenceRecord, OptionId, SimulateRequest } from "./contracts";
import type { BoardroomIdentity, ValidatedBoardroomRun } from "./day4-types";
import type { LiveSimulation } from "./types";
import { boardroomIdentity, boardroomRequestFor, isCurrentBoardroomRun, validateBoardroomSuccess } from "./boardroom-api";
import { postSimulate } from "./simulate-api";
import { validateEvidenceSuccess } from "./evidence-api";

export const VERIFIED_GOLDEN_STORAGE_KEY = "causora.verified-golden.v1";
const GOLDEN_SCHEMA = "causora.verified-golden.v1" as const;
const SIMULATION_HEADER_KEYS = ["x-causora-review-status", "x-causora-execution-mode", "x-causora-trace-contract"] as const;
const BOARDROOM_HEADER_KEYS = ["x-causora-provider-mode", "x-causora-critic-status"] as const;

export type BrowserHumanDecision = {
  decision: "Approved" | "Rejected";
  recordedAt: string;
  scope: "browser-local-only";
  identity: BoardroomIdentity;
  optionId: OptionId;
};

type CachePayload = {
  schema: typeof GOLDEN_SCHEMA;
  createdAt: string;
  simulationRequest: SimulateRequest;
  simulationResponse: unknown;
  simulationHeaders: Record<string, string>;
  scenarioId: string;
  boardroomRequestId: string;
  boardroomResponse: ApiSuccess<BoardroomResponse>;
  boardroomHeaders: Record<string, string>;
  evidenceRecords: Array<{ requestId: string; evidence: EvidenceRecord }>;
  humanDecision: BrowserHumanDecision;
};

type StoredRecord = CachePayload & { sha256: string };

export type VerifiedGoldenRun = {
  createdAt: string;
  liveRun: LiveSimulation;
  boardroomRun: ValidatedBoardroomRun;
  evidenceRecords: Array<{ requestId: string; evidence: EvidenceRecord }>;
  humanDecision: BrowserHumanDecision;
  sha256: string;
};

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

function canonical(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  const entries = Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b));
  return `{${entries.map(([key, child]) => `${JSON.stringify(key)}:${canonical(child)}`).join(",")}}`;
}

async function sha256(value: unknown): Promise<string> {
  if (!globalThis.crypto?.subtle) throw new Error("Web Crypto is unavailable; the Golden cache was not written.");
  const bytes = new TextEncoder().encode(canonical(value));
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function safeHeaders(source: Headers, allowlist: readonly string[]): Record<string, string> {
  const result: Record<string, string> = {};
  for (const key of allowlist) {
    const value = source.get(key);
    if (value !== null) result[key] = value;
  }
  return result;
}

function rawReviewedV2Response(liveRun: LiveSimulation): unknown {
  if (liveRun.integrationMode !== "reviewed-v2" || !liveRun.development || liveRun.development.executionContext.decisionReady !== true) throw new Error("Only a reviewed, decision-ready v2 run can be considered for Golden caching.");
  return {
    schemaVersion: "causora.contract.v2",
    dataVersion: liveRun.response.dataVersion,
    requestId: liveRun.response.requestId,
    data: { ...liveRun.response.data, ...liveRun.development }
  };
}

function assertHumanDecision(decision: BrowserHumanDecision, identity: BoardroomIdentity, recommendedOption: OptionId): void {
  if ((decision.decision !== "Approved" && decision.decision !== "Rejected") || decision.scope !== "browser-local-only" || decision.optionId !== recommendedOption) throw new Error("A same-run browser-local human decision is required before caching.");
  if (decision.identity.simulationId !== identity.simulationId || decision.identity.dataVersion !== identity.dataVersion || decision.identity.scenarioId !== identity.scenarioId || decision.identity.simulationRequestId !== identity.simulationRequestId) throw new Error("The human decision is bound to a different simulation, dataVersion, scenario, or request.");
  if (!Number.isFinite(Date.parse(decision.recordedAt))) throw new Error("The human decision timestamp is invalid.");
}

function assertGoldenEvidenceMatched(evidence: EvidenceRecord): void {
  if (evidence.quoteMatched !== true) throw new Error(`Evidence ${evidence.id} quote was not matched and cannot satisfy Verified Golden verification.`);
}

function cachePayload(liveRun: LiveSimulation, boardroomRun: ValidatedBoardroomRun, simulationHeaders: Headers, evidenceRecords: Array<{ requestId: string; evidence: EvidenceRecord }>, decision: BrowserHumanDecision): CachePayload {
  if (!isCurrentBoardroomRun(boardroomRun, liveRun, boardroomRun.identity.scenarioId)) throw new Error("The Boardroom result is not for the current simulation.");
  if (liveRun.integrationMode !== "reviewed-v2" || liveRun.development?.executionContext.decisionReady !== true) throw new Error("Unreviewed or non-v2 runs cannot be cached as verified Golden runs.");
  if (boardroomRun.response.data.numericGuardrail.passed !== true || boardroomRun.response.data.numericGuardrail.rejectedClaims.length !== 0 || boardroomRun.criticStatus !== "complete") throw new Error("A complete passing Critic and Numeric Guardrail result is required.");
  const selection = liveRun.response.data.selections[boardroomRun.identity.scenarioId];
  if (!selection || selection.status !== "selected" || selection.recommendedOptionId === null) throw new Error("No feasible option exists for a verified Golden run.");
  assertHumanDecision(decision, boardroomRun.identity, selection.recommendedOptionId);
  const expectedEvidenceIds = [...new Set(boardroomRun.response.data.criticIssues.flatMap((issue) => issue.evidenceIds))].sort();
  if (!expectedEvidenceIds.length) throw new Error("A verified Golden run requires at least one Boardroom Evidence citation.");
  if (evidenceRecords.length !== expectedEvidenceIds.length || new Set(evidenceRecords.map((item) => item.evidence.id)).size !== evidenceRecords.length || [...evidenceRecords.map((item) => item.evidence.id)].sort().join("|") !== expectedEvidenceIds.join("|")) throw new Error("Every unique Evidence ID cited by the Boardroom must be loaded and validated before caching.");
  for (const item of evidenceRecords) {
    const validated = validateEvidenceSuccess({ schemaVersion: "causora.contract.v1", dataVersion: boardroomRun.identity.dataVersion, requestId: item.requestId, data: { evidence: item.evidence } }, item.evidence.id, boardroomRun.identity.dataVersion);
    assertGoldenEvidenceMatched(validated.data.evidence);
  }
  const simulationResponse = rawReviewedV2Response(liveRun);
  const boardroomHeaders = new Headers();
  boardroomHeaders.set("x-causora-provider-mode", boardroomRun.providerMode);
  boardroomHeaders.set("x-causora-critic-status", boardroomRun.criticStatus);
  const payload: CachePayload = {
    schema: GOLDEN_SCHEMA,
    createdAt: new Date().toISOString(),
    simulationRequest: liveRun.request,
    simulationResponse,
    simulationHeaders: safeHeaders(simulationHeaders, SIMULATION_HEADER_KEYS),
    scenarioId: boardroomRun.identity.scenarioId,
    boardroomRequestId: boardroomRun.requestId,
    boardroomResponse: boardroomRun.response,
    boardroomHeaders: safeHeaders(boardroomHeaders, BOARDROOM_HEADER_KEYS),
    evidenceRecords,
    humanDecision: decision
  };
  if (JSON.stringify(payload).includes("TEST_FIXTURE_ONLY")) throw new Error("TEST_FIXTURE_ONLY data cannot be cached as a Golden run.");
  return payload;
}

export async function saveVerifiedGoldenRun(
  liveRun: LiveSimulation,
  boardroomRun: ValidatedBoardroomRun,
  simulationHeaders: Headers,
  evidenceRecords: Array<{ requestId: string; evidence: EvidenceRecord }>,
  decision: BrowserHumanDecision,
  storage: StorageLike = window.localStorage
): Promise<string> {
  const payload = cachePayload(liveRun, boardroomRun, simulationHeaders, evidenceRecords, decision);
  const digest = await sha256(payload);
  const stored: StoredRecord = { ...payload, sha256: digest };
  storage.setItem(VERIFIED_GOLDEN_STORAGE_KEY, JSON.stringify(stored));
  return digest;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function parseStored(value: unknown): StoredRecord {
  if (!isRecord(value) || value.schema !== GOLDEN_SCHEMA || typeof value.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(value.sha256)) throw new Error("Golden cache has an unsupported or malformed envelope.");
  const { sha256: digest, ...payload } = value;
  if (!isRecord(payload) || typeof payload.createdAt !== "string" || !isRecord(payload.simulationHeaders) || !isRecord(payload.boardroomHeaders) || !isRecord(payload.simulationRequest) || !isRecord(payload.boardroomResponse) || !Array.isArray(payload.evidenceRecords) || !isRecord(payload.humanDecision)) throw new Error("Golden cache is missing required fields.");
  return { ...(payload as unknown as CachePayload), sha256: digest };
}

export async function loadVerifiedGoldenRun(storage: StorageLike = window.localStorage): Promise<VerifiedGoldenRun | null> {
  const raw = storage.getItem(VERIFIED_GOLDEN_STORAGE_KEY);
  if (!raw) return null;
  let stored: StoredRecord;
  try { stored = parseStored(JSON.parse(raw) as unknown); }
  catch (error) { throw new Error(`Golden cache rejected: ${error instanceof Error ? error.message : "invalid JSON"}`); }
  const { sha256: digest, ...payload } = stored;
  if (await sha256(payload) !== digest) throw new Error("Golden cache SHA-256 integrity check failed.");
  if (JSON.stringify(payload).includes("TEST_FIXTURE_ONLY")) throw new Error("TEST_FIXTURE_ONLY data cannot be opened as a Golden run.");

  const responseHeaders = new Headers(payload.simulationHeaders);
  const simulated = await postSimulate(payload.simulationRequest, async () => new Response(JSON.stringify(payload.simulationResponse), { status: 200, headers: responseHeaders }));
  if (simulated.integrationMode !== "reviewed-v2" || simulated.development?.executionContext.decisionReady !== true) throw new Error("Cached simulation is not a reviewed, decision-ready v2 run.");
  const liveRun: LiveSimulation = { request: payload.simulationRequest, response: simulated.response, integrationMode: simulated.integrationMode, development: simulated.development, receivedAt: payload.createdAt };
  const boardroomRequest = boardroomRequestFor(liveRun, payload.scenarioId);
  const boardroomHeaders = new Headers(payload.boardroomHeaders);
  const boardroomRun = validateBoardroomSuccess(payload.boardroomResponse, boardroomRequest, liveRun, boardroomHeaders, payload.boardroomRequestId);
  const identity = boardroomIdentity(liveRun, payload.scenarioId);
  const expectedEvidenceIds = [...new Set(boardroomRun.response.data.criticIssues.flatMap((issue) => issue.evidenceIds))].sort();
  if (!expectedEvidenceIds.length || payload.evidenceRecords.length !== expectedEvidenceIds.length) throw new Error("Golden cache does not contain the complete cited Evidence set.");
  const evidenceRecords = payload.evidenceRecords.map((item, index) => {
    if (!isRecord(item) || typeof item.requestId !== "string" || !isRecord(item.evidence) || typeof item.evidence.id !== "string") throw new Error(`Golden Evidence record ${index} is malformed.`);
    const validated = validateEvidenceSuccess({ schemaVersion: "causora.contract.v1", dataVersion: identity.dataVersion, requestId: item.requestId, data: { evidence: item.evidence } }, item.evidence.id, identity.dataVersion);
    assertGoldenEvidenceMatched(validated.data.evidence);
    return { requestId: validated.requestId, evidence: validated.data.evidence };
  });
  if (new Set(evidenceRecords.map((item) => item.evidence.id)).size !== expectedEvidenceIds.length || [...evidenceRecords.map((item) => item.evidence.id)].sort().join("|") !== expectedEvidenceIds.join("|")) throw new Error("Golden Evidence IDs do not exactly match the current Boardroom citations.");
  assertHumanDecision(payload.humanDecision, identity, liveRun.response.data.selections[payload.scenarioId]?.recommendedOptionId ?? "D0");
  if (!isCurrentBoardroomRun(boardroomRun, liveRun, payload.scenarioId)) throw new Error("Cached Boardroom identity does not match the cached simulation.");
  return { createdAt: payload.createdAt, liveRun, boardroomRun, evidenceRecords, humanDecision: payload.humanDecision, sha256: digest };
}

export function clearVerifiedGoldenRun(storage: StorageLike = window.localStorage): void {
  storage.removeItem(VERIFIED_GOLDEN_STORAGE_KEY);
}
