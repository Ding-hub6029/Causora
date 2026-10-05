import { AnimatePresence, motion } from "framer-motion";
import { BadgeCheck, Boxes, BrainCircuit, Check, ChevronDown, CircleDollarSign, CircleHelp, ClipboardCheck, Database, FileCheck2, FileText, GitCompareArrows, Info, LockKeyhole, RotateCcw, Scale, SearchCheck, Settings2, SlidersHorizontal, Telescope, TriangleAlert, Upload, Waypoints, X } from "lucide-react";
import { useState } from "react";
import type { OptionId } from "@/lib/contracts";
import type { AppState, Evidence, MockData, StageId } from "@/lib/types";
import { decisionDelta, money, percent, renderGuarded, signedMoney, signedPercent, signedPp } from "@/lib/metrics";
import { GhostButton, Metric, Panel, PrimaryButton, SectionLabel, StateCard, StatusChip, TraceLink } from "./ui";
import { ContextDeck } from "./context-deck";

type StageProps = {
  stage: StageId;
  appState: AppState;
  data: MockData;
  currentScenario: MockData["scenarios"][number];
  scenarioId: string;
  demandShift: number;
  riskThreshold: number;
  isDraft: boolean;
  selectedOption: OptionId;
  humanDecision: string | null;
  onScenarioChange: (id: string) => void;
  onDemandShiftChange: (value: number) => void;
  onRiskThresholdChange: (value: number) => void;
  onOptionSelect: (id: OptionId) => void;
  onEvidence: (evidence: Evidence) => void;
  onEvidenceStack: () => void;
  onFormula: (optionId?: OptionId) => void;
  onNext: () => void;
  onPreviewState: (state: AppState) => void;
  onGoldenRun: () => void;
  onDecision: (decision: string) => void;
  onStageChange: (stage: StageId) => void;
};

const stageCopy: Record<StageId, { number: string; kicker: string; title: string; body: string }> = {
  intake: { number: "01", kicker: "Verified starting point", title: "Bring the record into focus.", body: "A deliberate decision begins with the files you can inspect, not a generated summary you cannot." },
  scenario: { number: "02", kicker: "External world, explicit", title: "Separate uncertainty from control.", body: "Scenarios describe what happens to you. Options describe what you can do about it." },
  matrix: { number: "03", kicker: "Code-bound comparison", title: "See the trade-off before the story.", body: "Every matrix cell represents a predefined option under one explicit external scenario." },
  boardroom: { number: "04", kicker: "Independent viewpoints", title: "Invite challenge into the room.", body: "Each perspective sees only its permitted decision surface. The Critic connects what they miss alone." },
  brief: { number: "05", kicker: "Human decision", title: "A recommendation ready for challenge.", body: "The recommendation is constrained to a simulated option. Human approval remains the final control." }
};

function PageIntro({ stage, appState, onPreviewState }: { stage: StageId; appState: AppState; onPreviewState: (state: AppState) => void }) {
  const copy = appState === "no-feasible" ? { ...stageCopy[stage], title: "No option passes the constraints.", body: "A recommendation requires a feasible option. Review the assumptions before requesting a new comparison." } : stageCopy[stage];
  return <div className="page-intro">
    <div><SectionLabel index={copy.number} label={copy.kicker} /><h1>{copy.title}</h1><p>{copy.body}</p></div>
    <div className="state-studio" aria-label="Preview Day 1 UI states">
      <span><Settings2 size={14} />State studio</span>
      <div>
        {(["loading", "empty", "error", "no-feasible"] as const).map((state) => <button key={state} type="button" className={appState === state ? "selected" : ""} aria-pressed={appState === state} onClick={() => onPreviewState(state)}>{state === "no-feasible" ? "No feasible option" : state}</button>)}
      </div>
    </div>
  </div>;
}

function StatePreview({ stage, state, onPreviewState, onGolden }: { stage: StageId; state: "loading" | "empty" | "error"; onPreviewState: (state: AppState) => void; onGolden: () => void }) {
  return <div className="stage-content"><PageIntro stage={stage} appState={state} onPreviewState={onPreviewState} /><Panel className="state-preview-panel"><StateCard stage={stageCopy[stage].title.split(".")[0]} state={state} /><div className="state-actions"><div><small>DAY 1 RESILIENCE PREVIEW</small><h2>Graceful degradation is part of the product.</h2><p>The active stage intentionally shows its {state} state. No data has left this browser. You can switch to another preview state, restore the local dataset, or load the cached Golden Run.</p></div><div className="button-row"><GhostButton onClick={() => onPreviewState("ready")}><RotateCcw size={15} />Restore local state</GhostButton><PrimaryButton onClick={onGolden}>Load Golden Run</PrimaryButton></div></div></Panel></div>;
}

