import type { CostBreakdown, DecisionDelta, MetricCell, OptionId, ScenarioSelection, ConstraintViolation } from "./contracts";
import type { MockData } from "./types";

/** `$420k` style money formatting for whole-dollar inputs. */
export function money(usd: number): string {
  const sign = usd < 0 ? "−" : "";
  const abs = Math.abs(usd);
  if (abs >= 1000 && abs % 1000 === 0) return `${sign}$${abs / 1000}k`;
  return `${sign}$${abs.toLocaleString("en-US")}`;
}

/** Full-precision money for formula rows, e.g. `$43,680`. */
export function moneyExact(usd: number): string {
  const sign = usd < 0 ? "−" : "";
  return `${sign}$${Math.abs(usd).toLocaleString("en-US")}`;
}

export function percent(fraction: number, digits = 0): string {
  return `${(fraction * 100).toFixed(digits)}%`;
}

export function signedPercent(whole: number): string {
  return `${whole > 0 ? "+" : whole < 0 ? "−" : ""}${Math.abs(whole)}%`;
}

export function signedMoney(usd: number): string {
  if (usd === 0) return "$0";
  const absolute = Math.abs(usd);
  return `${usd < 0 ? "−" : "+"}${absolute % 1000 === 0 ? money(absolute) : moneyExact(absolute)}`;
}

export function signedPp(pp: number): string {
  if (pp === 0) return "0 pp";
  return `${pp < 0 ? "−" : "+"}${Number(Math.abs(pp).toFixed(3))} pp`;
}

export function units(value: number): string {
  return `${value.toLocaleString("en-US")} units`;
}

export function cell(data: MockData, scenarioId: string, optionId: OptionId): MetricCell {
  const found = data.simulation.matrix[scenarioId]?.find((row) => row.optionId === optionId);
  if (!found) throw new Error(`Missing metric cell ${scenarioId}/${optionId}`);
  return found;
}

export function sumBreakdown(breakdown: CostBreakdown): number {
  return breakdown.purchase + breakdown.holding + breakdown.stockoutLoss + breakdown.renewalPremium + breakdown.terminationFee;
}

/** Live recommendation emphasis follows the validated selection, never a server-supplied tone hint. */
export function displayMatrixTone(cell: MetricCell, selection?: ScenarioSelection): MetricCell["tone"] {
  if (!selection) return cell.tone;
  if (selection.status === "selected" && selection.recommendedOptionId === cell.optionId) return "recommended";
  return cell.tone === "risk" ? "risk" : "neutral";
}

/** Inclusive limits, one deterministic selection for this scenario only. */
export function selectScenarioOption(data: MockData, scenarioId: string, riskThreshold: number, budgetCeilingUsd: number): ScenarioSelection {
  if (!Number.isFinite(riskThreshold) || riskThreshold < 0 || riskThreshold > 1 || !Number.isFinite(budgetCeilingUsd) || budgetCeilingUsd < 0) throw new Error("Invalid selection constraints");
  const rows = data.simulation.matrix[scenarioId];
  if (!rows) throw new Error(`Unknown scenario ${scenarioId}`);
  const constraintViolations: ConstraintViolation[] = [];
  const eligible = [...rows].sort((a, b) => a.optionId.localeCompare(b.optionId)).filter((row) => {
    const failures: ConstraintViolation["code"][] = [];
    if (!row.feasible) failures.push("infeasible");
    if (row.stockoutProbability > riskThreshold) failures.push("stockout_threshold");
    if (row.cashOutflowP90 > budgetCeilingUsd) failures.push("cash_ceiling");
    constraintViolations.push(...failures.map((code) => ({ optionId: row.optionId, code })));
    return failures.length === 0;
  });
  eligible.sort((a, b) => a.expectedTco - b.expectedTco || a.optionId.localeCompare(b.optionId));
  return eligible.length ? { scenarioId, status: "selected", recommendedOptionId: eligible[0].optionId, constraintViolations } : { scenarioId, status: "no_feasible_option", recommendedOptionId: null, constraintViolations };
}

/** Code-computed Decision Delta following the specification: option minus baseline option. */
export function decisionDelta(data: MockData, scenarioId: string, optionId: OptionId, baselineOptionId: OptionId = "D0"): DecisionDelta {
  const option = cell(data, scenarioId, optionId);
  const base = cell(data, scenarioId, baselineOptionId);
  return {
    scenarioId,
    optionId,
    baselineOptionId,
    deltaTco: option.expectedTco - base.expectedTco,
    deltaStockoutPp: Number((100 * (option.stockoutProbability - base.stockoutProbability)).toFixed(10)),
    deltaServicePp: Number((100 * (option.serviceLevel - base.serviceLevel)).toFixed(10)),
    deltaCashP90: option.cashOutflowP90 - base.cashOutflowP90
  };
}

/**
 * Numeric Guardrail rendering. Agent and Critic text may contain numbers only through tokens:
 *   {{delta_tco:scenario:base:option}}  -> "$9k lower" style absolute saving
 *   {{tco:scenario:option}}             -> "$420k"
 *   {{stockout:scenario:option}}        -> "9%"
 *   {{evidence:EV-024}}                 -> extracted value
 *   {{scenario:id:demandShock}}         -> "−15%"
 *   {{scenario:id:demandUnits}}         -> "22,100 units"
 *   {{contract:field}}                  -> formatted contract constraint field
 * Unknown tokens render as `[unresolved token]` so they are visible in review.
 */
export function renderGuarded(template: string, data: MockData): string {
  if (/\d/.test(stripTokens(template).replace(/\bD[012]\b/g, ""))) return "[unverified numeric claim]";
  return template.replace(/\{\{([^}]+)\}\}/g, (_, raw: string) => {
    const [kind, a, b, c] = raw.split(":");
    try {
      if (kind === "delta_tco") {
        const delta = decisionDelta(data, a, c as OptionId, b as OptionId).deltaTco;
        return delta === 0 ? "the same cost as" : `${money(Math.abs(delta))} ${delta < 0 ? "below" : "above"}`;
      }
      if (kind === "tco") return money(cell(data, a, b as OptionId).expectedTco);
      if (kind === "stockout") return `${Number((cell(data, a, b as OptionId).stockoutProbability * 100).toFixed(3))}%`;
      if (kind === "evidence") return data.evidence.find((item) => item.id === a)?.extractedValue ?? "[unresolved token]";
      if (kind === "scenario") {
        const scenario = data.scenarios.find((item) => item.id === a);
        if (!scenario) return "[unresolved token]";
        if (b === "demandShock") return signedPercent(scenario.demandShock);
        if (b === "demandUnits") return units(scenario.demandUnits24m);
        if (b === "label") return scenario.label;
      }
      if (kind === "contract") {
        const value = data.contract[a as keyof MockData["contract"]];
        if (typeof value === "number") return a.toLowerCase().includes("usd") ? moneyExact(value) : a.toLowerCase().includes("units") ? units(value) : String(value);
        if (typeof value === "string" || typeof value === "boolean") return String(value);
      }
    } catch {
      return "[unresolved token]";
    }
    return "[unresolved token]";
  });
}

/** Removes every token so tests can prove that no free-form digits remain in a template. */
export function stripTokens(template: string): string {
  return template.replace(/\{\{[^}]+\}\}/g, "");
}
