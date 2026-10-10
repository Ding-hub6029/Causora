import { BrainCircuit, Check, ClipboardCheck, FileCheck2, GitCompareArrows, Info, LockKeyhole, RotateCcw, TriangleAlert, X } from "lucide-react";
import { useState } from "react";
import type { OptionId } from "@/lib/contracts";
import type { BoardroomState, ValidatedBoardroomRun } from "@/lib/day4-types";
import type { LiveSimulation, StageId } from "@/lib/types";
import { isCurrentBoardroomRun } from "@/lib/boardroom-api";
import { boardroomMetricValues, renderBoardroomBody } from "@/lib/boardroom-template";
import { money, percent, signedMoney, signedPp, units } from "@/lib/metrics";
import { Metric, Panel, PrimaryButton, SectionLabel, StatusChip, TraceLink } from "./ui";

function scenarioLabel(liveRun: LiveSimulation, scenarioId: string): string {
  return liveRun.request.scenarios.find((scenario) => scenario.id === scenarioId)?.label ?? scenarioId;
}

function readyRun(state: BoardroomState, liveRun: LiveSimulation, scenarioId: string): ValidatedBoardroomRun | null {
  return state.status === "ready" && isCurrentBoardroomRun(state.run, liveRun, scenarioId) ? state.run : null;
}

function boundOption(liveRun: LiveSimulation, optionId: OptionId) {
  return liveRun.request.options.find((option) => option.id === optionId);
}

function BoundSimulationIdentity({ liveRun, scenarioId, boardroom }: { liveRun: LiveSimulation; scenarioId: string; boardroom?: ValidatedBoardroomRun | null }) {
  const simulation = liveRun.response.data.simulation;
  return <div className="day4-run-identity" aria-label="Current simulation identity">
    <span>Simulation <b>{simulation.simulationId}</b></span>
    <span>Data version <b>{simulation.dataVersion}</b></span>
    <span>Scenario <b>{scenarioId}</b></span>
    <span>Simulation request <b>{liveRun.response.requestId}</b></span>
    {boardroom && <span>Boardroom request <b>{boardroom.requestId}</b></span>}
    <span>Mode <b>{liveRun.integrationMode === "reviewed-v2" ? "reviewed-release-gated" : liveRun.integrationMode === "unreviewed-v2-dev" ? "unreviewed-development-only" : "v1"}</b></span>
  </div>;
}

function SimulationSummary({ liveRun, scenarioId, readOnlySnapshot = false }: { liveRun: LiveSimulation; scenarioId: string; readOnlySnapshot?: boolean }) {
  const scenario = scenarioLabel(liveRun, scenarioId);
  const selection = liveRun.response.data.selections[scenarioId];
  const rows = liveRun.response.data.simulation.matrix[scenarioId] ?? [];
  return <section className="downstream-simulation-summary" aria-label="Simulation summary retained for this downstream stage">
    <div className="downstream-summary-head"><div><small>{readOnlySnapshot ? "BOUND TO FROZEN VERIFIED SIMULATION" : "BOUND TO CURRENT SIMULATION"}</small><b>{scenario}</b></div><StatusChip tone={liveRun.integrationMode === "reviewed-v2" ? "success" : "warning"}>{liveRun.integrationMode === "reviewed-v2" ? "REVIEWED V2" : liveRun.integrationMode === "unreviewed-v2-dev" ? "UNREVIEWED DEV · NOT DECISION-READY" : "V1 · NOT RELEASE-READY"}</StatusChip></div>
    <div className="downstream-summary-metrics">{rows.map((row) => <div key={row.optionId}><b>{row.optionId}</b><span>{money(row.expectedTco)}</span><small>Stockout {percent(row.stockoutProbability)} · P90 {money(row.cashOutflowP90)}</small></div>)}</div>
    <p>{selection?.status === "selected" ? `${readOnlySnapshot ? "Stored validated server selection" : "Validated server selection"}: ${selection.recommendedOptionId}. Server selection is separate from the browser-local choice.` : "No feasible option passed the current constraints; the recommendation path is blocked."}</p>
    <BoundSimulationIdentity liveRun={liveRun} scenarioId={scenarioId} />
  </section>;
}