function IntakeView({ data, onNext, onEvidence }: Pick<StageProps, "data" | "onNext" | "onEvidence">) {
  const fileIcons = { demand: Database, delivery: Upload, inventory: Boxes, contract: FileText };
  const first = data.evidence[0];
  const matched = data.evidence.filter((item) => item.quoteMatched).length;
  return <div className="stage-grid intake-grid">
    <Panel className="intake-hero">
      <div className="hero-orb" aria-hidden="true"><span /><i /><b /></div>
      <div className="intake-hero-copy"><StatusChip tone="success">{data.intake.length} INPUTS READY</StatusChip><h2>Records form the first<br /><em>evidence boundary.</em></h2><p>Every source starts as a visible, local object. No opaque enrichment has been applied.</p><div className="button-row"><PrimaryButton onClick={onNext}>Inspect matched evidence</PrimaryButton><span className="tiny-proof"><LockKeyhole size={13} />Local demo only</span></div></div>
      <div className="dataset-stack" aria-label="Imported datasets">{data.intake.map((item, index) => <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 * index }} className="dataset-chip" key={item.id}><span className="dataset-icon">{(() => { const Icon = fileIcons[item.id as keyof typeof fileIcons]; return <Icon size={15} />; })()}</span><div><b>{item.label}</b><small>{item.type} · {item.detail}</small></div><BadgeCheck size={16} /></motion.div>)}</div>
      <div className="intake-hero-foot"><span><i />{matched} / {data.evidence.length} contract fields quote-matched</span><span>{first.id} · p. {first.page} · {first.matchMethod} {percent(first.matchScore)}</span></div>
    </Panel>
    <Panel className="file-register" title="Import register" action={<StatusChip tone="success">Verified</StatusChip>}>
      <div className="register-head"><span>Source file</span><span>Footprint</span><span>State</span></div>
      {data.intake.map((file) => <div className="register-row" key={file.id}><div><a href={file.path} target="_blank" rel="noopener noreferrer" aria-label={`Open synthetic ${file.label} file`}>{file.label}</a><small>{file.type} · {file.size}</small></div><span>{file.detail}</span><StatusChip tone={file.status === "Matched" ? "signal" : "success"}>{file.status}</StatusChip></div>)}
      <div className="integrity-band"><SearchCheck size={18} /><span><b>Input integrity is explicit.</b> The contract is machine-readable; the remaining inputs are local structured files.</span></div>
    </Panel>
    <Panel className="intake-evidence-card" title="The first matched clause">
      <div className="evidence-mini"><span className="evidence-id">{first.id}</span><strong>{first.extractedValue}</strong><p>{first.quote}</p><TraceLink kind="evidence" onClick={() => onEvidence(first)}>Open source quote</TraceLink></div>
    </Panel>
  </div>;
}

