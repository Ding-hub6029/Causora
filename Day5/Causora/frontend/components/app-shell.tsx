"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Activity, AlertTriangle, ArrowRight, Database, FileText, Grid2X2, Landmark, Play, RotateCcw, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import type { EvidenceRecord, OptionId } from "@/lib/contracts";
import type { AppState, LiveSimulation, MockData, StageId } from "@/lib/types";
import type { BoardroomState, SimulationModeLabel } from "@/lib/day4-types";
import type { BackendHealthState } from "@/lib/golden-health";
import { isCurrentBoardroomRun } from "@/lib/boardroom-api";
import { CausoraMark, GhostButton, PrimaryButton, StatusChip } from "./ui";
import { ProofEngine } from "./proof-engine";
import { DecisionMoment } from "./decision-moment";

export const stages: Array<{ id: StageId; number: string; label: string; caption: string; icon: typeof Database }> = [
  { id: "intake", number: "01", label: "Data Intake", caption: "Sources linked", icon: Database },
  { id: "scenario", number: "02", label: "Scenario Lab", caption: "Variables constrained", icon: Sparkles },
  { id: "matrix", number: "03", label: "Decision Matrix", caption: "Options compared", icon: Grid2X2 },
  { id: "boardroom", number: "04", label: "AI Boardroom", caption: "Views challenged", icon: Landmark },
  { id: "brief", number: "05", label: "Decision Brief", caption: "Human decision", icon: FileText }
];

function runLabel(runState: AppState, simulationStatus: SimulationModeLabel, hasLiveRun: boolean) {
  if (simulationStatus === "running") return { text: "POST /API/SIMULATE · RUNNING", tone: "signal" as const };
  if (simulationStatus === "dev-live") return { text: "UNREVIEWED DEV · NOT DECISION-READY", tone: "warning" as const };
  if (simulationStatus === "live") return { text: "LIVE · PRIMARY REVIEW COMPLETE", tone: "success" as const };
  if (simulationStatus === "simulation-only") return { text: "LIVE SIMULATION · REVIEW NOT COMPLETE", tone: "signal" as const };
  if (simulationStatus === "ai-unavailable") return { text: "LIVE SIMULATION · AI REVIEW UNAVAILABLE", tone: "warning" as const };
  if (simulationStatus === "same-family-review") return { text: "LIVE · SAME-FAMILY FALLBACK REVIEW", tone: "warning" as const };
  if (simulationStatus === "cached-verified") return { text: "CACHED · VERIFIED GOLDEN RUN", tone: "success" as const };
  if (simulationStatus === "error") return { text: hasLiveRun ? "LIVE API FAILED · LAST LIVE RESULT RETAINED" : "LIVE API FAILED · SAVED EXAMPLE RETAINED", tone: "warning" as const };
  if (simulationStatus === "saved-example" || runState === "golden") return { text: "SAVED EXAMPLE · NOT VERIFIED E2E", tone: "warning" as const };
  if (runState === "no-feasible") return { text: "NO FEASIBLE OPTION · APPROVAL BLOCKED", tone: "warning" as const };
  if (runState === "error") return { text: "LIVE UNAVAILABLE · LOCAL FALLBACK READY", tone: "warning" as const };
  if (runState === "loading") return { text: "LOCAL DEMO SEQUENCING", tone: "signal" as const };
  return { text: "LOCAL MOCK · TRACEABLE", tone: "success" as const };
}

