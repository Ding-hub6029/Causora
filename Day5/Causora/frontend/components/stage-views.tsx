import { AnimatePresence, motion } from "framer-motion";
import { BadgeCheck, Boxes, BrainCircuit, Check, ChevronDown, CircleDollarSign, CircleHelp, ClipboardCheck, Database, FileCheck2, FileText, GitCompareArrows, Info, LockKeyhole, RotateCcw, Scale, SearchCheck, Settings2, SlidersHorizontal, Telescope, TriangleAlert, Upload, X } from "lucide-react";
import { useState } from "react";
import type { OptionId } from "@/lib/contracts";
import type { AppState, Evidence, LiveSimulation, MockData, StageId } from "@/lib/types";
import type { BoardroomState } from "@/lib/day4-types";
import { isCurrentBoardroomRun } from "@/lib/boardroom-api";
import { decisionDelta, displayMatrixTone, money, percent, renderGuarded, signedMoney, signedPercent, signedPp } from "@/lib/metrics";
import { GhostButton, Metric, Panel, PrimaryButton, SectionLabel, StateCard, StatusChip, TraceLink } from "./ui";
import { ContextDeck } from "./context-deck";
import { LiveBoardroomView, LiveBriefView } from "./live-downstream-views";

type StageProps = {
  stage: StageId;
  appState: AppState;
  data: MockData;
  currentScenario: MockData["scenarios"][number];
  scenarioId: string;
  matrixScenarioId: string;
  decisionScenarioId: string;
  demandShift: number;
  riskThreshold: number;
  budgetCeilingUsd: number;
  isDraft: boolean;
  datasetId: string;
  liveRun: LiveSimulation | null;
  isSimulating: boolean;
  serviceReady: boolean;
  simulationError: string | null;
  boardroomState: BoardroomState;
  canRecordDecision: boolean;
  hasVerifiedGolden: boolean;
  cachedGoldenActive: boolean;
  goldenCacheError: string | null;
  selectedOption: OptionId;
  humanDecision: string | null;
  onScenarioChange: (id: string) => void;
  onDemandShiftChange: (value: number) => void;
  onRiskThresholdChange: (value: number) => void;
  onBudgetCeilingChange: (value: number) => void;
  onRunSimulation: () => void;
  onRunBoardroom: () => void;
  onRetryBoardroom: () => void;
  onOptionSelect: (id: OptionId) => void;
  onEvidence: (evidence: Evidence) => void;
  onLiveEvidence: (evidenceId: string) => void;
  onEvidenceStack: () => void;
  onFormula: (optionId?: OptionId, scenarioId?: string) => void;
  onNext: () => void;
  onPreviewState: (state: AppState) => void;
  onGoldenRun: () => void;
  onOpenVerifiedGolden: () => void;
  onExportVerifiedGolden: () => void;
  onDecision: (decision: string) => void;
  onStageChange: (stage: StageId) => void;
  onScenarioView: (id: string) => void;
};

const stageCopy: Record<StageId, { number: string; kicker: string; title: string; body: string }> = {
  intake: { number: "01", kicker: "Source-linked starting point", title: "Bring the record into focus.", body: "A deliberate decision begins with the files you can inspect, not a generated summary you cannot." },
  scenario: { number: "02", kicker: "External world, explicit", title: "Separate uncertainty from control.", body: "Scenarios describe what happens to you. Options describe what you can do about it." },
  matrix: { number: "03", kicker: "Code-bound comparison", title: "See the trade-off before the story.", body: "Every matrix cell represents a predefined option under one explicit external scenario." },
  boardroom: { number: "04", kicker: "Independent viewpoints", title: "Invite challenge into the room.", body: "Each perspective sees only its permitted decision surface. The Critic connects what they miss alone." },
  brief: { number: "05", kicker: "Human decision", title: "A recommendation ready for challenge.", body: "A formal decision requires a reviewed simulation and the matching Boardroom response." }
};