function ScenarioView({ data, scenarioId, currentScenario, demandShift, riskThreshold, isDraft, onScenarioChange, onDemandShiftChange, onRiskThresholdChange, onNext, onEvidence, onStageChange }: Pick<StageProps, "data" | "scenarioId" | "currentScenario" | "demandShift" | "riskThreshold" | "isDraft" | "onScenarioChange" | "onDemandShiftChange" | "onRiskThresholdChange" | "onNext" | "onEvidence" | "onStageChange">) {
  const minShare = data.evidence.find((item) => item.id === "EV-024")?.extractedValue ?? percent(data.contract.minPurchaseShareA);
  return <div className="stage-grid scenario-grid">
    <Panel className="scenario-control" title="External scenario">
      <div className="scenario-tabs" role="tablist" aria-label="Select mock scenario">{data.scenarios.map((scenario) => <button key={scenario.id} type="button" role="tab" aria-selected={scenarioId === scenario.id} onClick={() => onScenarioChange(scenario.id)} className={scenarioId === scenario.id ? "active" : ""}><span>{scenario.label}</span><small>{scenario.tag}</small></button>)}</div>
      <div className="scenario-focus"><div><small>SELECTED EXTERNAL WORLD</small><h2>{currentScenario.label}</h2><p>{currentScenario.description}</p></div><div className="scenario-signal"><Telescope size={22} /><span>External<br />only</span></div></div>
      <div className="slider-stack">
        <label><span>Demand shock <b>{signedPercent(demandShift)}</b></span><input aria-label="Demand shock" type="range" min="-20" max="10" value={demandShift} onChange={(event) => onDemandShiftChange(Number(event.target.value))} /><small>Scenario input · external world, not the option.</small></label>
        <label><span>Stockout risk threshold <b>{riskThreshold}%</b></span><input aria-label="Stockout risk threshold" type="range" min="4" max="25" value={riskThreshold} onChange={(event) => onRiskThresholdChange(Number(event.target.value))} /><small>User-controlled tolerance for a future live simulation.</small></label>
      </div>
      <div className="assumption-disclosure"><Info size={15} /><span>Day 1 draft controls only. The Matrix shows the selected preset snapshot; changing a slider does not recalculate its mock values.</span></div>
      {isDraft && <button type="button" className="assumption-reset" onClick={() => { onDemandShiftChange(currentScenario.demandShock); onRiskThresholdChange(12); }}><RotateCcw size={14} />Restore preset inputs to enable approval</button>}
      <div className="button-row"><GhostButton onClick={() => onStageChange("intake")}>Back to inputs</GhostButton><PrimaryButton onClick={onNext}>Compare options</PrimaryButton></div>
    </Panel>
    <Panel className="variable-panel" title="Evidence → Business Variables" action={<span className="code-tag">{data.variables.length} QUOTE-MATCHED</span>}>
      {data.variables.map((variable, index) => <motion.div className="variable-row" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.06 }} key={variable.key}><div><b>{variable.name}</b><small>{renderGuarded(variable.meaning, data)}</small><small className="variable-inputs">Inputs: {variable.inputs.map((input) => `${input.name} = ${input.value}`).join(" · ")}</small></div><div><strong>{variable.value}</strong><button type="button" onClick={() => { const evidence = data.evidence.find((item) => item.id === variable.source); if (evidence) onEvidence(evidence); }}>{variable.source}</button></div></motion.div>)}
      <div className="rule-note"><Scale size={16} /><span><b>Constraint rule (synthetic register assumption):</b> notice deadline {data.contract.noticeDeadline} passed with no written notice on record ({data.contract.daysToRenewal} days to renewal &lt; {data.contract.renewalNoticeDays}-day window), so D1 must keep {minShare} with A and D2 must carry the {money(data.contract.terminationFeeUsd)} termination cost. <a href="/demo/supplier_correspondence_log.csv" target="_blank" rel="noopener noreferrer">Inspect mock notice register</a>.</span></div>
    </Panel>
    <Panel className="option-principle"><div className="mini-icon"><Waypoints size={19} /></div><h3>Two objects.<br />Never blended.</h3><p><b>Scenario</b> = external pressure.<br /><b>Option</b> = controllable choice.</p></Panel>
  </div>;
}