function DownstreamFailure({ state, onRetry }: { state: Extract<BoardroomState, { status: "error" }>; onRetry: () => void }) {
  return <div className="boardroom-failure" role="alert"><div><TriangleAlert size={19} /><div><b>Boardroom unavailable · simulation preserved</b><p>{state.failure.message}</p><small>{state.failure.code.replaceAll("_", " ")}{state.failure.requestId ? ` · request ${state.failure.requestId}` : ""}</small></div></div>{state.failure.retryable ? <button type="button" onClick={onRetry}><RotateCcw size={15} />Retry Boardroom only</button> : <small>Retry is disabled for this non-retryable response.</small>}</div>;
}

export function LiveBoardroomView({ liveRun, scenarioId, state, readOnlySnapshot = false, onRun, onRetry, onLiveEvidence, onNext }: {
  liveRun: LiveSimulation;
  scenarioId: string;
  state: BoardroomState;
  readOnlySnapshot?: boolean;
  onRun: () => void;
  onRetry: () => void;
  onLiveEvidence: (evidenceId: string) => void;
  onNext: () => void;
}) {
  const label = scenarioLabel(liveRun, scenarioId);
  const selection = liveRun.response.data.selections[scenarioId];
  const isReviewed = liveRun.integrationMode === "reviewed-v2" && liveRun.development?.executionContext.decisionReady === true;
  const currentBoardroom = readyRun(state, liveRun, scenarioId);
  const dataBoardroom = currentBoardroom?.response.data;
  const metricValues = boardroomMetricValues(liveRun, scenarioId);
  const [openRoles, setOpenRoles] = useState<string[]>(["CFO", "COO", "Risk"]);

  return <div className="stage-grid day4-boardroom-grid">
    <Panel className="day4-boardroom-main">
      <div className="day4-boardroom-head"><div><SectionLabel index="04" label={readOnlySnapshot ? "Verified Golden review · read-only" : "Run-bound review"} /><h2>{readOnlySnapshot ? "Review the validated stored perspectives." : isReviewed ? "Review this validated simulation." : "The simulation is retained; formal review is gated."}</h2><p>{readOnlySnapshot ? "The Boardroom and Critic outputs are frozen records bound to this simulation identity. No AI provider is called in this replay." : isReviewed ? "The Boardroom request is bound to the current simulation ID, dataVersion, and selected scenario." : "A model narrative, Critic result, or formal brief is not created from an unreviewed or unreleased run."}</p></div><StatusChip tone={currentBoardroom ? "success" : isReviewed ? "signal" : "warning"}>{currentBoardroom ? readOnlySnapshot ? "CACHED · VERIFIED BOARDROOM" : currentBoardroom.providerMode === "same-family-fallback" ? "LIVE · SAME-FAMILY REVIEW" : "LIVE BOARDROOM · PRIMARY" : isReviewed ? "WAITING FOR BOARDROOM" : "REVIEW GATE CLOSED"}</StatusChip></div>
      <SimulationSummary liveRun={liveRun} scenarioId={scenarioId} readOnlySnapshot={readOnlySnapshot} />
      {!selection || selection.status === "no_feasible_option" ? <div className="no-feasible-panel downstream-no-feasible" role="status"><h3>No feasible option</h3><p>The validated selection contains no winner for {label}. Boardroom and Brief are not requested; review the assumptions and run a new simulation.</p></div> : null}
      {liveRun.integrationMode === "unreviewed-v2-dev" && <div className="unreviewed-dev-banner downstream-gate" role="alert"><TriangleAlert size={18} /><div><b>UNREVIEWED — DEVELOPMENT ONLY</b><span>DecisionReady=false. No approval, Critic, Synthesizer, or decision brief is permitted.</span></div></div>}
      {!isReviewed && liveRun.integrationMode !== "unreviewed-v2-dev" && <div className="downstream-gate" role="status"><LockKeyhole size={18} /><span>This {liveRun.integrationMode} response is not a reviewed, released v2 run. The formal Boardroom endpoint stays locked.</span></div>}
      {isReviewed && selection?.status === "selected" && state.status === "idle" && <div className="downstream-action"><div><b>Ready to request Boardroom</b><span>AI review does not re-run or replace the simulation.</span></div><PrimaryButton onClick={onRun}>Run Boardroom for {label}</PrimaryButton></div>}
      {isReviewed && state.status === "loading" && <div className="downstream-loading" role="status" aria-live="polite"><span className="loading-dot" /><div><b>Boardroom is running</b><span>Request {state.requestId}. Current matrix and Formula Trace stay available.</span></div></div>}
      {isReviewed && state.status === "error" && <DownstreamFailure state={state} onRetry={onRetry} />}
      {currentBoardroom && dataBoardroom && <section className="live-agent-deck" aria-label={readOnlySnapshot ? "Verified Golden stored Boardroom outputs" : "Validated live agent outputs"}>
        <div className="live-section-heading"><div><small>{readOnlySnapshot ? "VERIFIED BOARDROOM SNAPSHOT" : "VALIDATED BOARDROOM RESPONSE"}</small><h3>Three bounded perspectives</h3></div><StatusChip tone={currentBoardroom.providerMode === "same-family-fallback" ? "warning" : "success"}>{readOnlySnapshot ? `STORED PROVIDER MODE · ${currentBoardroom.providerMode.toUpperCase()}` : currentBoardroom.providerMode === "same-family-fallback" ? "SAME-FAMILY FALLBACK" : "PRIMARY PROVIDER"}</StatusChip></div>
        {dataBoardroom.agentOutputs.map((agent) => {
          const expanded = openRoles.includes(agent.role);
          return (
            <article className={`agent-card live-agent-card role-${agent.role.toLowerCase()} ${expanded ? "open" : ""}`} key={agent.role}>
              <button type="button" onClick={() => setOpenRoles((current) => current.includes(agent.role) ? current.filter((role) => role !== agent.role) : [...current, agent.role])} aria-expanded={expanded}>
                <span className="agent-top"><i>{agent.role.slice(0, 1)}</i><em>{agent.focus}</em><span className="agent-expand-indicator">{expanded ? "−" : "+"}</span></span>
                <h3>{agent.headline}</h3>
                <StatusChip tone={agent.status === "Watch" ? "warning" : "success"}>{agent.status}</StatusChip>
              </button>
              {expanded && <div className="agent-details"><p>{renderBoardroomBody(agent.body, metricValues)}</p><div className="agent-metric-refs">{agent.metrics.map((ref) => <span key={ref}>{ref}</span>)}</div></div>}
            </article>
          );
        })}
      </section>}
      {currentBoardroom && dataBoardroom && <section className="live-critic-block" aria-label={readOnlySnapshot ? "Verified Golden stored Critic issues" : "Validated live Critic issues"}><div className="live-section-heading"><div><small>{readOnlySnapshot ? "STORED CRITIC SNAPSHOT" : `CRITIC · ${currentBoardroom.criticStatus.toUpperCase()}`}</small><h3>{dataBoardroom.criticIssues.length ? "Cross-view issues" : "No Critic issues returned"}</h3></div><BrainCircuit size={20} /></div>{dataBoardroom.criticIssues.map((issue, index) => <article className="live-critic-issue" key={`${issue.severity}-${index}`}><span className="critic-severity">{issue.severity}</span><h4>{issue.headline}</h4><p>{issue.body}</p><div className="live-critic-mechanism"><span>Locked forecast <b>{units(issue.mechanism.lockedForecastUnits24m)}</b></span><span>Minimum purchase A <b>{units(issue.mechanism.minPurchaseUnitsA)}</b></span><span>Scenario demand <b>{units(issue.mechanism.scenarioDemandUnits24m)}</b></span><span>Committed excess <b>{units(issue.mechanism.committedExcessUnits)}</b></span><span>Holding Δ D0 / D1 / D2 <b>{signedMoney(issue.mechanism.holdingCostDeltaUsd.D0)} / {signedMoney(issue.mechanism.holdingCostDeltaUsd.D1)} / {signedMoney(issue.mechanism.holdingCostDeltaUsd.D2)}</b></span></div><div className="evidence-buttons">{issue.evidenceIds.map((id) => <button type="button" key={id} onClick={() => onLiveEvidence(id)}>{id} · {readOnlySnapshot ? "verified Evidence" : "live source"}</button>)}</div></article>)}</section>}
      <div className="downstream-footer"><Info size={15} /><span>{readOnlySnapshot ? "The frozen Boardroom, Critic and cited Evidence records were revalidated from the Golden snapshot. No AI or API call is made; this view is read-only." : "AI failure, timeout, unavailable Critic, or malformed Brief never clears the validated simulation. Retry is Boardroom-only; review mode and approval stay tied to the same run."}</span></div>
      {currentBoardroom && <div className="button-row"><PrimaryButton onClick={onNext}>Review matching Decision Brief</PrimaryButton></div>}
    </Panel>
  </div>;
}