export function AppShell({ data, activeStage, runState, scenarioLabel, scenarioId, selectedOption, optionCosts, liveRun, goldenEvidenceRecords, simulationStatus, humanDecision, decisionMoment, decisionOptionId, boardroomState, cachedGoldenActive, hasVerifiedGolden, goldenSource, backendHealth, onDismissMoment, onStageChange, onGoldenRun, onOpenVerifiedGolden, onHealthCheck, onReset, children, toast }: { data: MockData; activeStage: StageId; runState: AppState; scenarioLabel: string; scenarioId: string; selectedOption: OptionId; optionCosts: Record<string, string>; liveRun: LiveSimulation | null; goldenEvidenceRecords: ReadonlyArray<{ requestId: string; evidence: EvidenceRecord }>; simulationStatus: SimulationModeLabel; humanDecision: string | null; decisionMoment: "Approved" | "Rejected" | null; decisionOptionId: OptionId; boardroomState: BoardroomState; cachedGoldenActive: boolean; hasVerifiedGolden: boolean; goldenSource: "browser-cache" | "static-bundle" | null; backendHealth: BackendHealthState; onDismissMoment: () => void; onStageChange: (stage: StageId) => void; onGoldenRun: () => void; onOpenVerifiedGolden: () => void; onHealthCheck: () => void; onReset: () => void; children: ReactNode; toast: string | null }) {
  const activeIndex = stages.findIndex((stage) => stage.id === activeStage);
  const label = runLabel(runState, simulationStatus, Boolean(liveRun));
  const matched = data.evidence.filter((item) => item.quoteMatched).length;
  const currentBoardroom = liveRun && boardroomState.status === "ready" && isCurrentBoardroomRun(boardroomState.run, liveRun, scenarioId) ? boardroomState.run : null;
  const currentBoardroomFailure = liveRun && boardroomState.status === "error" && boardroomState.identity.simulationId === liveRun.response.data.simulation.simulationId && boardroomState.identity.dataVersion === liveRun.response.data.simulation.dataVersion && boardroomState.identity.scenarioId === scenarioId && boardroomState.identity.simulationRequestId === liveRun.response.requestId;
  const previousIndex = useRef(activeIndex);
  const reduceMotion = useReducedMotion();
  const direction = activeIndex >= previousIndex.current ? 1 : -1;
  useEffect(() => { previousIndex.current = activeIndex; }, [activeIndex]);

  return (
    <main className="app-shell">
      <aside className="decision-rail" aria-label="Decision workflow">
        <div className="rail-brand"><CausoraMark /><span className="day-one">DAY 5 / 07</span></div>
        <div className="rail-intro"><p>Decision twin</p><strong>Trace the choice<br />before you make it.</strong></div>
        <nav className="stage-nav">
          {stages.map((stage, index) => {
            const Icon = stage.icon;
            const selected = stage.id === activeStage;
            const complete = index < activeIndex;
            return <button type="button" key={stage.id} className={`stage-nav-item ${selected ? "active" : ""} ${complete ? "complete" : ""}`} onClick={() => onStageChange(stage.id)} aria-current={selected ? "step" : undefined}>
              <span className="stage-dot">{complete ? <Activity size={14} /> : stage.number}</span>
              <span className="stage-name"><b>{stage.label}</b><small>{stage.caption}</small></span>
              <Icon size={16} aria-hidden="true" />
            </button>;
          })}
        </nav>
        <div className="rail-bottom">
          <div className="integrity-card"><ShieldCheck size={17} /><div><small>{cachedGoldenActive ? "Verified Golden integrity" : liveRun ? "Saved-example integrity" : "Integrity layer"}</small><b>{cachedGoldenActive ? "Complete frozen records revalidated" : `${matched} / ${data.evidence.length} ${liveRun ? "fixture fields matched" : "fields matched"}`}</b></div></div>
          <p>{cachedGoldenActive ? `Read-only complete reviewed E2E snapshot from ${goldenSource === "static-bundle" ? "the static site bundle" : "browser cache"}; all records were revalidated.` : liveRun?.integrationMode === "unreviewed-v2-dev" ? "Matrix values: UNREVIEWED development calculation." : liveRun ? "Matrix values: validated live API response." : simulationStatus === "running" ? "Waiting for /api/simulate." : runState === "golden" ? "Showing the saved Day 2 example; not a verified E2E run." : "Matrix values: saved Day 2 example until a successful run."}<br />{cachedGoldenActive ? "No API call is made and the snapshot is read-only." : liveRun?.integrationMode === "unreviewed-v2-dev" ? "No approval, Boardroom result, or recommendation is created." : currentBoardroom ? "Boardroom and Critic are validated for this exact run; Evidence is fetched on demand." : currentBoardroomFailure ? "AI review failed; Matrix and Formula Trace remain. No mock is substituted." : liveRun ? "Matching Boardroom is separate; downstream failures never clear Matrix values." : "No response is presented as live without validation."}</p>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="breadcrumb"><span>CAUSORA</span><i /> <b>Decision workspace</b><i /> <strong>{stages[activeIndex].label}</strong><span className="breadcrumb-progress">0{activeIndex + 1} / 05</span></div>
          <div className="topbar-actions">
            <StatusChip tone={label.tone}>{label.text}</StatusChip>
            <GhostButton onClick={onReset} ariaLabel="Reset local demo"><RotateCcw size={16} /><span>Reset</span></GhostButton>
            {hasVerifiedGolden && !cachedGoldenActive && <GhostButton onClick={onOpenVerifiedGolden} ariaLabel="Open cached verified Golden E2E run"><ShieldCheck size={15} /><span>Verified cache</span></GhostButton>}
            <PrimaryButton onClick={onGoldenRun} icon={false} className="golden-trigger"><Play size={14} fill="currentColor" />Open saved example</PrimaryButton>
          </div>
        </header>
        {backendHealth.status === "checking" && <aside className="backend-health-panel checking" role="status" aria-live="polite"><Activity size={18} /><div><b>Connecting to live simulation · waiting for server</b><p>The free server may need about a minute to start. This page waits up to 75 seconds and enables Run simulation when ready. Saved examples and Verified cache remain available; they are not new live results.</p></div></aside>}
        {backendHealth.status === "healthy" && <aside className="backend-health-panel healthy" role="status"><ShieldCheck size={18} /><div><b>Simulation service reachable · {backendHealth.health.simulation.replaceAll("_", " ")}</b><p>{backendHealth.health.missingReasons.length ? `Review/release gates remain pending: ${backendHealth.health.missingReasons.join(", ")}. Reachability is not approval.` : "Health confirms service readiness only; human review and team policy gates are evaluated separately."}</p></div><button type="button" onClick={onHealthCheck}>Recheck health</button></aside>}
        {backendHealth.status === "waking" && <aside className="backend-health-panel waking" role="status" aria-live="polite"><AlertTriangle size={19} /><div className="backend-health-copy"><b>{backendHealth.code === "not_configured" ? "Public backend not configured" : "Server waking up"}</b><p>{backendHealth.message}{backendHealth.code === "not_configured" ? "" : " Wait briefly and retry; a cold-start service may take about one minute to wake."}</p>{hasVerifiedGolden ? <p>A complete reviewed Golden snapshot is available in this site bundle or browser cache and will open read-only without an API request.</p> : <p>This site checks the bundled full E2E snapshot on startup; only a record that passes production validation is labeled Verified. The separate Day 2 example is synthetic and is <strong>not</strong> a verified Golden Run.</p>}</div><div className="backend-health-actions">{backendHealth.code !== "not_configured" && <button type="button" onClick={onHealthCheck}><RotateCcw size={14} />Check again</button>}{hasVerifiedGolden ? <button type="button" className="golden-fallback-button" onClick={onOpenVerifiedGolden}><ShieldCheck size={14} />Open Verified Golden Run</button> : <button type="button" className="golden-fallback-button" onClick={onGoldenRun}><Play size={14} />Open saved example · not verified E2E</button>}</div></aside>}
        {cachedGoldenActive && <aside className="golden-provenance-panel" role="note" aria-label="Verified Golden provenance"><ShieldCheck size={18} /><div><b>READ-ONLY VERIFIED GOLDEN · {goldenSource === "static-bundle" ? "SITE-BUNDLED" : "BROWSER-CACHED"}</b>{goldenSource === "static-bundle" ? <p>Stored choice: <strong>{humanDecision ?? "Unavailable"}</strong>. This choice is an automated G4 UI-test artifact scoped to a browser; it is not a business decision or team/release approval.</p> : <p>Stored choice: <strong>{humanDecision ?? "Unavailable"}</strong>. This browser-local snapshot is not an external action or team/release approval.</p>}<span>Simulation, Boardroom, Brief, and cited Evidence were revalidated from the frozen record. No backend call is made; this view is read-only.</span></div></aside>}
        {liveRun?.integrationMode === "unreviewed-v2-dev" && <aside className="unreviewed-dev-banner" role="alert"><AlertTriangle size={18} /><div><b>UNREVIEWED — DEVELOPMENT ONLY</b><span>Human review, team policy and v2 release are still pending. This Monte Carlo result is NOT DECISION-READY, not a formal recommendation and cannot be approved.</span></div></aside>}

        <div className="mobile-progress" aria-label="Workflow progress">
          {stages.map((stage, index) => <button type="button" onClick={() => onStageChange(stage.id)} key={stage.id} className={stage.id === activeStage ? "active" : ""}><span>{index + 1}</span>{stage.label}</button>)}
        </div>

        <div className="thread-line" aria-hidden="true"><span style={{ width: `${((activeIndex + 1) / stages.length) * 100}%` }} /></div>
        {runState !== "no-feasible" && <ProofEngine data={data} activeStage={activeStage} scenarioLabel={scenarioLabel} scenarioId={scenarioId} selectedOption={selectedOption} optionCosts={optionCosts} liveRun={liveRun} goldenEvidenceRecords={goldenEvidenceRecords} readOnlySnapshot={cachedGoldenActive} boardroomState={boardroomState} decision={humanDecision} decisionOptionId={decisionOptionId} onStageChange={onStageChange} />}
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={activeStage} className="stage-canvas" initial={{ opacity: 0, x: 30 * direction }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 * direction }} transition={{ duration: reduceMotion ? 0.06 : 0.31, ease: [0.22, 1, 0.36, 1] }}>
            {children}
          </motion.div>
        </AnimatePresence>
      </section>
      <DecisionMoment optionId={decisionOptionId} decision={decisionMoment} onDismiss={onDismissMoment} />
      <AnimatePresence>{toast && <motion.div className="toast" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }}><AlertTriangle size={16} />{toast}<ArrowRight size={15} /></motion.div>}</AnimatePresence>
    </main>
  );
}
