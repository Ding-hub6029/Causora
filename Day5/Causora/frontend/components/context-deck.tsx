import { ArrowUpRight, FileCheck2, GitBranch, GitCompareArrows, LockKeyhole, ScanSearch, ShieldCheck, SlidersHorizontal } from "lucide-react";
import type { OptionId } from "@/lib/contracts";
import type { Evidence, MockData, StageId } from "@/lib/types";
import { cell, decisionDelta, money, percent, signedPercent } from "@/lib/metrics";

type Props = {
  stage: StageId;
  data: MockData;
  scenarioId: string;
  onEvidence: (evidence: Evidence) => void;
  onFormula: (optionId?: OptionId) => void;
  onStageChange: (stage: StageId) => void;
};

type Insight = { index: string; label: string; value: string; body: string; action: string; onClick: () => void; icon: typeof FileCheck2 };

export function ContextDeck({ stage, data, scenarioId, onEvidence, onFormula, onStageChange }: Props) {
  const scenario = data.scenarios.find((item) => item.id === scenarioId) ?? data.scenarios[0];
  const recommended = data.brief.recommendedOptionId;
  const d0 = cell(data, scenario.id, "D0");
  const d1 = cell(data, scenario.id, recommended);
  const d2 = cell(data, scenario.id, "D2");
  const delta = decisionDelta(data, scenario.id, recommended, "D0");
  const serviceSpread = ((d2.serviceLevel - d1.serviceLevel) * 100).toFixed(1);
  const ev = (id: string) => data.evidence.find((record) => record.id === id);
  const evidence = (id: string) => { const item = ev(id); if (item) onEvidence(item); };
  const scrollTo = (selector: string) => document.querySelector(selector)?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
  const notice = ev("EV-014");
  const minShare = ev("EV-024");
  const exitFee = ev("EV-027");
  const compound = data.scenarios.find((item) => item.id === data.critic.mechanism.scenarioId);
  let insights: Insight[];

  if (stage === "intake") insights = [
    { index: "01 / TIMING", label: "Contract clock", value: notice?.extractedValue ?? "—", body: `The renewal notice window is source-matched on page ${notice?.page ?? "—"}; the decision date ${data.contract.decisionDate} is ${data.contract.daysToRenewal} days from renewal on ${data.contract.renewalDate}, and no written notice is on record.`, action: `Inspect ${notice?.id ?? "evidence"}`, onClick: () => evidence("EV-014"), icon: FileCheck2 },
    { index: "02 / COVERAGE", label: "Evidence perimeter", value: `${data.intake.length} sources`, body: "Demand history, delivery records, opening inventory and the machine-readable supplier agreement form the local input boundary.", action: "View input register", onClick: () => scrollTo(".file-register"), icon: ScanSearch },
    { index: "03 / HANDOFF", label: "Next transformation", value: "Quote → variable", body: `${data.variables.length} matched contract fields are mapped to explicit business variables before any option is compared.`, action: "Open Scenario Lab", onClick: () => onStageChange("scenario"), icon: GitBranch }
  ];
  else if (stage === "scenario") insights = [
    { index: "01 / EXTERNAL", label: "Selected world", value: scenario.label, body: `Demand shock ${signedPercent(scenario.demandShock)} · lead-time condition ${scenario.leadTime}. This is a preset mock scenario, not an option.`, action: "Compare preset values", onClick: () => onStageChange("matrix"), icon: SlidersHorizontal },
    { index: "02 / CONTRACT", label: "Locked commitment", value: `${minShare?.extractedValue ?? percent(data.contract.minPurchaseShareA)} to A`, body: `${recommended} can retain the minimum A share (${data.contract.minPurchaseUnitsA.toLocaleString("en-US")} units of the locked forecast). D2 requires the ${money(data.contract.terminationFeeUsd)} exit fee in the renewed term.`, action: `Inspect ${minShare?.id ?? "evidence"}`, onClick: () => evidence("EV-024"), icon: LockKeyhole },
    { index: "03 / CONTROL", label: "Available moves", value: data.options.map((option) => option.id).join(" / "), body: "Keep A, diversify at the minimum, or exit with the contract cost. These three actions stay fixed while the external world changes.", action: "See the matrix", onClick: () => onStageChange("matrix"), icon: GitCompareArrows }
  ];
  else if (stage === "matrix") insights = [
    { index: "01 / COST", label: `${recommended} vs D0 · ${scenario.label}`, value: `${money(Math.abs(delta.deltaTco))} ${delta.deltaTco <= 0 ? "lower" : "higher"}`, body: `In ${scenario.label}, ${recommended} has ${money(d1.expectedTco)} expected 24m TCO versus D0 at ${money(d0.expectedTco)}. Values are preset mock data.`, action: `Open ${recommended} formula trace`, onClick: () => onFormula(recommended), icon: GitCompareArrows },
    { index: "02 / SERVICE", label: "Service trade-off", value: `${serviceSpread} pp`, body: `D2 service ${percent(d2.serviceLevel, 1)} versus ${recommended} ${percent(d1.serviceLevel, 1)}; the exit path carries higher mock cost and the ${exitFee?.extractedValue ?? money(data.contract.terminationFeeUsd)} termination fee.`, action: "Inspect exit clause", onClick: () => evidence("EV-027"), icon: ShieldCheck },
    { index: "03 / RULE", label: "Inspectable ranking", value: "Constraint first", body: "Feasibility and risk filters come before expected cost. Day 1 shows code-bound preset cells; no simulation ran.", action: "Review perspectives", onClick: () => onStageChange("boardroom"), icon: ScanSearch }
  ];
  else if (stage === "boardroom") insights = [
    { index: "01 / SCOPE", label: "Separate lenses", value: data.boardroom.map((agent) => agent.role).join(" · "), body: "Cost and cash, service and stockout, then contract exposure are reviewed as distinct mock perspectives.", action: "Inspect role cards", onClick: () => scrollTo(".agent-deck"), icon: GitBranch },
    { index: "02 / CRITIC", label: "Compound question", value: `${compound ? signedPercent(compound.demandShock) : "—"} × ${minShare?.extractedValue ?? "—"}`, body: `A demand decline against a minimum purchase share measured on the locked forecast leaves ${data.critic.mechanism.committedExcessUnits.toLocaleString("en-US")} Supplier A units above a rolling minimum-share benchmark, not above total demand. D1 purchases exceed realised demand by ${(cell(data, data.critic.mechanism.scenarioId, 'D1').unitsFromA + cell(data, data.critic.mechanism.scenarioId, 'D1').unitsFromB - data.critic.mechanism.scenarioDemandUnits24m).toLocaleString('en-US')} units.`, action: `Inspect ${minShare?.id ?? "evidence"}`, onClick: () => evidence("EV-024"), icon: ScanSearch },
    { index: "03 / EVIDENCE", label: "Source coverage", value: `${data.critic.evidenceIds.length} cited IDs`, body: `The Critic references ${data.critic.evidenceIds.join(", ")}. It cannot invent a new contract term.`, action: "Open first citation", onClick: () => evidence(data.critic.evidenceIds[0]), icon: FileCheck2 }
  ];
  else insights = [
    { index: "01 / PROVENANCE", label: `What backs ${recommended}`, value: "Evidence + metric", body: "The contract minimum, renewal price and exit fee connect the quote trail to a fixed mock comparison.", action: "Open evidence", onClick: () => evidence("EV-024"), icon: FileCheck2 },
    { index: "02 / AUTHORITY", label: "What remains human", value: "Approve / reject", body: "A local reviewer can accept, decline or revise assumptions; this prototype never changes a supplier or contract.", action: "Go to decision controls", onClick: () => scrollTo(".human-control"), icon: ShieldCheck },
    { index: "03 / REVISION", label: "Inspectable return path", value: "Back to scenario", body: "Return to the external scenario and compare the same three options under a different preset world.", action: "Change assumptions", onClick: () => onStageChange("scenario"), icon: SlidersHorizontal }
  ];

  return <section className="context-deck" aria-label="Decision context and next steps">
    <div className="context-heading"><div><span>THE DECISION THREAD / {stage.toUpperCase()}</span><h2>Read the signal. Follow the proof.</h2></div><p>Every panel is anchored to the local Day 1 mock contract ({data.meta.dataVersion}). No live data or provider call is implied.</p></div>
    <div className="context-grid">{insights.map((insight) => { const Icon = insight.icon; return <article className="context-card" key={insight.index}><div className="context-card-top"><span>{insight.index}</span><Icon size={18} /></div><small>{insight.label}</small><h3>{insight.value}</h3><p>{insight.body}</p><button type="button" onClick={insight.onClick}>{insight.action}<ArrowUpRight size={14} /></button></article>; })}</div>
  </section>;
}