function MatrixView({ data, scenarioId, currentScenario, demandShift, riskThreshold, isDraft, selectedOption, onOptionSelect, onFormula, onNext }: Pick<StageProps, "data" | "scenarioId" | "currentScenario" | "demandShift" | "riskThreshold" | "isDraft" | "selectedOption" | "onOptionSelect" | "onFormula" | "onNext">) {
  const activeRow = data.simulation.matrix[scenarioId];
  return <div className="stage-grid matrix-grid">
    <Panel className="matrix-panel">
      <div className="matrix-header"><div><small>OPTION × SCENARIO MATRIX</small><h2>{currentScenario.label}<span> / deterministic mock</span></h2></div><StatusChip tone="signal">CODE-BOUND VALUES</StatusChip></div>
      {isDraft && <div className="matrix-draft-note"><Info size={15} /><span>Draft assumptions: demand {signedPercent(demandShift)} · threshold {riskThreshold}%. Values below are the unchanged preset mock snapshot—not a recalculation.</span></div>}
      <div className="matrix-table" role="table" aria-label="Mock option scenario matrix"><div className="matrix-table-head" role="row"><span>Decision option</span><span>Expected 24m TCO</span><span>Stockout probability</span><span>Service level</span><span>P90 cash</span></div>{data.options.map((option) => { const metrics = activeRow.find((row) => row.optionId === option.id); if (!metrics) return null; const active = option.id === selectedOption; return <button type="button" className={`matrix-row ${metrics.tone} ${active ? "selected" : ""}`} key={option.id} onClick={() => onOptionSelect(option.id)} aria-pressed={active}><span className="option-cell"><b>{option.id}</b><i><strong>{option.label}</strong><small>{option.allocation}</small></i></span><span><b>{money(metrics.expectedTco)}</b></span><span><b>{percent(metrics.stockoutProbability)}</b></span><span><b>{percent(metrics.serviceLevel, 1)}</b></span><span><b>{money(metrics.cashOutflowP90)}</b></span>{metrics.tone === "recommended" && <em>Best fit</em>}</button>; })}</div>
      <div className="matrix-footer"><div><Info size={15} />Mock deterministic values for Day 1 only. Final cells must be generated by SimulationResult.</div><TraceLink onClick={() => onFormula(selectedOption)}>Open Formula Trace for {selectedOption}</TraceLink></div>
    </Panel>
    <Panel className="option-inspector" title="Selected option">
      {(() => { const option = data.options.find((item) => item.id === selectedOption) ?? data.options[1]; const metrics = activeRow.find((item) => item.optionId === option.id); return <><div className="inspector-option"><span>{option.id}</span><div><h3>{option.label}</h3><p>{option.description}</p></div></div><div className="metric-row"><Metric label="Expected TCO" value={metrics ? money(metrics.expectedTco) : "—"} tone="lime" /><Metric label="Stockout" value={metrics ? percent(metrics.stockoutProbability) : "—"} tone="blue" /></div><div className="decision-logic"><GitCompareArrows size={18} /><p><b>Selection rule:</b> filter infeasible options, apply the stockout threshold ({riskThreshold}%) and cash constraints, then select the lowest expected TCO.</p></div></>; })()}
      <div className="button-row"><GhostButton onClick={() => onFormula(selectedOption)}>Inspect {selectedOption} formulas</GhostButton><PrimaryButton onClick={onNext}>Open Boardroom</PrimaryButton></div>
    </Panel>
  </div>;
}

function BoardroomView({ data, onEvidence, onNext }: Pick<StageProps, "data" | "onEvidence" | "onNext">) {
  const [openRoles, setOpenRoles] = useState<string[]>(data.boardroom.map((agent) => agent.role));
  const mechanism = data.critic.mechanism;
  return <div className="stage-grid boardroom-grid">
    <Panel className="boardroom-hero"><div><StatusChip tone="signal">PARALLEL MOCK REVIEW</StatusChip><h2>Three limited views.<br /><em>One stronger challenge.</em></h2></div><div className="dag"><span>SimulationResult<br />+ EvidenceSummary</span><i /><b>CFO</b><b>COO</b><b>Risk</b><i /><strong>Critic</strong><i /><em>Brief</em></div></Panel>
    <div className="agent-deck">{data.boardroom.map((agent, index) => { const expanded = openRoles.includes(agent.role); return <motion.article className={`agent-card ${agent.accent} ${expanded ? "open" : ""}`} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.08 }} key={agent.role}><button type="button" onClick={() => setOpenRoles((current) => current.includes(agent.role) ? current.filter((role) => role !== agent.role) : [...current, agent.role])} aria-expanded={expanded}><span className="agent-top"><i>{agent.role.slice(0, 1)}</i><em>{agent.focus}</em><ChevronDown size={16} /></span><h3>{agent.headline}</h3><StatusChip tone={agent.status === "Watch" ? "warning" : "success"}>{agent.status}</StatusChip></button><AnimatePresence>{expanded && <motion.div className="agent-details" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}><p>{renderGuarded(agent.body, data)}</p><div>{agent.metrics.map((metric) => <span key={metric}>{metric}</span>)}</div></motion.div>}</AnimatePresence></motion.article>; })}</div>
    <Panel className="critic-panel"><div className="critic-badge"><BrainCircuit size={20} /><span>CRITIC<br />{data.critic.severity}</span></div><div><small>CROSS-VIEW ISSUE</small><h2>{data.critic.headline}</h2><p>{renderGuarded(data.critic.body, data)}</p><div className="critic-mechanism"><span>Locked forecast <b>{mechanism.lockedForecastUnits24m.toLocaleString("en-US")} u</b></span><span>Committed to A <b>{mechanism.minPurchaseUnitsA.toLocaleString("en-US")} u</b></span><span>Scenario demand <b>{mechanism.scenarioDemandUnits24m.toLocaleString("en-US")} u</b></span><span>A floor above rolling benchmark <b>{mechanism.committedExcessUnits.toLocaleString("en-US")} u</b></span><span>Holding Δ D0 / D1 / D2 <b>{signedMoney(mechanism.holdingCostDeltaUsd.D0)} / {signedMoney(mechanism.holdingCostDeltaUsd.D1)} / {signedMoney(mechanism.holdingCostDeltaUsd.D2)}</b></span></div><div className="evidence-buttons">{data.critic.evidenceIds.map((id) => { const evidence = data.evidence.find((item) => item.id === id); return evidence ? <button type="button" key={id} onClick={() => onEvidence(evidence)}>{id}</button> : null; })}</div></div><PrimaryButton onClick={onNext}>Review decision brief</PrimaryButton></Panel>
  </div>;
}

