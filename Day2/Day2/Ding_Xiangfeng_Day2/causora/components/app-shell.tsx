"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Activity, AlertTriangle, ArrowRight, Database, FileText, Grid2X2, Landmark, Play, RotateCcw, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import type { AppState, MockData, StageId } from "@/lib/types";
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

function runLabel(runState: AppState) {
  if (runState === "golden") return { text: "CACHED · VERIFIED GOLDEN RUN", tone: "warning" as const };
  if (runState === "no-feasible") return { text: "NO FEASIBLE OPTION · APPROVAL BLOCKED", tone: "warning" as const };
  if (runState === "error") return { text: "LIVE UNAVAILABLE · LOCAL FALLBACK READY", tone: "warning" as const };
  if (runState === "loading") return { text: "LOCAL DEMO SEQUENCING", tone: "signal" as const };
  return { text: "LOCAL MOCK · TRACEABLE", tone: "success" as const };
}

export function AppShell({ data, activeStage, runState, scenarioLabel, optionCosts, humanDecision, decisionMoment, onDismissMoment, onStageChange, onGoldenRun, onReset, children, toast }: { data: MockData; activeStage: StageId; runState: AppState; scenarioLabel: string; optionCosts: Record<string, string>; humanDecision: string | null; decisionMoment: "Approved" | "Rejected" | null; onDismissMoment: () => void; onStageChange: (stage: StageId) => void; onGoldenRun: () => void; onReset: () => void; children: ReactNode; toast: string | null }) {
  const activeIndex = stages.findIndex((stage) => stage.id === activeStage);
  const label = runLabel(runState);
  const matched = data.evidence.filter((item) => item.quoteMatched).length;
  const previousIndex = useRef(activeIndex);
  const reduceMotion = useReducedMotion();
  const direction = activeIndex >= previousIndex.current ? 1 : -1;
  useEffect(() => { previousIndex.current = activeIndex; }, [activeIndex]);

  return (
    <main className="app-shell">
      <aside className="decision-rail" aria-label="Decision workflow">
        <div className="rail-brand"><CausoraMark /><span className="day-one">DAY 2 / 07</span></div>
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
          <div className="integrity-card"><ShieldCheck size={17} /><div><small>Integrity layer</small><b>{matched} / {data.evidence.length} fields matched</b></div></div>
          <p>Static mock only.<br />No simulation, AI, or HTTP calls.</p>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="breadcrumb"><span>CAUSORA</span><i /> <b>Decision workspace</b><i /> <strong>{stages[activeIndex].label}</strong><span className="breadcrumb-progress">0{activeIndex + 1} / 05</span></div>
          <div className="topbar-actions">
            <StatusChip tone={label.tone}>{label.text}</StatusChip>
            <GhostButton onClick={onReset} ariaLabel="Reset local demo"><RotateCcw size={16} /><span>Reset</span></GhostButton>
            <PrimaryButton onClick={onGoldenRun} icon={false} className="golden-trigger"><Play size={14} fill="currentColor" />Open Golden Run</PrimaryButton>
          </div>
        </header>

        <div className="mobile-progress" aria-label="Workflow progress">
          {stages.map((stage, index) => <button type="button" onClick={() => onStageChange(stage.id)} key={stage.id} className={stage.id === activeStage ? "active" : ""}><span>{index + 1}</span>{stage.label}</button>)}
        </div>

        <div className="thread-line" aria-hidden="true"><span style={{ width: `${((activeIndex + 1) / stages.length) * 100}%` }} /></div>
        {runState !== "no-feasible" && <ProofEngine data={data} activeStage={activeStage} scenarioLabel={scenarioLabel} optionCosts={optionCosts} decision={humanDecision} onStageChange={onStageChange} />}
        <AnimatePresence mode="wait">
          <motion.div key={activeStage} className="stage-canvas" initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: 30 * direction }} animate={{ opacity: 1, x: 0 }} exit={reduceMotion ? { opacity: 0 } : { opacity: 0, x: -24 * direction }} transition={{ duration: reduceMotion ? 0.06 : 0.31, ease: [0.22, 1, 0.36, 1] }}>
            {children}
          </motion.div>
        </AnimatePresence>
      </section>
      <DecisionMoment optionId={data.brief.recommendedOptionId} decision={decisionMoment} onDismiss={onDismissMoment} />
      <AnimatePresence>{toast && <motion.div className="toast" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }}><AlertTriangle size={16} />{toast}<ArrowRight size={15} /></motion.div>}</AnimatePresence>
    </main>
  );
}