function PageIntro({ stage, appState, onPreviewState, liveRun = null, boardroomState, scenarioId }: { stage: StageId; appState: AppState; onPreviewState: (state: AppState) => void; liveRun?: LiveSimulation | null; boardroomState?: BoardroomState; scenarioId?: string }) {
  const matchingReview = !!liveRun && boardroomState?.status === "ready" && !!scenarioId && isCurrentBoardroomRun(boardroomState.run, liveRun, scenarioId);
  const baseCopy = stage === "brief" && liveRun
    ? { ...stageCopy.brief, ...(liveRun.integrationMode === "unreviewed-v2-dev"
      ? { title: "Development results are not ready for a decision brief.", body: "These Monte Carlo results are unreviewed development data. They cannot support a formal recommendation or approval." }
      : matchingReview
      ? { title: "Review the matching decision brief.", body: "The simulation, Boardroom and Critic are validated for this exact run. The final choice remains under human control and is recorded only in this browser." }
      : { title: "Waiting for the matching Boardroom response.", body: "The simulation is available. A decision brief remains unavailable until its analysis is linked to this exact run." }) }
    : stageCopy[stage];
  const copy = appState === "no-feasible" ? { ...baseCopy, title: "No option passes the constraints.", body: "A recommendation requires a feasible option. Review the assumptions before requesting a new comparison." } : baseCopy;
  return <div className="page-intro">
    <div><SectionLabel index={copy.number} label={copy.kicker} /><h1>{copy.title}</h1><p>{copy.body}</p></div>
    {!liveRun && <div className="state-studio" aria-label="Preview prototype UI states">
      <span><Settings2 size={14} />State studio</span>
      <div>
        {(["loading", "empty", "error", "no-feasible"] as const).map((state) => <button key={state} type="button" className={appState === state ? "selected" : ""} aria-pressed={appState === state} onClick={() => onPreviewState(state)}>{state === "no-feasible" ? "No feasible option" : state}</button>)}
      </div>
    </div>}
  </div>;
}

function StatePreview({ stage, state, onPreviewState, onGolden }: { stage: StageId; state: "loading" | "empty" | "error"; onPreviewState: (state: AppState) => void; onGolden: () => void }) {
  return <div className="stage-content"><PageIntro stage={stage} appState={state} onPreviewState={onPreviewState} /><Panel className="state-preview-panel"><StateCard stage={stageCopy[stage].title.split(".")[0]} state={state} /><div className="state-actions"><div><small>LOCAL RESILIENCE PREVIEW</small><h2>Graceful degradation is part of the product.</h2><p>The active stage intentionally shows its {state} state. No data has left this browser. You can switch to another preview state, restore the local dataset, or load the saved example (not a live or verified E2E run).</p></div><div className="button-row"><GhostButton onClick={() => onPreviewState("ready")}><RotateCcw size={15} />Restore local state</GhostButton><PrimaryButton onClick={onGolden}>Load saved example</PrimaryButton></div></div></Panel></div>;
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
    <Panel className="file-register" title="Import register" action={<StatusChip tone="signal">LOCAL MOCK FILES</StatusChip>}>
      <div className="register-head"><span>Source file</span><span>Footprint</span><span>State</span></div>
      {data.intake.map((file) => <div className="register-row" key={file.id}><div><a href={file.path} target="_blank" rel="noopener noreferrer" aria-label={`Open synthetic ${file.label} file`}>{file.label}</a><small>{file.type} · {file.size}</small></div><span>{file.detail}</span><StatusChip tone={file.status === "Matched" ? "signal" : "success"}>{file.status}</StatusChip></div>)}
      <div className="integrity-band"><SearchCheck size={18} /><span><b>Input integrity is explicit.</b> The contract is machine-readable; the remaining inputs are local structured files.</span></div>
    </Panel>
    <Panel className="intake-evidence-card" title="The first matched clause">
      <div className="evidence-mini"><span className="evidence-id">{first.id}</span><strong>{first.extractedValue}</strong><p>{first.quote}</p><TraceLink kind="evidence" onClick={() => onEvidence(first)}>Open source quote</TraceLink></div>
    </Panel>
  </div>;
}

