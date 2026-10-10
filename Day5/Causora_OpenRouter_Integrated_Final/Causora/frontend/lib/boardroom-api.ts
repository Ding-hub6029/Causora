import type { ApiFailure, ApiSuccess, BoardroomRequest, BoardroomResponse, OptionId, SimulateResponse } from "./contracts";
import type { LiveSimulation } from "./types";
import type { BoardroomIdentity, BoardroomProviderMode, Day4FailureCode, ValidatedBoardroomRun } from "./day4-types";
import { boardroomTemplateError } from "./boardroom-template";

const SCHEMA_VERSION = "causora.contract.v1" as const;
const ALLOWED_METRIC_REFS = new Set(["delta_tco", "stockout_probability", "cash_outflow_p90"]);
const OPTION_IDS: OptionId[] = ["D0", "D1", "D2"];
const ROLES = ["CFO", "COO", "Risk"] as const;
const REQUEST_TIMEOUT_MS = 45_000;

export class Day4ApiError extends Error {
  readonly code: Day4FailureCode;
  readonly requestId?: string;
  readonly retryable: boolean;

  constructor(code: Day4FailureCode, message: string, options: { requestId?: string; retryable?: boolean } = {}) {
    super(message);
    this.name = "Day4ApiError";
    this.code = code;
    this.requestId = options.requestId;
    this.retryable = options.retryable ?? false;
  }
}

type Obj = Record<string, unknown>;

function object(value: unknown, path: string): Obj {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Day4ApiError("malformed_response", `${path}: expected an object.`);
  return value as Obj;
}
function nonEmpty(value: unknown, path: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Day4ApiError("malformed_response", `${path}: expected non-empty text.`);
  return value;
}
function integer(value: unknown, path: string, minimum = 0): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < minimum) throw new Day4ApiError("malformed_response", `${path}: expected a whole number.`);
  return value;
}
function metricRef(value: unknown, path: string): string {
  const ref = nonEmpty(value, path);
  if (!ALLOWED_METRIC_REFS.has(ref)) throw new Day4ApiError("malformed_response", `${path}: unsupported metric reference "${ref}".`);
  return ref;
}

export function boardroomIdentity(liveRun: LiveSimulation, scenarioId: string): BoardroomIdentity {
  return {
    simulationId: liveRun.response.data.simulation.simulationId,
    dataVersion: liveRun.response.data.simulation.dataVersion,
    scenarioId,
    simulationRequestId: liveRun.response.requestId
  };
}

