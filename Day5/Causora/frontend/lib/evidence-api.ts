import type { ApiFailure, ApiSuccess, EvidenceRecord } from "./contracts";
import type { Day4FailureCode } from "./day4-types";
import { Day4ApiError } from "./boardroom-api";

const SCHEMA_VERSION = "causora.contract.v1" as const;
const REQUEST_TIMEOUT_MS = 15_000;
const LOCAL_PDF_ALLOWLIST = new Set(["supplier_a_agreement.pdf"]);

type Obj = Record<string, unknown>;

function object(value: unknown, path: string): Obj {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Day4ApiError("malformed_response", `${path}: expected an object.`);
  return value as Obj;
}
function text(value: unknown, path: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Day4ApiError("malformed_response", `${path}: expected non-empty text.`);
  return value;
}
function safeLocalFilename(value: string): boolean {
  return value === value.trim() && !value.includes("..") && !/[\\/\0]/.test(value) && LOCAL_PDF_ALLOWLIST.has(value);
}

export function validateEvidenceSuccess(input: unknown, evidenceId: string, dataVersion: string): ApiSuccess<{ evidence: EvidenceRecord }> {
  const envelope = object(input, "response");
  if (envelope.schemaVersion !== SCHEMA_VERSION) throw new Day4ApiError("malformed_response", "Evidence response must use causora.contract.v1.");
  if (envelope.dataVersion !== dataVersion) throw new Day4ApiError("stale_response", "Evidence response dataVersion differs from the active run.");
  text(envelope.requestId, "response.requestId");
  const data = object(envelope.data, "response.data");
  const evidence = object(data.evidence, "response.data.evidence");
  if (evidence.id !== evidenceId || typeof evidence.id !== "string" || !/^EV-\d{3}$/.test(evidence.id)) throw new Day4ApiError("stale_response", "Evidence response id does not match the requested citation.");
  const sourceFile = text(evidence.sourceFile, "evidence.sourceFile");
  if (!safeLocalFilename(sourceFile)) throw new Day4ApiError("source_unavailable", "The requested source file is not in the approved local evidence bundle.");
  const page = evidence.page;
  if (typeof page !== "number" || !Number.isSafeInteger(page) || page < 1) throw new Day4ApiError("locator_invalid", "Evidence page locator is invalid.");
  const quote = text(evidence.quote, "evidence.quote");
  const extractedField = text(evidence.extractedField, "evidence.extractedField");
  const extractedValue = text(evidence.extractedValue, "evidence.extractedValue");
  if (evidence.matchMethod !== "exact" && evidence.matchMethod !== "fuzzy") throw new Day4ApiError("malformed_response", "Evidence matchMethod is invalid.");
  if (typeof evidence.matchScore !== "number" || !Number.isFinite(evidence.matchScore) || evidence.matchScore < 0 || evidence.matchScore > 1) throw new Day4ApiError("malformed_response", "Evidence matchScore must be a fraction from 0 to 1.");
  if (typeof evidence.quoteMatched !== "boolean") throw new Day4ApiError("malformed_response", "Evidence quoteMatched must be a boolean.");
  let locatorBbox: EvidenceRecord["locatorBbox"] = null;
  if (evidence.locatorBbox !== null) {
    if (!Array.isArray(evidence.locatorBbox) || evidence.locatorBbox.length !== 4 || evidence.locatorBbox.some((part) => typeof part !== "number" || !Number.isFinite(part))) throw new Day4ApiError("locator_invalid", "Evidence bounding box must contain four finite PDF-point coordinates.");
    const [x0, y0, x1, y1] = evidence.locatorBbox as number[];
    if (x0 < 0 || y0 < 0 || x1 <= x0 || y1 <= y0) throw new Day4ApiError("locator_invalid", "Evidence bounding box coordinates are invalid.");
    locatorBbox = [x0, y0, x1, y1];
  }
  return {
    schemaVersion: SCHEMA_VERSION,
    dataVersion,
    requestId: envelope.requestId as string,
    data: { evidence: { id: evidenceId, sourceFile, page, quote, locatorBbox, extractedField, extractedValue, matchMethod: evidence.matchMethod, matchScore: evidence.matchScore, quoteMatched: evidence.quoteMatched } }
  };
}

