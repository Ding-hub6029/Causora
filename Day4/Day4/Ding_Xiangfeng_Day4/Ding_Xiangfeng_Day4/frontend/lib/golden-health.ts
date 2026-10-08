export const HEALTH_CHECK_TIMEOUT_MS = 2_500;

export type BackendHealth = {
  requestId: string;
  simulation: string;
  evidence: string;
  missingReasons: string[];
  banner?: string;
};

export type BackendHealthState =
  | { status: "checking" }
  | { status: "healthy"; health: BackendHealth; checkedAt: string }
  | { status: "waking"; message: string; code: "timeout" | "unavailable" | "invalid_response" | "network" };

export class BackendHealthError extends Error {
  readonly code: "timeout" | "unavailable" | "invalid_response" | "network";

  constructor(message: string, code: BackendHealthError["code"]) {
    super(message);
    this.name = "BackendHealthError";
    this.code = code;
  }
}

function record(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

export function getHealthEndpoint(): string {
  const base = typeof process !== "undefined" ? process.env.NEXT_PUBLIC_CAUSORA_API_BASE_URL?.trim() ?? "" : "";
  return base ? `${base.replace(/\/+$/, "")}/health` : "/health";
}

/** Check only service reachability/readiness. A ready health response never implies human or policy approval. */
export async function probeBackendHealth(fetcher: typeof fetch = fetch, timeoutMs = HEALTH_CHECK_TIMEOUT_MS): Promise<BackendHealth> {
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) throw new RangeError("Health check timeout must be a positive number of milliseconds.");
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timedOut = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(new BackendHealthError(`The simulation service did not answer the health check within ${(timeoutMs / 1000).toFixed(1)} seconds. It may be waking from cold sleep.`, "timeout"));
    }, timeoutMs);
  });
  const request = (async () => {
    let response: Response;
    try {
      response = await fetcher(getHealthEndpoint(), {
        method: "GET",
        headers: { accept: "application/json" },
        cache: "no-store",
        credentials: "omit",
        signal: controller.signal
      });
    } catch (error) {
      if (controller.signal.aborted) throw new BackendHealthError("The simulation health check timed out; the service may be waking from cold sleep.", "timeout");
      throw new BackendHealthError(`The simulation health endpoint could not be reached: ${error instanceof Error ? error.message : "network error"}`, "network");
    }
    if (!response.ok) throw new BackendHealthError(`The simulation health endpoint returned HTTP ${response.status}.`, "unavailable");
    let payload: unknown;
    try { payload = await response.json(); }
    catch { throw new BackendHealthError("The simulation health endpoint returned invalid JSON.", "invalid_response"); }
    const envelope = record(payload);
    const data = record(envelope?.data);
    const requestId = envelope?.requestId;
    const service = data?.service;
    const simulation = data?.simulation;
    const evidence = data?.evidence;
    const missingReasons = data?.missingReasons;
    const banner = data?.banner;
    if (envelope?.schemaVersion !== "causora.contract.v1" || typeof requestId !== "string" || !requestId.trim() || service !== "ready" || typeof simulation !== "string" || !simulation.trim() || typeof evidence !== "string" || !evidence.trim() || !Array.isArray(missingReasons) || missingReasons.some((item) => typeof item !== "string")) {
      throw new BackendHealthError("The health response is incomplete or reports that the service is not ready.", "invalid_response");
    }
    return {
      requestId,
      simulation,
      evidence,
      missingReasons: missingReasons as string[],
      ...(typeof banner === "string" ? { banner } : {})
    };
  })();
  try {
    return await Promise.race([request, timedOut]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}
