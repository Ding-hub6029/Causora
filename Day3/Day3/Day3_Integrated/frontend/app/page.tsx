"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import data from "@/demo_data/causora_day1_mock.json";
import goldenRunJson from "@/golden/golden_run.json";
import type { OptionId } from "@/lib/contracts";
import { buildSimulateRequest, postSimulate } from "@/lib/simulate-api";
import type { AppState, GoldenRun, LiveSimulation, MockData, ModalState, StageId } from "@/lib/types";
import { validateMockData, validateGoldenRun, verifyGoldenHash } from "@/lib/validation";
import { money } from "@/lib/metrics";
import { AppShell, stages } from "@/components/app-shell";
import { StageView } from "@/components/stage-views";
import { DetailModal } from "@/components/detail-modal";

const mockData = data as MockData;
const goldenRun = goldenRunJson as GoldenRun;
const DEFAULT_RISK_THRESHOLD = 12;
const DEFAULT_BUDGET_CEILING_USD = 480000;

export default function Home() {
  try { validateMockData(data); validateGoldenRun(goldenRunJson); }
  catch { return <main className="stage-content" role="alert"><h1>Local dataset could not be verified.</h1><p>Approval is unavailable. Restore the supplied mock and Golden files before continuing.</p></main>; }
  return <Workspace />;
}