export function LiveBriefView({ onExportVerifiedGolden, readOnlySnapshot = false, liveRun, scenarioId, state, canRecordDecision, humanDecision, hasVerifiedGolden, goldenCacheError, onRun, onRetry, onFormula, onLiveEvidence, onDecision, onStageChange, onOpenVerifiedGolden }: {
  liveRun: LiveSimulation;
  scenarioId: string;
  state: BoardroomState;
  canRecordDecision: boolean;
  readOnlySnapshot?: boolean;
  humanDecision: string | null;
  hasVerifiedGolden: boolean;
  goldenCacheError: string | null;
  onRun: () => void;
  onRetry: () => void;
  onFormula: (optionId?: OptionId, scenarioId?: string) => void;
  onLiveEvidence: (evidenceId: string) => void;
  onDecision: (decision: string) => void;
  onStageChange: (stage: StageId) => void;
  onOpenVerifiedGolden: () => void;
  onExportVerifiedGolden: () => void;
}) {
  const sim = liveRun.response.data.simulation;
  const selection = liveRun.response.data.selections[scenarioId];
  const scenario = liveRun.request.scenarios.find((item) => item.id === scenarioId);
  const boardroom = readyRun(state, liveRun, scenarioId);
  const response = boardroom?.response.data;
  const brief = response?.brief.status === "selected" ? response.brief : null;
  const selectedId = selection?.status === "selected" ? selection.recommendedOptionId : null;
  const option = selectedId ? boundOption(liveRun, selectedId) : undefined;
  const cell = selectedId ? sim.matrix[scenarioId]?.find((row) => row.optionId === selectedId) : undefined;
  const baseline = sim.matrix[scenarioId]?.find((row) => row.optionId === "D0");
  const delta = selectedId ? liveRun.response.data.deltas.find((item) => item.scenarioId === scenarioId && item.optionId === selectedId) : undefined;
  const isReviewed = liveRun.integrationMode === "reviewed-v2" && liveRun.development?.executionContext.decisionReady === true;
  const decisionReady = canRecordDecision && isReviewed && !!boardroom && !!brief && !!selection && selection.status === "selected" && !!cell && cell.feasible && response?.numericGuardrail.passed === true && response.numericGuardrail.rejectedClaims.length === 0;
  const label = scenario?.label ?? scenarioId;

  return <div className="stage-grid day4-brief-grid">
    <Panel className="day4-live-brief">
      <div className="day4-brief-header"><div><SectionLabel index="05" label={readOnlySnapshot ? "Stored test choice · read-only" : "Run-bound human decision"} /><h2>{selectedId && option ? brief ? brief.recommendation : "Matching Boardroom response required" : "No feasible option"}</h2><p>{brief ? brief.rationale : "The saved Day 2 example is not substituted for this live simulation."}</p></div><StatusChip tone={response ? boardroom?.providerMode === "same-family-fallback" ? "warning" : "success" : "warning"}>{readOnlySnapshot ? "CACHED VERIFIED REVIEW · READ-ONLY" : response ? boardroom?.providerMode === "same-family-fallback" ? "LIVE · SAME-FAMILY REVIEW" : "LIVE · PRIMARY REVIEW" : isReviewed ? "WAITING FOR MATCHING BOARDROOM" : "NOT DECISION-READY"}</StatusChip></div>
      <SimulationSummary liveRun={liveRun} scenarioId={scenarioId} readOnlySnapshot={readOnlySnapshot} />
      {!selection || selection.status === "no_feasible_option" ? <div className="no-feasible-panel downstream-no-feasible" role="status"><h3>No feasible option</h3><p>No recommendation, approve, or reject action is available for {label}. Review constraints, change assumptions, and run a new simulation.</p></div> : null}
      {!boardroom && <div className="brief-gate-panel" role="status"><LockKeyhole size={20} /><div><b>Brief is not ready</b><p>{isReviewed ? "Run the Boardroom stage for this exact simulation and scenario first." : "A formal Brief requires a reviewed, release-gated v2 simulation. The current run remains viewable."}</p><button type="button" className="brief-change-assumptions" onClick={() => onStageChange("scenario")}><FileCheck2 size={15} />Change assumptions</button></div></div>}
      {response && brief && boardroom && selectedId && cell && baseline && delta && option && <>
        <div className="brief-bound-metrics"><Metric label="Expected 24m TCO" value={money(cell.expectedTco)} detail={`${selectedId} · ${label} · from current validated Simulation`} tone="lime" /><Metric label="Stockout probability" value={percent(cell.stockoutProbability)} detail="from current validated Simulation" /><Metric label="P90 cash outflow" value={money(cell.cashOutflowP90)} detail="from current validated Simulation" /></div>
        <section className="live-delta-panel"><div><GitCompareArrows size={18} /><b>Decision Delta · {selectedId} − D0 · {label}</b></div><span>TCO {signedMoney(delta.deltaTco)}</span><span>Stockout {signedPp(delta.deltaStockoutPp)}</span><span>Service {signedPp(delta.deltaServicePp)}</span><span>P90 cash {signedMoney(delta.deltaCashP90)}</span></section>
        <div className="day4-numeric-guardrail"><LockKeyhole size={16} /><span>Numeric Guardrail <b>{response.numericGuardrail.passed && response.numericGuardrail.rejectedClaims.length === 0 ? "PASSED" : "BLOCKED"}</b> · {response.numericGuardrail.rejectedClaims.length} rejected claims · accepted refs: {brief.metricRefs.join(", ")}</span></div>
        <div className="live-brief-critic-list"><div className="live-section-heading"><div><small>{readOnlySnapshot ? "STORED CRITIC · SAME RUN" : "CRITIC · SAME RUN"}</small><h3>{response.criticIssues.length ? "Challenges retained" : "No Critic issues returned"}</h3></div><BrainCircuit size={20} /></div>{response.criticIssues.map((issue, index) => <article className="live-brief-critic" key={`${issue.severity}-${index}`}><b>{issue.severity} · {issue.headline}</b><p>{issue.body}</p><div className="evidence-buttons">{issue.evidenceIds.map((id) => <button type="button" key={id} onClick={() => onLiveEvidence(id)}>{id} · {readOnlySnapshot ? "open verified Evidence" : "open live Evidence"}</button>)}</div></article>)}</div>
        <div className="day4-brief-actions"><TraceLink onClick={() => onFormula(selectedId, scenarioId)}>Formula Trace · {selectedId} · same simulation</TraceLink>{response.criticIssues.flatMap((issue) => issue.evidenceIds)[0] ? <TraceLink kind="evidence" onClick={() => onLiveEvidence(response.criticIssues.flatMap((issue) => issue.evidenceIds)[0])}>{readOnlySnapshot ? "Open verified Evidence" : "Open live Evidence"}</TraceLink> : <span className="evidence-pending-note">No Evidence IDs were returned.</span>}</div>
        <div className="brief-run-provenance"><span>Simulation ID <b>{sim.simulationId}</b></span><span>Simulation request <b>{liveRun.response.requestId}</b></span><span>Boardroom request <b>{boardroom.requestId}</b></span><span>Data version <b>{sim.dataVersion}</b></span><span>Scenario <b>{scenarioId}</b></span><span>{readOnlySnapshot ? "Original provider mode" : "Provider"} <b>{boardroom.providerMode === "same-family-fallback" ? "same-family fallback" : "primary"}</b></span><span>Human review <b>{liveRun.development?.executionContext.humanReviewStatus ?? "not represented"}</b></span><span>Team policy <b>{liveRun.development?.executionContext.policyStatus ?? "not represented"}</b></span><span>v2 release <b>{liveRun.development?.executionContext.contractReleaseStatus ?? "not represented"}</b></span></div>
        <div className="human-decision-scope"><LockKeyhole size={16} /><span>{readOnlySnapshot ? "The stored Rejected value is an automated G4 UI-test artifact, not a human business decision, team approval, or supplier action." : "Approve/Reject records a choice in this browser for this exact run and option only. It is not transmitted, signed, or sent to a supplier."}</span></div>
        {readOnlySnapshot ? <div className="decision-buttons"><button type="button" className="change" onClick={() => onStageChange("scenario")}><FileCheck2 size={17} />Exit read-only snapshot · change assumptions</button></div> : <div className="decision-buttons"><button type="button" className="approve" onClick={() => onDecision("Approved")} disabled={!decisionReady} title={!decisionReady ? "Requires the matching reviewed run, complete Boardroom, and passing Numeric Guardrail" : undefined}><Check size={17} />Record human approval {selectedId}</button><button type="button" className="reject" onClick={() => onDecision("Rejected")} disabled={!decisionReady}><X size={17} />Record rejection</button><button type="button" className="change" onClick={() => onStageChange("scenario")}><FileCheck2 size={17} />Change assumptions</button></div>}
        {humanDecision && <div className="decision-confirm"><ClipboardCheck size={18} /><div><b>{readOnlySnapshot ? `Stored choice · ${humanDecision}` : humanDecision}</b><span>{readOnlySnapshot ? "Automated G4 UI-test artifact only; no human business decision or release approval was recorded." : `Recorded locally for ${sim.simulationId} · ${scenarioId} · ${selectedId}; no external approval occurred.`}</span></div></div>}
        {hasVerifiedGolden && <div className="verified-golden-open"><b>A complete verified Golden E2E run is available in this site bundle or browser cache.</b><button type="button" onClick={onOpenVerifiedGolden}>Open cached verified Golden run</button><button type="button" onClick={onExportVerifiedGolden}>Export verified Golden snapshot</button></div>}
        {goldenCacheError && <div className="golden-cache-status" role="status"><b>Verified Golden cache status</b><span>{goldenCacheError}</span></div>}
      </>}
      {isReviewed && state.status === "idle" && selection?.status === "selected" && <div className="downstream-action"><div><b>Complete the matching Boardroom review</b><span>This request does not rerun simulation.</span></div><PrimaryButton onClick={onRun}>Run Boardroom</PrimaryButton></div>}
      {isReviewed && state.status === "error" && <DownstreamFailure state={state} onRetry={onRetry} />}
      {!isReviewed && <div className="downstream-gate" role="status"><Info size={17} /><span>The simulation, Matrix, and Formula Trace remain available. Approval remains disabled while required review/policy/release gates are pending.</span></div>}
    </Panel>
    <Panel className="day4-human-control" title={readOnlySnapshot ? "Stored choice provenance" : "Human decision control"}><div className="human-portrait"><span>{readOnlySnapshot ? "T" : "H"}</span><div><small>{readOnlySnapshot ? "AUTOMATED TEST RECORD" : "HUMAN REVIEWER"}</small><h3>{readOnlySnapshot ? "No human business decision was recorded." : "Keep the final call with the human."}</h3></div></div><p>{readOnlySnapshot ? "This verified Golden snapshot is read-only. Its stored Rejected choice is an automated G4 UI-test artifact, not team approval or a supplier instruction." : decisionReady ? "The current live Brief passed the v1 response, run-identity, Critic, and Numeric Guardrail checks." : "No action is enabled until the current simulation and matching Boardroom result pass their gates."}</p><ul className="human-control-gates"><li><span>Simulation</span><b>{isReviewed ? "Reviewed v2" : "Not decision-ready"}</b></li><li><span>Boardroom identity</span><b>{boardroom ? "Matches current run" : "No matching response"}</b></li><li><span>Numeric Guardrail</span><b>{response?.numericGuardrail.passed && response.numericGuardrail.rejectedClaims.length === 0 ? "Passed" : "Pending"}</b></li><li><span>{readOnlySnapshot ? "Human decision" : "Human action"}</span><b>{readOnlySnapshot ? "Not present · stored test choice only" : decisionReady ? "Local only" : "Disabled"}</b></li></ul><button type="button" className="human-back-to-matrix" onClick={() => onStageChange("matrix")}>Return to Decision Matrix</button></Panel>
  </div>;
}