function BriefView({ data, scenarioId, currentScenario, demandShift, riskThreshold, isDraft, selectedOption, humanDecision, onFormula, onEvidenceStack, onDecision, onStageChange }: Pick<StageProps, "data" | "scenarioId" | "currentScenario" | "demandShift" | "riskThreshold" | "isDraft" | "selectedOption" | "humanDecision" | "onFormula" | "onEvidenceStack" | "onDecision" | "onStageChange">) {
  const recommended = data.brief.recommendedOptionId;
  const delta = decisionDelta(data, scenarioId, recommended, "D0");
  const deltas = [
    { label: "Expected 24m TCO", value: signedMoney(delta.deltaTco) },
    { label: "Stockout probability", value: signedPp(delta.deltaStockoutPp) },
    { label: "P90 cash outflow", value: signedMoney(delta.deltaCashP90) }
  ];
  const minShare = data.evidence.find((item) => item.id === "EV-024");
  return <div className="stage-grid brief-grid">
    <Panel className="recommendation-card"><div className="brief-top"><div><small>DECISION BRIEF / {currentScenario.label.toUpperCase()} MOCK RUN</small><StatusChip tone="signal">CODE-BOUND RECOMMENDATION</StatusChip></div><span className="brief-id">{recommended}</span></div><h2>{data.brief.recommendation}</h2><p>{data.brief.rationale}</p><div className="brief-guardrail"><LockKeyhole size={16} /><span>{data.brief.guardrail}</span></div>{isDraft && <div className="brief-draft-warning" role="status"><TriangleAlert size={16} /><span><b>Approval basis: the {currentScenario.label} preset only.</b> Your draft assumptions (demand {signedPercent(demandShift)}, threshold {riskThreshold}%) have not been simulated and are not reflected in these numbers.</span></div>}<div className="delta-grid">{deltas.map((item, index) => <Metric key={item.label} label={item.label} value={item.value} detail={`${recommended} vs. D0 in ${currentScenario.label} mock run`} tone={index === 0 ? "lime" : "light"} />)}</div><div className="button-row"><TraceLink onClick={() => onFormula(recommended)}>Formula Trace · {recommended}</TraceLink><TraceLink kind="evidence" onClick={onEvidenceStack}>Evidence stack · {data.evidence.length}</TraceLink></div><div className="brief-proof-strip"><div><small>01 / SOURCE</small><b>{minShare?.id ?? "EV-024"}</b><span>{minShare?.extractedValue ?? ""} minimum share</span></div><div><small>02 / OPTION</small><b>{recommended}</b><span>Preset mock comparison</span></div><div><small>03 / AUTHORITY</small><b>Human reviewer</b><span>No external action</span></div></div></Panel>
    <Panel className="human-control" title="Human decision control"><div className="human-portrait"><span>H</span><div><small>REVIEWER REQUIRED</small><h3>You retain the final call.</h3></div></div><p>The system has narrowed a traceable option. It has not taken action, changed a supplier, or approved any contract.{isDraft ? " Approval is disabled because your draft inputs have not been simulated; restore the preset first." : ""}</p><div className="decision-buttons"><button type="button" className="approve" onClick={() => onDecision("Approved")} disabled={isDraft} title={isDraft ? "Restore preset assumptions before approving" : undefined}><Check size={17} />Approve {recommended}{isDraft ? " · unavailable for draft" : ""}</button><button type="button" className="reject" onClick={() => onDecision("Rejected")}><X size={17} />Reject</button><button type="button" className="change" onClick={() => { onDecision("Assumptions queued"); onStageChange("scenario"); }}><SlidersHorizontal size={17} />Change assumptions</button></div>{humanDecision && <div className="decision-confirm"><ClipboardCheck size={18} /><div><b>{humanDecision}</b><span>Recorded locally for the {currentScenario.label} preset in this mock walkthrough.</span></div></div>}</Panel>
    <Panel className="brief-evidence" title="Why this stays inspectable"><div className="brief-evidence-row"><FileCheck2 size={20} /><div><b>Evidence can be reopened</b><span>{data.evidence.filter((item) => item.quoteMatched).length} of {data.evidence.length} contract values remain linked to a source quote and page.</span></div><button type="button" onClick={onEvidenceStack}>Stack</button></div><div className="brief-evidence-row"><CircleDollarSign size={20} /><div><b>Metrics are injected</b><span>The brief references computed metric IDs ({data.brief.metricRefs.join(", ")}), never free-form numbers.</span></div><button type="button" onClick={() => onFormula(recommended)}>TCO</button></div><div className="brief-evidence-row"><CircleHelp size={20} /><div><b>Recommendation is constrained</b><span>{recommended} is an existing option, not an invented fourth choice. Matrix inspection: {selectedOption}.</span></div><button type="button" onClick={() => onStageChange("matrix")}>Matrix</button></div></Panel>
  </div>;
}