export function evidenceSourceHref(evidence: Pick<EvidenceRecord, "sourceFile" | "page">): string | null {
  if (!safeLocalFilename(evidence.sourceFile) || !Number.isSafeInteger(evidence.page) || evidence.page < 1) return null;
  return `/demo/${encodeURIComponent(evidence.sourceFile)}#page=${evidence.page}&zoom=page-width`;
}

export function getEvidenceEndpoint(evidenceId: string): string {
  const base = process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL?.trim().replace(/\/+$/, "") ?? "";
  return `${base}/api/evidence/${encodeURIComponent(evidenceId)}`;
}

function requestId(): string {
  const random = globalThis.crypto?.randomUUID?.();
  return `causora-ev-${random ?? `${Date.now()}-${Math.random().toString(36).slice(2, 12)}`}`;
}

function failureCode(status: number, payload: unknown): Day4FailureCode {
  const envelope = payload && typeof payload === "object" && !Array.isArray(payload) ? payload as Partial<ApiFailure> : undefined;
  if (status === 404 || envelope?.error?.code === "not_found") return "not_found";
  if (status === 503) return "backend_unavailable";
  if (status === 408 || status === 504 || envelope?.error?.code === "provider_timeout") return "timeout";
  if (status >= 500) return "backend_unavailable";
  return "unknown";
}

export async function fetchEvidenceRecord(
  evidenceId: string,
  dataVersion: string,
  fetchImpl: typeof fetch = fetch,
  externalSignal?: AbortSignal
): Promise<{ evidence: EvidenceRecord; requestId: string }> {
  if (!/^EV-\d{3}$/.test(evidenceId)) throw new Day4ApiError("not_found", "Evidence id is invalid.");
  const ownRequestId = requestId();
  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => controller.abort(new DOMException("Evidence request timed out.", "TimeoutError")), REQUEST_TIMEOUT_MS);
  const forwardAbort = () => controller.abort(externalSignal?.reason);
  externalSignal?.addEventListener("abort", forwardAbort, { once: true });
  try {
    const response = await fetchImpl(getEvidenceEndpoint(evidenceId), {
      method: "GET",
      headers: { "X-Request-Id": ownRequestId },
      cache: "no-store",
      credentials: "omit",
      signal: controller.signal
    });
    const responseRequestId = response.headers.get("x-request-id") ?? undefined;
    let payload: unknown;
    try { payload = await response.json(); }
    catch { throw new Day4ApiError("malformed_response", "Evidence service returned unreadable JSON.", { requestId: responseRequestId, retryable: false }); }
    if (!response.ok) {
      const envelope = payload && typeof payload === "object" && !Array.isArray(payload) ? payload as Partial<ApiFailure> : undefined;
      const message = typeof envelope?.error?.message === "string" ? envelope.error.message : `Evidence request failed with HTTP ${response.status}.`;
      throw new Day4ApiError(failureCode(response.status, payload), response.status === 404 ? `Evidence endpoint or record ${evidenceId} was not found.` : message, { requestId: envelope?.error?.requestId ?? responseRequestId, retryable: response.status >= 500 || response.status === 408 });
    }
    const validated = validateEvidenceSuccess(payload, evidenceId, dataVersion);
    return { evidence: validated.data.evidence, requestId: validated.requestId };
  } catch (error) {
    if (error instanceof Day4ApiError) throw error;
    if (controller.signal.aborted) {
      const timedOut = controller.signal.reason instanceof DOMException && controller.signal.reason.name === "TimeoutError";
      throw new Day4ApiError(timedOut ? "timeout" : "stale_response", timedOut ? "Evidence lookup timed out. Close or retry without changing the current simulation." : "Evidence lookup was cancelled because the active run changed.", { requestId: ownRequestId, retryable: timedOut });
    }
    throw new Day4ApiError("backend_unavailable", "Evidence source service could not be reached. The current simulation is unchanged.", { requestId: ownRequestId, retryable: true });
  } finally {
    globalThis.clearTimeout(timeout);
    externalSignal?.removeEventListener("abort", forwardAbort);
  }
}