function Workspace() {
  const [activeStage, setActiveStage] = useState<StageId>("intake");
  const [runState, setRunState] = useState<AppState>("ready");
  const [scenarioId, setScenarioId] = useState("baseline");
  const [matrixScenarioId, setMatrixScenarioId] = useState("baseline");
  const [demandShift, setDemandShift] = useState(0);
  const [riskThreshold, setRiskThreshold] = useState(DEFAULT_RISK_THRESHOLD);
  const [budgetCeilingUsd, setBudgetCeilingUsd] = useState(DEFAULT_BUDGET_CEILING_USD);
  const [selectedOption, setSelectedOption] = useState<OptionId>("D1");
  const [modal, setModal] = useState<ModalState>({ kind: "closed" });
  const [toast, setToast] = useState<string | null>(null);
  const [humanDecision, setHumanDecision] = useState<string | null>(null);
  const [decisionMoment, setDecisionMoment] = useState<"Approved" | "Rejected" | null>(null);
  const [liveRun, setLiveRun] = useState<LiveSimulation | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationError, setSimulationError] = useState<string | null>(null);
  const runSequence = useRef(0);
  const latestRequestKey = useRef("");

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
  const currentMatrixScenario = useMemo(() => activeData.scenarios.find((scenario) => scenario.id === matrixScenarioId) ?? activeData.scenarios[0], [activeData, matrixScenarioId]);
  const contextScenario = activeStage === "matrix" ? currentMatrixScenario : currentScenario;
  const contextScenarioId = contextScenario.id;
  const datasetId = process.env.NEXT_PUBLIC_CAUSORA_DATASET_ID?.trim() || "ds-001";
  const currentRequest = useMemo(() => buildSimulateRequest({ datasetId, scenarios: activeData.scenarios, options: activeData.options, selectedScenarioId: scenarioId, demandShift, riskThresholdPct: riskThreshold, budgetCeilingUsd, seed: activeData.meta.seed }), [activeData, budgetCeilingUsd, datasetId, demandShift, riskThreshold, scenarioId]);
  const currentRequestKey = JSON.stringify(currentRequest);
  latestRequestKey.current = currentRequestKey;
  const currentLiveRun = liveRun && JSON.stringify(liveRun.request) === currentRequestKey && runState !== "golden" ? liveRun : null;
  const optionCosts = useMemo(() => Object.fromEntries((currentLiveRun?.response.data.simulation.matrix[contextScenarioId] ?? activeData.simulation.matrix[contextScenarioId]).map((row) => [row.optionId, money(row.expectedTco)])), [activeData, currentLiveRun, contextScenarioId]);
  const isDraft = !currentLiveRun && (demandShift !== currentScenario.demandShock || riskThreshold !== DEFAULT_RISK_THRESHOLD || budgetCeilingUsd !== DEFAULT_BUDGET_CEILING_USD);

  function invalidateSimulation() {
    runSequence.current += 1;
    setIsSimulating(false);
    setLiveRun(null);
    setSimulationError(null);
  }

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
    invalidateSimulation();
    setRunState("golden");
    setActiveStage("intake");
    setHumanDecision(null);
    setDecisionMoment(null);
    setScenarioId(goldenRun.request.scenario);
    setMatrixScenarioId(goldenRun.request.scenario);
    setDemandShift(goldenRun.snapshot.scenarios.find((scenario) => scenario.id === goldenRun.request.scenario)?.demandShock ?? 0);
    setRiskThreshold(goldenRun.request.riskThreshold);
    setBudgetCeilingUsd(DEFAULT_BUDGET_CEILING_USD);
    setSelectedOption(goldenRun.response.recommendedOptionId);
    setToast(`Local mock snapshot ${goldenRun.dataVersion} loaded. Integrity check passed; saved example data only, no live calculation.`);
  }

  /** Any edit leaves the frozen snapshot: the modified state is no longer the verified Golden Run. */
  function leaveGoldenIfNeeded() {
    if (runState !== "golden") return;
    setRunState("ready");
    setToast("You changed the inputs, so the verified Golden Run label was removed. The workspace is back on the local mock dataset.");
  }

  function resetDemo() {
    invalidateSimulation();
    setRunState("ready");
    setActiveStage("intake");
    setScenarioId("baseline");
    setMatrixScenarioId("baseline");
    setDemandShift(0);
    setRiskThreshold(DEFAULT_RISK_THRESHOLD);
    setBudgetCeilingUsd(DEFAULT_BUDGET_CEILING_USD);
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
    const nextShift = mockData.scenarios.find((scenario) => scenario.id === id)?.demandShock ?? 0;
    if (nextShift !== demandShift) invalidateSimulation();
    setScenarioId(id);
    setMatrixScenarioId(id);
    setDemandShift(nextShift);
    setHumanDecision(null);
    setDecisionMoment(null);
  }

  function viewMatrixScenario(id: string) {
    setMatrixScenarioId(id);
  }

  function changeDemandShift(value: number) {
    leaveGoldenIfNeeded();
    invalidateSimulation();
    setDemandShift(value);
    setHumanDecision(null);
    setDecisionMoment(null);
  }

  function changeRiskThreshold(value: number) {
    leaveGoldenIfNeeded();
    invalidateSimulation();
    setRiskThreshold(value);
    setHumanDecision(null);
    setDecisionMoment(null);
  }

  function changeBudgetCeiling(value: number) {
    leaveGoldenIfNeeded();
    invalidateSimulation();
    setBudgetCeilingUsd(Number.isFinite(value) ? Math.max(0, Math.round(value)) : 0);
    setHumanDecision(null);
    setDecisionMoment(null);
  }

  async function runSimulation() {
    if (runState === "golden") { setToast("The frozen Golden Run is read-only. Return to the live workspace before requesting a simulation."); return; }
    const request = currentRequest;
    const requestKey = currentRequestKey;
    const sequence = ++runSequence.current;
    setLiveRun(null);
    setSimulationError(null);
    setIsSimulating(true);
    setHumanDecision(null);
    setDecisionMoment(null);
    try {
      const result = await postSimulate(request);
      if (sequence !== runSequence.current || latestRequestKey.current !== requestKey) return;
      const response = result.response;
      setLiveRun({ request, response, integrationMode: result.integrationMode, development: result.development, receivedAt: new Date().toISOString() });
      const selection = response.data.selections[scenarioId];
      if (selection?.status === "selected") setSelectedOption(selection.recommendedOptionId);
      setToast(result.integrationMode === "unreviewed-v2-dev" ? `UNREVIEWED DEVELOPMENT ONLY · ${response.data.simulation.monteCarloRuns.toLocaleString("en-US")} Monte Carlo runs · NOT DECISION-READY · no approval.` : `Live /api/simulate response validated · ${response.data.simulation.monteCarloRuns.toLocaleString("en-US")} runs · seed ${response.data.simulation.seed}.`);
    } catch (error) {
      if (sequence !== runSequence.current || latestRequestKey.current !== requestKey) return;
      const message = error instanceof Error ? error.message : "Simulation request failed.";
      setSimulationError(message);
      setToast("Live simulation was not applied. The saved Day 2 example remains clearly labelled below.");
    } finally {
      if (sequence === runSequence.current) setIsSimulating(false);
    }
  }

  function decide(decision: string) {
    if (currentLiveRun && decision === "Approved") {
      setToast("Approval is blocked: the live simulation has not yet been reviewed by the /api/boardroom workflow.");
      return;
    }
    if ((isDraft || runState === "no-feasible") && decision === "Approved") {
      setToast("Approval blocked: these draft assumptions were not simulated. Return to Scenario Lab and restore the preset inputs first.");
      return;
    }
    const recommended = activeData.brief.recommendedOptionId;
    setHumanDecision(decision === "Assumptions queued" ? null : decision);
    if (decision === "Approved" || decision === "Rejected") setDecisionMoment(decision);
    setToast(decision === "Approved" ? `${recommended} has been marked as approved by a human reviewer for the ${currentScenario.label} preset.` : decision === "Rejected" ? "The recommendation has been rejected. The evidence remains available for review." : "Assumption review is now queued. Return to Scenario Lab to adjust the local mock inputs.");
  }

  const openFormula = (optionId?: OptionId, formulaScenarioId: string = contextScenarioId) => setModal({ kind: "formula", scenarioId: formulaScenarioId, optionId: optionId ?? selectedOption });

  return (
    <AppShell
      data={activeData}
      activeStage={activeStage}
      runState={runState}
      scenarioLabel={contextScenario.label}
      scenarioId={contextScenarioId}
      selectedOption={selectedOption}
      optionCosts={optionCosts}
      liveRun={currentLiveRun}
      simulationStatus={isSimulating ? "running" : currentLiveRun?.integrationMode === "unreviewed-v2-dev" ? "dev-live" : currentLiveRun ? "live" : simulationError ? "error" : "idle"}
      humanDecision={humanDecision}
      decisionMoment={decisionMoment}
      onDismissMoment={() => setDecisionMoment(null)}
      onStageChange={moveStage}
      onGoldenRun={openGoldenRun}
      onReset={resetDemo}
      toast={toast}
    >
      <StageView
        stage={activeStage}
        appState={runState}
        data={activeData}
        currentScenario={currentScenario}
        scenarioId={scenarioId}
        matrixScenarioId={matrixScenarioId}
        demandShift={demandShift}
        riskThreshold={riskThreshold}
        budgetCeilingUsd={budgetCeilingUsd}
        isDraft={isDraft}
        datasetId={datasetId}
        liveRun={currentLiveRun}
        isSimulating={isSimulating}
        simulationError={simulationError}
        selectedOption={selectedOption}
        humanDecision={humanDecision}
        onScenarioChange={selectScenario}
        onDemandShiftChange={changeDemandShift}
        onRiskThresholdChange={changeRiskThreshold}
        onBudgetCeilingChange={changeBudgetCeiling}
        onRunSimulation={runSimulation}
        onOptionSelect={setSelectedOption}
        onScenarioView={viewMatrixScenario}
        onEvidence={(evidence) => setModal({ kind: "evidence", evidence })}
        onEvidenceStack={() => setModal({ kind: "stack" })}
        onFormula={openFormula}
        onNext={nextStage}
        onPreviewState={previewState}
        onGoldenRun={openGoldenRun}
        onDecision={decide}
        onStageChange={moveStage}
      />
      <DetailModal modal={modal} onClose={() => setModal({ kind: "closed" })} onEvidence={(evidence) => setModal({ kind: "evidence", evidence })} data={activeData} liveRun={currentLiveRun} />
    </AppShell>
  );
}