function ScenarioView({ data, scenarioId, currentScenario, demandShift, riskThreshold, budgetCeilingUsd, isDraft, serviceReady, cachedGoldenActive, onScenarioChange, onDemandShiftChange, onRiskThresholdChange, onBudgetCeilingChange, onNext, onEvidence, onStageChange }: Pick<StageProps, "data" | "scenarioId" | "currentScenario" | "demandShift" | "riskThreshold" | "budgetCeilingUsd" | "isDraft" | "serviceReady" | "cachedGoldenActive" | "onScenarioChange" | "onDemandShiftChange" | "onRiskThresholdChange" | "onBudgetCeilingChange" | "onNext" | "onEvidence" | "onStageChange">) {
  const minShare = data.evidence.find((item) => item.id === "EV-024")?.extractedValue ?? percent(data.contract.minPurchaseShareA);
  return <div className="stage-grid scenario-grid">
    <Panel className="scenario-control" title="Choose an external scenario" action={<StatusChip tone={cachedGoldenActive || serviceReady ? "success" : "warning"}>{cachedGoldenActive ? "VERIFIED GOLDEN · READ-ONLY" : serviceReady ? "LIVE API READY" : "PUBLIC API NOT READY"}</StatusChip>}>
      <div className="scenario-day2-notice" role="note">
        <Info size={17} />
        <div><strong>{cachedGoldenActive ? "The verified snapshot is read-only." : "Set assumptions, then run the comparison."}</strong><p>{cachedGoldenActive ? "Changing an input exits the frozen Golden replay. This page never changes the stored run; a new live result requires a ready public backend." : serviceReady ? "The controls edit a draft. The Matrix stays on its labelled example until a successful, validated POST /api/simulate response arrives." : "The controls edit a draft only. No public simulation backend is ready, so the Matrix remains a clearly labelled saved example and no live result will be computed."}</p></div>
      </div>
      <div className="scenario-axis-key" aria-label="Difference between a scenario and a decision option">
        <div><small>SCENARIO · OUTSIDE YOUR CONTROL</small><strong>What might happen?</strong><p>Demand and supplier lead-time conditions describe the external world.</p></div>
        <div><small>DECISION OPTION · YOUR CHOICE</small><strong>What can the business do?</strong><p>D0, D1, and D2 are the same controllable choices compared in every scenario.</p></div>
      </div>
      <div className="scenario-tabs" role="tablist" aria-label="Select scenario">{data.scenarios.map((scenario) => <button key={scenario.id} type="button" role="tab" aria-selected={scenarioId === scenario.id} onClick={() => onScenarioChange(scenario.id)} className={scenarioId === scenario.id ? "active" : ""}><span>{scenario.label}</span><small>{scenario.tag}</small></button>)}</div>
      <div className="scenario-focus"><div><small>SELECTED EXTERNAL WORLD</small><h2>{currentScenario.label}</h2><p>{currentScenario.description}</p></div><div className="scenario-signal"><Telescope size={22} /><span>External<br />only</span></div></div>
      <div className="slider-stack">
        <label><span>Demand shock <b>{signedPercent(demandShift)}</b></span><input aria-label="Demand shock" type="range" min="-20" max="10" value={demandShift} onChange={(event) => onDemandShiftChange(Number(event.target.value))} /><small>Whole-percent scenario input; sent as demandShock and rescaled 24-month units.</small></label>
        <label><span>Stockout risk cap <b>{riskThreshold}%</b></span><input aria-label="Stockout risk threshold" type="range" min="4" max="25" value={riskThreshold} onChange={(event) => onRiskThresholdChange(Number(event.target.value))} /><small>Displayed as percent; sent to v1 as a decimal fraction for per-scenario selection.</small></label>
        <label><span>Cash ceiling <b>{money(budgetCeilingUsd)}</b></span><input aria-label="Cash budget ceiling in USD" type="number" min="0" step="1000" value={budgetCeilingUsd} onChange={(event) => onBudgetCeilingChange(Number(event.target.value))} /><small>Whole USD, sent as budgetCeilingUsd. $480,000 is the existing v1 demo request value.</small></label>
      </div>
      <div className="assumption-disclosure"><Info size={15} /><span>Changes are not results: request a new simulation to replace the saved Day 2 example. A live response is accepted only after schema, matrix, cost-sum, Decision Delta and constraint-selection checks pass.</span></div>
      {isDraft && <button type="button" className="assumption-reset" onClick={() => { onDemandShiftChange(currentScenario.demandShock); onRiskThresholdChange(12); onBudgetCeilingChange(480000); }}><RotateCcw size={14} />Restore preset request inputs</button>}
      <div className="button-row"><GhostButton onClick={() => onStageChange("intake")}>Back to inputs</GhostButton><PrimaryButton onClick={onNext}>Next: compare the three choices</PrimaryButton></div>
    </Panel>
    <Panel className="variable-panel" title="Evidence → Business Variables" action={<span className="code-tag">{data.variables.length} QUOTE-MATCHED</span>}>
      {data.variables.map((variable, index) => <motion.div className="variable-row" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.06 }} key={variable.key}><div><b>{variable.name}</b><small>{renderGuarded(variable.meaning, data)}</small><small className="variable-inputs">Inputs: {variable.inputs.map((input) => `${input.name} = ${input.value}`).join(" · ")}</small></div><div><strong>{variable.value}</strong><button type="button" onClick={() => { const evidence = data.evidence.find((item) => item.id === variable.source); if (evidence) onEvidence(evidence); }}>{variable.source}</button></div></motion.div>)}
      <div className="evidence-scope-note"><Info size={14} /><span>“Quote-matched” refers only to a value in this synthetic source. It does not verify real-world notice history or legal interpretation.</span></div><div className="rule-note"><Scale size={16} /><span><b>Constraint rule (synthetic register assumption):</b> notice deadline {data.contract.noticeDeadline} passed with no written notice on record ({data.contract.daysToRenewal} days to renewal &lt; {data.contract.renewalNoticeDays}-day window), so D1 must keep {minShare} with A and D2 must carry the {money(data.contract.terminationFeeUsd)} termination cost. <a href="/demo/supplier_correspondence_log.csv" target="_blank" rel="noopener noreferrer">Inspect mock notice register</a>.</span></div>
    </Panel>
    <Panel className="option-principle" title="Decision options · controllable choices">
      <p className="option-principle-lead">These three choices stay the same when the external scenario changes. Compare them in the Matrix; selecting a scenario does not select an option.</p>
      <div className="scenario-option-list">{data.options.map((option) => <article className="scenario-option-card" key={option.id}><div className="scenario-option-heading"><strong>{option.id === "D0" ? "Keep the current supplier" : option.id === "D1" ? "Keep the minimum with A, diversify to B" : "Exit A and switch to B"}</strong><span>{option.id}</span></div><small>{option.allocation}</small><p>{option.id === "D0" ? "Keep the current allocation with Supplier A; do not exit the agreement." : option.id === "D1" ? `Keep ${minShare} with A and diversify the remaining volume to B.` : `Exit the renewed A agreement and include the ${money(data.contract.terminationFeeUsd)} termination fee in this mock case.`}</p></article>)}</div>
      <div className="option-principle-footer"><b>Quick check:</b> scenario = outside condition; option = business action.</div>
    </Panel>
  </div>;
}

