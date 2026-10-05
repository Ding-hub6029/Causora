"use client";

import { useEffect, useMemo, useState } from "react";
import data from "@/demo_data/causora_day1_mock.json";
import goldenRunJson from "@/golden/golden_run.json";
import type { OptionId } from "@/lib/contracts";
import type { AppState, GoldenRun, MockData, ModalState, StageId } from "@/lib/types";
import { validateMockData, validateGoldenRun, verifyGoldenHash } from "@/lib/validation";
import { money } from "@/lib/metrics";
import { AppShell, stages } from "@/components/app-shell";
import { StageView } from "@/components/stage-views";
import { DetailModal } from "@/components/detail-modal";

const mockData = data as MockData;
const goldenRun = goldenRunJson as GoldenRun;
const DEFAULT_RISK_THRESHOLD = 12;

export default function Home() {
  try { validateMockData(data); validateGoldenRun(goldenRunJson); }
  catch { return <main className="stage-content" role="alert"><h1>Local dataset could not be verified.</h1><p>Approval is unavailable. Restore the supplied mock and Golden files before continuing.</p></main>; }
  return <Workspace />;
}

function Workspace() {
  const [activeStage, setActiveStage] = useState<StageId>("intake");
  const [runState, setRunState] = useState<AppState>("ready");
  const [scenarioId, setScenarioId] = useState("baseline");
  const [demandShift, setDemandShift] = useState(0);
  const [riskThreshold, setRiskThreshold] = useState(DEFAULT_RISK_THRESHOLD);
  const [selectedOption, setSelectedOption] = useState<OptionId>("D1");
  const [modal, setModal] = useState<ModalState>({ kind: "closed" });
  const [toast, setToast] = useState<string | null>(null);
  const [humanDecision, setHumanDecision] = useState<string | null>(null);
  const [decisionMoment, setDecisionMoment] = useState<"Approved" | "Rejected" | null>(null);

  // While the Golden Run is active the UI reads only the frozen snapshot, never the live mock file.
  const activeData: MockData = runState === "golden" ? goldenRun.snapshot : mockData;

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 3800);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (!decisionMoment) return;
    const timer = window.setTimeout(() => setDecisionMoment(null), 2900);
    return () => window.clearTimeout(timer);
  }, [decisionMoment]);

  const currentScenario = useMemo(() => activeData.scenarios.find((scenario) => scenario.id === scenarioId) ?? activeData.scenarios[0], [activeData, scenarioId]);
  const optionCosts = useMemo(() => Object.fromEntries(activeData.simulation.matrix[scenarioId].map((row) => [row.optionId, money(row.expectedTco)])), [activeData, scenarioId]);
  const isDraft = demandShift !== currentScenario.demandShock || riskThreshold !== DEFAULT_RISK_THRESHOLD;

  function moveStage(stage: StageId) {
    setActiveStage(stage);
    if (runState === "loading") setRunState("ready");
  }

  function nextStage() {
    const current = stages.findIndex((stage) => stage.id === activeStage);
    const next = stages[Math.min(current + 1, stages.length - 1)];
    setActiveStage(next.id);
  }

  async function openGoldenRun() {
    try { await verifyGoldenHash(goldenRun); }
    catch { setToast("Golden integrity validation failed. Approval remains unavailable for this cache."); return; }
    setRunState("golden");
    setActiveStage("intake");
    setHumanDecision(null);
    setDecisionMoment(null);
    setScenarioId(goldenRun.request.scenario);
    setDemandShift(goldenRun.snapshot.scenarios.find((scenario) => scenario.id === goldenRun.request.scenario)?.demandShock ?? 0);
    setRiskThreshold(goldenRun.request.riskThreshold);
    setSelectedOption(goldenRun.response.recommendedOptionId);
    setToast(`Verified local Golden Run ${goldenRun.dataVersion} loaded. The UI now renders only the frozen snapshot.`);
  }

  /** Any edit leaves the frozen snapshot: the modified state is no longer the verified Golden Run. */
  function leaveGoldenIfNeeded() {
    if (runState !== "golden") return;
    setRunState("ready");
    setToast("You changed the inputs, so the verified Golden Run label was removed. The workspace is back on the local mock dataset.");
  }

  function resetDemo() {
    setRunState("ready");
    setActiveStage("intake");
    setScenarioId("baseline");
    setDemandShift(0);
    setRiskThreshold(DEFAULT_RISK_THRESHOLD);
    setSelectedOption("D1");
    setHumanDecision(null);
    setDecisionMoment(null);
    setToast("The local decision workspace has been reset.");
  }

  function previewState(state: AppState) {
    setRunState(state);
    setHumanDecision(null);
    setDecisionMoment(null);
    setToast(`${state.charAt(0).toUpperCase() + state.slice(1)} state preview enabled for ${activeStage}.`);
  }

  function selectScenario(id: string) {
    leaveGoldenIfNeeded();
    setScenarioId(id);
    setDemandShift(mockData.scenarios.find((scenario) => scenario.id === id)?.demandShock ?? 0);
    setHumanDecision(null);
    setDecisionMoment(null);
  }

  function changeDemandShift(value: number) {
    leaveGoldenIfNeeded();
    setDemandShift(value);
    setHumanDecision(null);
    setDecisionMoment(null);
  }

  function changeRiskThreshold(value: number) {
    leaveGoldenIfNeeded();
    setRiskThreshold(value);
    setHumanDecision(null);
    setDecisionMoment(null);
  }

  function decide(decision: string) {
    if ((isDraft || runState === "no-feasible") && decision === "Approved") {
      setToast("Approval blocked: these draft assumptions were not simulated. Return to Scenario Lab and restore the preset inputs first.");
      return;
    }
    const recommended = activeData.brief.recommendedOptionId;
    setHumanDecision(decision === "Assumptions queued" ? null : decision);
    if (decision === "Approved" || decision === "Rejected") setDecisionMoment(decision);
    setToast(decision === "Approved" ? `${recommended} has been marked as approved by a human reviewer for the ${currentScenario.label} preset.` : decision === "Rejected" ? "The recommendation has been rejected. The evidence remains available for review." : "Assumption review is now queued. Return to Scenario Lab to adjust the local mock inputs.");
  }

  const openFormula = (optionId?: OptionId) => setModal({ kind: "formula", scenarioId, optionId: optionId ?? selectedOption });

  return (
    <AppShell data={activeData} activeStage={activeStage} runState={runState} scenarioLabel={currentScenario.label} optionCosts={optionCosts} humanDecision={humanDecision} decisionMoment={decisionMoment} onDismissMoment={() => setDecisionMoment(null)} onStageChange={moveStage} onGoldenRun={openGoldenRun} onReset={resetDemo} toast={toast}>
      <StageView
        stage={activeStage}
        appState={runState}
        data={activeData}
        currentScenario={currentScenario}
        scenarioId={scenarioId}
        demandShift={demandShift}
        riskThreshold={riskThreshold}
        isDraft={isDraft}
        selectedOption={selectedOption}
        humanDecision={humanDecision}
        onScenarioChange={selectScenario}
        onDemandShiftChange={changeDemandShift}
        onRiskThresholdChange={changeRiskThreshold}
        onOptionSelect={setSelectedOption}
        onEvidence={(evidence) => setModal({ kind: "evidence", evidence })}
        onEvidenceStack={() => setModal({ kind: "stack" })}
        onFormula={openFormula}
        onNext={nextStage}
        onPreviewState={previewState}
        onGoldenRun={openGoldenRun}
        onDecision={decide}
        onStageChange={moveStage}
      />
      <DetailModal modal={modal} onClose={() => setModal({ kind: "closed" })} onEvidence={(evidence) => setModal({ kind: "evidence", evidence })} data={activeData} />
    </AppShell>
  );
}
