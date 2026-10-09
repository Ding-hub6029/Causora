import type { LiveSimulation } from "./types";
import { money, percent, signedMoney } from "./metrics";

export const BOARDROOM_METRIC_TOKENS = ["delta_tco", "stockout_probability", "cash_outflow_p90"] as const;
export type BoardroomMetricToken = typeof BOARDROOM_METRIC_TOKENS[number];
export type BoardroomMetricValues = Record<BoardroomMetricToken, string>;

const ALLOWED_TOKENS = new Set<string>(BOARDROOM_METRIC_TOKENS);
const TOKEN_PATTERN = /\{\{([a-z][a-z0-9_]*)\}\}/g;

/** A body may reference only the supported metric tokens declared in its metrics list. */
export function boardroomTemplateError(body: string, metricRefs: readonly string[]): string | null {
  const tokens = [...body.matchAll(TOKEN_PATTERN)].map((match) => match[1]);
  const remainder = body.replace(TOKEN_PATTERN, "");
  if (remainder.includes("{{") || remainder.includes("}}")) return "contains a malformed {{token}} placeholder.";
  for (const token of tokens) {
    if (!ALLOWED_TOKENS.has(token)) return `contains unsupported metric token "${token}".`;
    if (!metricRefs.includes(token)) return `references "${token}" without declaring it in metrics.`;
  }
  return null;
}

/** Values are derived from the selected option in the same validated Simulation/scenario. */
export function boardroomMetricValues(liveRun: LiveSimulation, scenarioId: string): BoardroomMetricValues {
  const selection = liveRun.response.data.selections[scenarioId];
  const optionId = selection?.status === "selected" ? selection.recommendedOptionId : null;
  const cell = optionId
    ? liveRun.response.data.simulation.matrix[scenarioId]?.find((row) => row.optionId === optionId)
    : undefined;
  const delta = optionId
    ? liveRun.response.data.deltas.find((item) => item.scenarioId === scenarioId && item.optionId === optionId)
    : undefined;
  return {
    delta_tco: delta ? signedMoney(delta.deltaTco) : "Not available",
    stockout_probability: cell ? percent(cell.stockoutProbability) : "Not available",
    cash_outflow_p90: cell ? money(cell.cashOutflowP90) : "Not available"
  };
}

/** Plain-text interpolation: React escapes the returned string; no model HTML is interpreted. */
export function renderBoardroomBody(body: string, values: Partial<BoardroomMetricValues>): string {
  return body.replace(TOKEN_PATTERN, (_placeholder, rawToken: string) => {
    if (!ALLOWED_TOKENS.has(rawToken)) return "[unverified metric]";
    const value = values[rawToken as BoardroomMetricToken];
    return typeof value === "string" ? value : "[metric unavailable]";
  });
}