export function validateBoardroomSuccess(
  input: unknown,
  request: BoardroomRequest,
  liveRun: LiveSimulation,
  responseHeaders: Pick<Headers, "get">,
  outboundRequestId: string
): ValidatedBoardroomRun {
  if (liveRun.integrationMode !== "reviewed-v2" || liveRun.development?.executionContext.decisionReady !== true) {
    throw new Day4ApiError("review_pending", "A formal Boardroom review requires a reviewed, decision-ready v2 simulation.");
  }
  const simulation = liveRun.response.data.simulation;
  const identity = boardroomIdentity(liveRun, request.scenarioId);
  if (request.schemaVersion !== SCHEMA_VERSION || request.simulationId !== identity.simulationId || request.dataVersion !== identity.dataVersion || request.scenarioId !== identity.scenarioId) {
    throw new Day4ApiError("stale_response", "The Boardroom request does not match the current simulation identity.");
  }
  const envelope = object(input, "response");
  if (envelope.schemaVersion !== SCHEMA_VERSION) throw new Day4ApiError("malformed_response", "Boardroom response must use causora.contract.v1.");
  if (envelope.dataVersion !== identity.dataVersion) throw new Day4ApiError("stale_response", "Boardroom response dataVersion differs from the current simulation.");
  const responseRequestId = nonEmpty(envelope.requestId, "response.requestId");
  if (responseRequestId !== outboundRequestId) throw new Day4ApiError("stale_response", "Boardroom response requestId does not match this request.", { requestId: responseRequestId });

  const providerHeader = responseHeaders.get("x-causora-provider-mode");
  if (providerHeader !== "primary" && providerHeader !== "same-family-fallback") {
    throw new Day4ApiError("malformed_response", "Boardroom response must declare X-Causora-Provider-Mode as primary or same-family-fallback.", { requestId: responseRequestId });
  }
  const criticHeader = responseHeaders.get("x-causora-critic-status");
  if (criticHeader === "unavailable") throw new Day4ApiError("critic_unavailable", "The simulation is intact, but the Critic service is unavailable.", { requestId: responseRequestId, retryable: true });
  if (criticHeader !== "complete") throw new Day4ApiError("malformed_response", "Boardroom response must explicitly declare X-Causora-Critic-Status: complete.", { requestId: responseRequestId });

  const data = object(envelope.data, "response.data");
  if (data.scenarioId !== identity.scenarioId) throw new Day4ApiError("stale_response", "Boardroom response scenarioId differs from the selected scenario.", { requestId: responseRequestId });
  const selection = liveRun.response.data.selections[identity.scenarioId];
  if (!selection || selection.status !== "selected" || selection.recommendedOptionId === null) {
    throw new Day4ApiError("no_feasible_option", "No allowed option passed the current constraints; a formal brief cannot be created.", { requestId: responseRequestId });
  }

  const outputs = data.agentOutputs;
  if (!Array.isArray(outputs) || outputs.length !== ROLES.length) throw new Day4ApiError("malformed_response", "Boardroom must contain exactly the CFO, COO, and Risk outputs.", { requestId: responseRequestId });
  for (const [index, raw] of outputs.entries()) {
    const output = object(raw, `agentOutputs[${index}]`);
    if (output.role !== ROLES[index]) throw new Day4ApiError("malformed_response", "Boardroom role outputs are incomplete or out of order.", { requestId: responseRequestId });
    const body = nonEmpty(output.body, `agentOutputs[${index}].body`);
    for (const key of ["accent", "focus", "headline"] as const) nonEmpty(output[key], `agentOutputs[${index}].${key}`);
    if (!Array.isArray(output.metrics) || output.metrics.length < 1 || output.metrics.length > 8) throw new Day4ApiError("malformed_response", `agentOutputs[${index}].metrics is invalid.`, { requestId: responseRequestId });
    output.metrics.forEach((ref, metricIndex) => metricRef(ref, `agentOutputs[${index}].metrics[${metricIndex}]`));
    const templateError = boardroomTemplateError(body, output.metrics as string[]);
    if (templateError) throw new Day4ApiError("malformed_response", `agentOutputs[${index}].body ${templateError}`, { requestId: responseRequestId });
    if (output.status !== "Aligned" && output.status !== "Watch") throw new Day4ApiError("malformed_response", `agentOutputs[${index}].status is invalid.`, { requestId: responseRequestId });
  }

  const criticIssues = data.criticIssues;
  if (!Array.isArray(criticIssues)) throw new Day4ApiError("malformed_response", "Boardroom criticIssues must be an array.", { requestId: responseRequestId });
  for (const [index, raw] of criticIssues.entries()) {
    const issue = object(raw, `criticIssues[${index}]`);
    nonEmpty(issue.severity, `criticIssues[${index}].severity`);
    nonEmpty(issue.headline, `criticIssues[${index}].headline`);
    nonEmpty(issue.body, `criticIssues[${index}].body`);
    if (!Array.isArray(issue.evidenceIds) || issue.evidenceIds.some((id) => typeof id !== "string" || !/^EV-\d{3}$/.test(id))) throw new Day4ApiError("malformed_response", `criticIssues[${index}].evidenceIds is invalid.`, { requestId: responseRequestId });
    const mechanism = object(issue.mechanism, `criticIssues[${index}].mechanism`);
    if (mechanism.scenarioId !== identity.scenarioId) throw new Day4ApiError("stale_response", `criticIssues[${index}] is not linked to the selected scenario.`, { requestId: responseRequestId });
    if (mechanism.forecastBasis !== "locked-at-renewal" && mechanism.forecastBasis !== "rolling") throw new Day4ApiError("malformed_response", `criticIssues[${index}].mechanism.forecastBasis is invalid.`, { requestId: responseRequestId });
    for (const key of ["lockedForecastUnits24m", "minPurchaseUnitsA", "scenarioDemandUnits24m", "committedExcessUnits"] as const) integer(mechanism[key], `criticIssues[${index}].mechanism.${key}`);
    const requestedScenario = liveRun.request.scenarios.find((scenario) => scenario.id === identity.scenarioId);
    if (!requestedScenario || mechanism.scenarioDemandUnits24m !== requestedScenario.demandUnits24m) throw new Day4ApiError("stale_response", `criticIssues[${index}] uses demand from a different scenario.`, { requestId: responseRequestId });
    const holdingDeltas = object(mechanism.holdingCostDeltaUsd, `criticIssues[${index}].mechanism.holdingCostDeltaUsd`);
    const rows = simulation.matrix[identity.scenarioId];
    const baseline = rows?.find((row) => row.optionId === "D0");
    if (!baseline) throw new Day4ApiError("malformed_response", "The matching simulation matrix is missing D0.", { requestId: responseRequestId });
    for (const optionId of OPTION_IDS) {
      const row = rows?.find((candidate) => candidate.optionId === optionId);
      if (!row || holdingDeltas[optionId] !== row.breakdown.holding - baseline.breakdown.holding) throw new Day4ApiError("stale_response", `criticIssues[${index}] holding delta does not match the current simulation.`, { requestId: responseRequestId });
    }
  }

  const brief = object(data.brief, "response.data.brief");
  if (brief.scenarioId !== identity.scenarioId || brief.status !== "selected" || brief.recommendedOptionId !== selection.recommendedOptionId) {
    throw new Day4ApiError("stale_response", "The brief recommendation does not match this scenario's validated server selection.", { requestId: responseRequestId });
  }
  nonEmpty(brief.recommendation, "brief.recommendation");
  nonEmpty(brief.rationale, "brief.rationale");
  if (!Array.isArray(brief.metricRefs) || brief.metricRefs.length < 1) throw new Day4ApiError("malformed_response", "The brief must declare metric references.", { requestId: responseRequestId });
  brief.metricRefs.forEach((ref, index) => metricRef(ref, `brief.metricRefs[${index}]`));
  const formulaVersion = simulation.formulaVersion;
  if (brief.formulaVersion !== formulaVersion) throw new Day4ApiError("stale_response", "The brief formula version differs from the current simulation.", { requestId: responseRequestId });
  nonEmpty(brief.formula, "brief.formula");
  nonEmpty(brief.guardrail, "brief.guardrail");
  const guardrail = object(data.numericGuardrail, "response.data.numericGuardrail");
  if (guardrail.passed !== true || !Array.isArray(guardrail.rejectedClaims) || guardrail.rejectedClaims.length !== 0) {
    throw new Day4ApiError("numeric_guardrail_rejected", "Numeric Guardrail did not approve every Boardroom claim; the formal Brief is blocked.", { requestId: responseRequestId });
  }

  return {
    identity,
    response: input as ApiSuccess<BoardroomResponse>,
    requestId: responseRequestId,
    providerMode: providerHeader as BoardroomProviderMode,
    criticStatus: "complete",
    receivedAt: new Date().toISOString()
  };
}