function MatrixView({ data, currentScenario, matrixScenarioId, demandShift, riskThreshold, budgetCeilingUsd, isDraft, datasetId, liveRun, cachedGoldenActive, isSimulating, serviceReady, simulationError, appState, selectedOption, onScenarioView, onOptionSelect, onFormula, onNext, onRunSimulation }: Pick<StageProps, "data" | "currentScenario" | "matrixScenarioId" | "demandShift" | "riskThreshold" | "budgetCeilingUsd" | "isDraft" | "datasetId" | "liveRun" | "cachedGoldenActive" | "isSimulating" | "serviceReady" | "simulationError" | "appState" | "selectedOption" | "onScenarioView" | "onOptionSelect" | "onFormula" | "onNext" | "onRunSimulation">) {
  const simulation = liveRun?.response.data.simulation ?? data.simulation;
  const matrixScenario = data.scenarios.find((scenario) => scenario.id === matrixScenarioId) ?? data.scenarios[0];
  const selection = liveRun?.response.data.selections[matrixScenarioId];
  const isUnreviewedDev = liveRun?.integrationMode === "unreviewed-v2-dev";
  const activeRow = simulation.matrix[matrixScenarioId] ?? [];
  const selectedMetrics = activeRow.find((row) => row.optionId === selectedOption);
  const selectedDelta = liveRun?.response.data.deltas.find((delta) => delta.scenarioId === matrixScenarioId && delta.optionId === selectedOption);
  const selectedChoice = selection?.status === "selected" ? selection.recommendedOptionId : null;
  return <div className="stage-grid matrix-grid">
    <Panel className="matrix-panel">
      <div className="matrix-header"><div><small>OPTION × SCENARIO MATRIX</small><h2>{matrixScenario.label}<span>{liveRun ? ` / ${simulation.monteCarloRuns.toLocaleString("en-US")} Monte Carlo runs` : " / saved Day 2 example"}</span></h2></div><StatusChip tone={isUnreviewedDev || (!liveRun && !cachedGoldenActive) ? "warning" : "success"}>{cachedGoldenActive ? "CACHED · VERIFIED GOLDEN · READ-ONLY" : isUnreviewedDev ? "UNREVIEWED DEV · NOT DECISION-READY" : liveRun ? `LIVE API · ${simulation.weeks} WEEKS` : "SAVED VALUES · NOT COMPUTED"}</StatusChip></div>
      {isDraft && <div className="matrix-draft-note"><Info size={15} /><span>Draft assumptions: demand {signedPercent(demandShift)} · risk cap {riskThreshold}% · cash ceiling {money(budgetCeilingUsd)}. The saved example below is not a result for this draft; run the API request before using its numbers.</span></div>}
      {simulationError && <div className="simulation-error" role="alert"><TriangleAlert size={16} /><span><b>Live simulation was not applied.</b> {simulationError} {liveRun ? "The previous validated live 3×3 Matrix and Formula Trace remain visible; the failed request did not replace them." : "The 3×3 grid below remains the saved Day 2 example and is not a substitute for the draft result."}</span></div>}
      <div className="matrix-run-controls"><div><small>{cachedGoldenActive ? "STORED REQUEST · READ-ONLY" : "REQUEST"}</small><b>POST /api/simulate</b><span>input scenario {currentScenario.label} · dataset {datasetId} · seed {data.meta.seed} · risk {percent(riskThreshold / 100)} · cash {money(budgetCeilingUsd)}</span></div><PrimaryButton onClick={onRunSimulation} disabled={!serviceReady || isSimulating || appState === "golden"}>{isSimulating ? "Running simulation…" : appState === "golden" || cachedGoldenActive ? "Golden Run is read-only" : serviceReady ? "Run simulation" : process.env.NEXT_PUBLIC_CAUSORA_STATIC_ONLY === "true" ? "Public backend not configured" : "Waiting for /health"}</PrimaryButton></div>
      <div className="matrix-table matrix-live-table" role="table" aria-label={isUnreviewedDev ? "Unreviewed development-only option scenario matrix" : cachedGoldenActive ? "Verified Golden option scenario matrix" : liveRun ? "Live option scenario matrix" : "Saved Day 2 option scenario example"}>
        <div className="matrix-live-head" role="row"><span>Scenario</span>{data.options.map((option) => <span key={option.id}><b>{option.id}</b><small>{option.label}</small></span>)}</div>
        {data.scenarios.map((scenario) => {
          const rows = simulation.matrix[scenario.id] ?? [];
          const scenarioSelection = liveRun?.response.data.selections[scenario.id];
          return <div className="matrix-live-row" role="row" key={scenario.id}>
            <button type="button" className={`matrix-scenario-select ${matrixScenarioId === scenario.id ? "selected" : ""}`} onClick={() => onScenarioView(scenario.id)} aria-pressed={matrixScenarioId === scenario.id}><b>{scenario.label}</b><small>{scenario.tag}</small></button>
            {data.options.map((option) => {
              const metrics = rows.find((row) => row.optionId === option.id);
              if (!metrics) return <span key={option.id} className="matrix-live-cell missing">No cell</span>;
              const active = matrixScenarioId === scenario.id && selectedOption === option.id;
              const devCandidate = isUnreviewedDev && scenarioSelection?.status === "selected" && scenarioSelection.recommendedOptionId === option.id;
              const recommended = liveRun ? !isUnreviewedDev && scenarioSelection?.status === "selected" && scenarioSelection.recommendedOptionId === option.id : metrics.tone === "recommended";
              const displayTone = isUnreviewedDev ? (metrics.tone === "risk" ? "risk" : "neutral") : displayMatrixTone(metrics, liveRun ? scenarioSelection : undefined);
              return <button key={option.id} type="button" className={`matrix-live-cell ${displayTone} ${active ? "selected" : ""}`} onClick={() => { onScenarioView(scenario.id); onOptionSelect(option.id); }} aria-pressed={active}>
                <b>{money(metrics.expectedTco)}</b><small>Stockout {percent(metrics.stockoutProbability)} · P90 {money(metrics.cashOutflowP90)}</small>
                {recommended && <em>{cachedGoldenActive ? "Stored selection" : liveRun ? "Selected" : "Day 2 example"}</em>}
                {devCandidate && <em>Constraint screen · not a recommendation</em>}
                {liveRun && !metrics.feasible && <i>Infeasible</i>}
              </button>;
            })}
          </div>;
        })}
      </div>
      <div className="matrix-footer"><div><Info size={15} />{cachedGoldenActive && liveRun ? `Frozen Golden response ${liveRun.response.requestId} · ${simulation.dataVersion} · formula ${simulation.formulaVersion} · no API call was made.` : liveRun ? `Server response ${liveRun.response.requestId} · ${simulation.dataVersion} · formula ${simulation.formulaVersion}.` : "Saved Day 2 values only. A successful, validated API response replaces all nine cells; failed requests never relabel the example."}</div><TraceLink onClick={() => onFormula(selectedOption, matrixScenarioId)}>Open Formula Trace for {selectedOption}</TraceLink></div>
    </Panel>
    <Panel className="option-inspector" title="Selected option">
      {(() => { const option = data.options.find((item) => item.id === selectedOption) ?? data.options[1]; const metrics = selectedMetrics; return <><div className="inspector-option"><span>{option.id}</span><div><h3>{option.label}</h3><p>{option.description}</p></div></div><div className="metric-row"><Metric label="Expected TCO" value={metrics ? money(metrics.expectedTco) : "—"} tone="lime" /><Metric label="Stockout" value={metrics ? percent(metrics.stockoutProbability) : "—"} tone="blue" /></div><div className="decision-logic"><GitCompareArrows size={18} /><p><b>{isUnreviewedDev ? "UNREVIEWED development constraint screen:" : liveRun ? "API selection:" : "Saved example:"}</b> {liveRun ? isUnreviewedDev ? selection?.status === "selected" ? `${selectedChoice} passes the current development constraints for ${matrixScenario.label}; this is not a reviewed recommendation.` : "No option passes the development constraints for this scenario; no candidate is shown." : selection?.status === "selected" ? `${selectedChoice} is selected for ${matrixScenario.label} after feasibility, ${riskThreshold}% risk and ${money(budgetCeilingUsd)} cash-ceiling checks.` : "No option passes all constraints for this scenario; there is no winner." : isDraft ? `The ${riskThreshold}% draft risk cap and ${money(budgetCeilingUsd)} cash ceiling have not been evaluated; “Day 2 example” markers are unchanged.` : "This saved example is illustrative; it is not a live simulation result."}</p></div>{liveRun && selectedDelta && <div className="live-delta-strip"><b>{selectedOption} − D0</b><span>TCO {signedMoney(selectedDelta.deltaTco)}</span><span>Stockout {signedPp(selectedDelta.deltaStockoutPp)}</span><span>Service {signedPp(selectedDelta.deltaServicePp)}</span><span>P90 {signedMoney(selectedDelta.deltaCashP90)}</span></div>}</>; })()}
      <div className="button-row"><GhostButton onClick={() => onFormula(selectedOption, matrixScenarioId)}>Inspect {selectedOption} formulas</GhostButton><PrimaryButton onClick={onNext}>{cachedGoldenActive ? "Open verified Boardroom snapshot" : liveRun ? "Open live Boardroom" : "Open saved Boardroom example"}</PrimaryButton></div>
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

function BriefView({ data, scenarioId, currentScenario, demandShift, riskThreshold, isDraft, selectedOption, humanDecision, onFormula, onEvidenceStack, onStageChange }: Pick<StageProps, "data" | "scenarioId" | "currentScenario" | "demandShift" | "riskThreshold" | "isDraft" | "selectedOption" | "humanDecision" | "onFormula" | "onEvidenceStack" | "onStageChange">) {
  const recommended = data.brief.recommendedOptionId;
  const delta = decisionDelta(data, scenarioId, recommended, "D0");
  const deltas = [
    { label: "Expected 24m TCO", value: signedMoney(delta.deltaTco) },
    { label: "Stockout probability", value: signedPp(delta.deltaStockoutPp) },
    { label: "P90 cash outflow", value: signedMoney(delta.deltaCashP90) }
  ];
  const minShare = data.evidence.find((item) => item.id === "EV-024");
  return <div className="stage-grid brief-grid">
    <Panel className="recommendation-card"><div className="brief-top"><div><small>DECISION BRIEF / {currentScenario.label.toUpperCase()} MOCK RUN</small><StatusChip tone="signal">PRESET MOCK RECOMMENDATION</StatusChip></div><span className="brief-id">{recommended}</span></div><h2>{data.brief.recommendation}</h2><p>{data.brief.rationale}</p><div className="brief-guardrail"><LockKeyhole size={16} /><span>{data.brief.guardrail}</span></div>{isDraft && <div className="brief-draft-warning" role="status"><TriangleAlert size={16} /><span><b>Approval basis: the {currentScenario.label} preset only.</b> Your draft assumptions (demand {signedPercent(demandShift)}, threshold {riskThreshold}%) have not been simulated and are not reflected in these numbers.</span></div>}<div className="delta-grid">{deltas.map((item, index) => <Metric key={item.label} label={item.label} value={item.value} detail={`${recommended} vs. D0 in ${currentScenario.label} mock run`} tone={index === 0 ? "lime" : "light"} />)}</div><div className="button-row"><TraceLink onClick={() => onFormula(recommended)}>Formula Trace · {recommended}</TraceLink><TraceLink kind="evidence" onClick={onEvidenceStack}>Evidence stack · {data.evidence.length}</TraceLink></div><div className="brief-proof-strip"><div><small>01 / SOURCE</small><b>{minShare?.id ?? "EV-024"}</b><span>{minShare?.extractedValue ?? ""} minimum share</span></div><div><small>02 / OPTION</small><b>{recommended}</b><span>Preset mock comparison</span></div><div><small>03 / AUTHORITY</small><b>Human reviewer</b><span>No external action</span></div></div></Panel>
    <Panel className="human-control" title="Human decision control"><div className="human-portrait"><span>H</span><div><small>HUMAN REVIEW REQUIRED</small><h3>You retain the final call.</h3></div></div><p>This is a saved Day 2 example, not a live Simulation/Boardroom run. Approve and Reject remain unavailable; no choice can be recorded against a mock recommendation.</p><div className="decision-buttons"><button type="button" className="approve" disabled title="A live reviewed Simulation and matching Boardroom response are required"><Check size={17} />Approval unavailable · saved example</button><button type="button" className="reject" disabled><X size={17} />Rejection unavailable · saved example</button><button type="button" className="change" onClick={() => onStageChange("scenario")}><SlidersHorizontal size={17} />Change assumptions</button></div>{humanDecision && <div className="decision-confirm"><ClipboardCheck size={18} /><div><b>{humanDecision}</b><span>Recorded locally for the {currentScenario.label} preset in this mock walkthrough.</span></div></div>}</Panel>
    <Panel className="brief-evidence" title="Why this stays inspectable"><div className="brief-evidence-row"><FileCheck2 size={20} /><div><b>Evidence can be reopened</b><span>{data.evidence.filter((item) => item.quoteMatched).length} of {data.evidence.length} contract values remain linked to a source quote and page.</span></div><button type="button" onClick={onEvidenceStack}>Stack</button></div><div className="brief-evidence-row"><CircleDollarSign size={20} /><div><b>Preset metrics are linked</b><span>The brief references mock metric IDs ({data.brief.metricRefs.join(", ")}), never free-form numbers.</span></div><button type="button" onClick={() => onFormula(recommended)}>TCO</button></div><div className="brief-evidence-row"><CircleHelp size={20} /><div><b>Recommendation is constrained</b><span>{recommended} is an existing option, not an invented fourth choice. Matrix inspection: {selectedOption}.</span></div><button type="button" onClick={() => onStageChange("matrix")}>Matrix</button></div></Panel>
  </div>;
}

export function StageView(props: StageProps) {
  if (props.liveRun && props.stage === "boardroom") return <div className="stage-content"><PageIntro stage={props.stage} appState={props.appState} onPreviewState={props.onPreviewState} liveRun={props.liveRun} /><LiveBoardroomView readOnlySnapshot={props.cachedGoldenActive} liveRun={props.liveRun} scenarioId={props.decisionScenarioId} state={props.boardroomState} onRun={props.onRunBoardroom} onRetry={props.onRetryBoardroom} onLiveEvidence={props.onLiveEvidence} onNext={props.onNext} /></div>;
  if (props.liveRun && props.stage === "brief") return <div className="stage-content"><PageIntro stage={props.stage} appState={props.appState} onPreviewState={props.onPreviewState} liveRun={props.liveRun} boardroomState={props.boardroomState} scenarioId={props.decisionScenarioId} /><LiveBriefView onExportVerifiedGolden={props.onExportVerifiedGolden} readOnlySnapshot={props.cachedGoldenActive} liveRun={props.liveRun} scenarioId={props.decisionScenarioId} state={props.boardroomState} canRecordDecision={props.canRecordDecision} humanDecision={props.humanDecision} hasVerifiedGolden={props.hasVerifiedGolden} goldenCacheError={props.goldenCacheError} onRun={props.onRunBoardroom} onRetry={props.onRetryBoardroom} onFormula={props.onFormula} onLiveEvidence={props.onLiveEvidence} onDecision={props.onDecision} onStageChange={props.onStageChange} onOpenVerifiedGolden={props.onOpenVerifiedGolden} /></div>;

  if (!props.liveRun && props.appState === "no-feasible") return <div className="stage-content"><PageIntro stage={props.stage} appState={props.appState} onPreviewState={props.onPreviewState} /><Panel className="no-feasible-panel" title="No feasible option"><div role="status"><h2>No recommendation is available.</h2><p>This local preview shows a result where no option passed the required constraints. Approval remains unavailable; review the constraints or change assumptions before requesting a new simulation.</p></div><div className="button-row"><button className="button primary" disabled type="button">Approve unavailable</button><GhostButton onClick={() => { props.onPreviewState("ready"); props.onStageChange("scenario"); }}>Review assumptions</GhostButton><GhostButton onClick={() => props.onPreviewState("ready")}>Restore local state</GhostButton></div></Panel></div>;

  if (!props.liveRun && (props.appState === "loading" || props.appState === "empty" || props.appState === "error")) {
    return <StatePreview stage={props.stage} state={props.appState} onPreviewState={props.onPreviewState} onGolden={props.onGoldenRun} />;
  }

  const traceScenarioId = props.stage === "matrix" ? props.matrixScenarioId : props.scenarioId;
  let view;
  if (props.stage === "intake") view = <IntakeView data={props.data} onNext={props.onNext} onEvidence={props.onEvidence} />;
  else if (props.stage === "scenario") view = <ScenarioView data={props.data} scenarioId={props.scenarioId} currentScenario={props.currentScenario} demandShift={props.demandShift} riskThreshold={props.riskThreshold} budgetCeilingUsd={props.budgetCeilingUsd} isDraft={props.isDraft} serviceReady={props.serviceReady} cachedGoldenActive={props.cachedGoldenActive} onScenarioChange={props.onScenarioChange} onDemandShiftChange={props.onDemandShiftChange} onRiskThresholdChange={props.onRiskThresholdChange} onBudgetCeilingChange={props.onBudgetCeilingChange} onNext={props.onNext} onEvidence={props.onEvidence} onStageChange={props.onStageChange} />;
  else if (props.stage === "matrix") view = <MatrixView data={props.data} currentScenario={props.currentScenario} matrixScenarioId={props.matrixScenarioId} demandShift={props.demandShift} riskThreshold={props.riskThreshold} budgetCeilingUsd={props.budgetCeilingUsd} isDraft={props.isDraft} datasetId={props.datasetId} liveRun={props.liveRun} cachedGoldenActive={props.cachedGoldenActive} isSimulating={props.isSimulating} serviceReady={props.serviceReady} simulationError={props.simulationError} appState={props.appState} selectedOption={props.selectedOption} onScenarioView={props.onScenarioView} onOptionSelect={props.onOptionSelect} onFormula={props.onFormula} onNext={props.onNext} onRunSimulation={props.onRunSimulation} />;
  else if (props.stage === "boardroom") view = <BoardroomView data={props.data} onEvidence={props.onEvidence} onNext={props.onNext} />;
  else view = <BriefView data={props.data} scenarioId={props.scenarioId} currentScenario={props.currentScenario} demandShift={props.demandShift} riskThreshold={props.riskThreshold} isDraft={props.isDraft} selectedOption={props.selectedOption} humanDecision={props.humanDecision} onFormula={props.onFormula} onEvidenceStack={props.onEvidenceStack} onStageChange={props.onStageChange} />;
  return <div className="stage-content"><PageIntro stage={props.stage} appState={props.appState} onPreviewState={props.onPreviewState} liveRun={props.liveRun} />{view}{props.liveRun ? <div className="live-run-context" role="status"><b>{props.cachedGoldenActive ? "Verified Golden snapshot · read-only" : "Validated live response"}</b><span>{props.liveRun.response.data.simulation.simulationId} · {props.liveRun.response.requestId} · {props.liveRun.response.data.simulation.monteCarloRuns.toLocaleString("en-US")} runs · seed {props.liveRun.response.data.simulation.seed}</span><small>{props.cachedGoldenActive ? "Frozen, revalidated data; no API call was made." : "Downstream AI review is requested only for this exact run and scenario."}</small></div> : <ContextDeck stage={props.stage} data={props.data} scenarioId={traceScenarioId} onEvidence={props.onEvidence} onFormula={(optionId) => props.onFormula(optionId, traceScenarioId)} onStageChange={props.onStageChange} />}</div>;
}