export function StageView(props: StageProps) {
  if (props.appState === "no-feasible") return <div className="stage-content"><PageIntro stage={props.stage} appState={props.appState} onPreviewState={props.onPreviewState} /><Panel className="no-feasible-panel" title="No feasible option"><div role="status"><h2>No recommendation is available.</h2><p>This local preview shows a result where no option passed the required constraints. Approval remains unavailable; review the constraints or change assumptions before requesting a new simulation.</p></div><div className="button-row"><button className="button primary" disabled type="button">Approve unavailable</button><GhostButton onClick={() => { props.onPreviewState("ready"); props.onStageChange("scenario"); }}>Review assumptions</GhostButton><GhostButton onClick={() => props.onPreviewState("ready")}>Restore local state</GhostButton></div></Panel></div>;

  if (props.appState === "loading" || props.appState === "empty" || props.appState === "error") {
    return <StatePreview stage={props.stage} state={props.appState} onPreviewState={props.onPreviewState} onGolden={props.onGoldenRun} />;
  }
  let view;
  if (props.stage === "intake") view = <IntakeView data={props.data} onNext={props.onNext} onEvidence={props.onEvidence} />;
  else if (props.stage === "scenario") view = <ScenarioView data={props.data} scenarioId={props.scenarioId} currentScenario={props.currentScenario} demandShift={props.demandShift} riskThreshold={props.riskThreshold} isDraft={props.isDraft} onScenarioChange={props.onScenarioChange} onDemandShiftChange={props.onDemandShiftChange} onRiskThresholdChange={props.onRiskThresholdChange} onNext={props.onNext} onEvidence={props.onEvidence} onStageChange={props.onStageChange} />;
  else if (props.stage === "matrix") view = <MatrixView data={props.data} scenarioId={props.scenarioId} currentScenario={props.currentScenario} demandShift={props.demandShift} riskThreshold={props.riskThreshold} isDraft={props.isDraft} selectedOption={props.selectedOption} onOptionSelect={props.onOptionSelect} onFormula={props.onFormula} onNext={props.onNext} />;
  else if (props.stage === "boardroom") view = <BoardroomView data={props.data} onEvidence={props.onEvidence} onNext={props.onNext} />;
  else view = <BriefView data={props.data} scenarioId={props.scenarioId} currentScenario={props.currentScenario} demandShift={props.demandShift} riskThreshold={props.riskThreshold} isDraft={props.isDraft} selectedOption={props.selectedOption} humanDecision={props.humanDecision} onFormula={props.onFormula} onEvidenceStack={props.onEvidenceStack} onDecision={props.onDecision} onStageChange={props.onStageChange} />;
  return <div className="stage-content"><PageIntro stage={props.stage} appState={props.appState} onPreviewState={props.onPreviewState} />{view}<ContextDeck stage={props.stage} data={props.data} scenarioId={props.scenarioId} onEvidence={props.onEvidence} onFormula={props.onFormula} onStageChange={props.onStageChange} /></div>;
}