export function getBoardroomEndpoint(): string {
  const base = process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL?.trim().replace(/\/+$/, "") ?? "";
  return `${base}/api/boardroom`;
}

export function createBoardroomRequestId(): string {
  const random = globalThis.crypto?.randomUUID?.();
  return `causora-br-${random ?? `${Date.now()}-${Math.random().toString(36).slice(2, 12)}`}`;
}

function parseFailure(value: unknown, status: number, responseRequestId?: string): Day4ApiError {
  const envelope = value && typeof value === "object" && !Array.isArray(value) ? value as Partial<ApiFailure> : undefined;
  const raw = envelope?.error;
  const requestId = typeof raw?.requestId === "string" ? raw.requestId : responseRequestId;
  const message = typeof raw?.message === "string" && raw.message.trim() ? raw.message : `Boardroom request failed with HTTP ${status}.`;
  const apiCode = raw?.code;
  if (status === 404 || apiCode === "not_found") return new Day4ApiError("endpoint_missing", "POST /api/boardroom is not available on this backend yet. The validated simulation remains available.", { requestId, retryable: false });
  if (status === 503) return new Day4ApiError("backend_unavailable", message, { requestId, retryable: true });
  if (status === 408 || status === 504 || apiCode === "provider_timeout") return new Day4ApiError("provider_timeout", message, { requestId, retryable: true });
  if (status >= 500) return new Day4ApiError("provider_unavailable", message, { requestId, retryable: true });
  if (status === 422) return new Day4ApiError("malformed_response", message, { requestId, retryable: false });
  return new Day4ApiError("unknown", message, { requestId, retryable: status >= 500 });
}

export async function postBoardroom(
  liveRun: LiveSimulation,
  scenarioId: string,
  fetchImpl: typeof fetch = fetch,
  externalSignal?: AbortSignal,
  requestIdOverride?: string
): Promise<ValidatedBoardroomRun> {
  if (liveRun.integrationMode !== "reviewed-v2" || liveRun.development?.executionContext.decisionReady !== true) {
    throw new Day4ApiError("review_pending", "AI review is locked because this simulation is not a reviewed, decision-ready v2 run.");
  }
  const selection = liveRun.response.data.selections[scenarioId];
  if (!selection || selection.status !== "selected" || selection.recommendedOptionId === null) {
    throw new Day4ApiError("no_feasible_option", "No feasible option exists for this scenario; no Boardroom recommendation can be requested.");
  }
  const request: BoardroomRequest = { schemaVersion: SCHEMA_VERSION, simulationId: liveRun.response.data.simulation.simulationId, dataVersion: liveRun.response.data.simulation.dataVersion, scenarioId };
  const requestId = requestIdOverride ?? createBoardroomRequestId();
  if (externalSignal?.aborted) {
    throw new Day4ApiError("stale_response", "Boardroom request was cancelled because the run changed.", { requestId, retryable: false });
  }
  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => controller.abort(new DOMException("Boardroom request timed out.", "TimeoutError")), REQUEST_TIMEOUT_MS);
  const forwardAbort = () => controller.abort(externalSignal?.reason);
  externalSignal?.addEventListener("abort", forwardAbort, { once: true });
  try {
    const response = await fetchImpl(getBoardroomEndpoint(), {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Request-Id": requestId },
      body: JSON.stringify(request),
      cache: "no-store",
      credentials: "omit",
      signal: controller.signal
    });
    const responseRequestId = response.headers.get("x-request-id") ?? undefined;
    if (response.ok && responseRequestId !== requestId) {
      throw new Day4ApiError("stale_response", "Boardroom response request-id header does not match this request.", { requestId: responseRequestId, retryable: false });
    }
    let payload: unknown;
    try { payload = await response.json(); }
    catch { throw new Day4ApiError("malformed_response", "Boardroom returned unreadable JSON; the simulation remains available.", { requestId: responseRequestId, retryable: false }); }
    if (!response.ok) throw parseFailure(payload, response.status, responseRequestId);
    return validateBoardroomSuccess(payload, request, liveRun, response.headers, requestId);
  } catch (error) {
    if (error instanceof Day4ApiError) throw error;
    if (controller.signal.aborted) {
      const timedOut = controller.signal.reason instanceof DOMException && controller.signal.reason.name === "TimeoutError";
      throw new Day4ApiError(timedOut ? "timeout" : "stale_response", timedOut ? "Boardroom request timed out. The validated simulation is unchanged." : "Boardroom request was cancelled because the run changed.", { requestId, retryable: timedOut });
    }
    throw new Day4ApiError("backend_unavailable", "Boardroom service could not be reached. The validated simulation is unchanged.", { requestId, retryable: true });
  } finally {
    globalThis.clearTimeout(timeout);
    externalSignal?.removeEventListener("abort", forwardAbort);
  }
}

export function isCurrentBoardroomRun(run: ValidatedBoardroomRun, liveRun: LiveSimulation | null, scenarioId: string): boolean {
  return !!liveRun
    && liveRun.integrationMode === "reviewed-v2"
    && run.identity.simulationId === liveRun.response.data.simulation.simulationId
    && run.identity.dataVersion === liveRun.response.data.simulation.dataVersion
    && run.identity.scenarioId === scenarioId
    && run.identity.simulationRequestId === liveRun.response.requestId;
}

export function selectedOptionFor(response: ApiSuccess<SimulateResponse>, scenarioId: string): OptionId | null {
  const selection = response.data.selections[scenarioId];
  return selection?.status === "selected" ? selection.recommendedOptionId : null;
}

export function boardroomRequestFor(liveRun: LiveSimulation, scenarioId: string): BoardroomRequest {
  const identity = boardroomIdentity(liveRun, scenarioId);
  return { schemaVersion: SCHEMA_VERSION, simulationId: identity.simulationId, dataVersion: identity.dataVersion, scenarioId: identity.scenarioId };
}

export function briefIdentityMatches(request: BoardroomRequest, identity: BoardroomIdentity): boolean {
  return request.schemaVersion === SCHEMA_VERSION && request.simulationId === identity.simulationId && request.dataVersion === identity.dataVersion && request.scenarioId === identity.scenarioId;
}
