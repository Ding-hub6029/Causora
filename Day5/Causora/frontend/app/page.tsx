"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import data from "@/demo_data/causora_day1_mock.json";
import goldenRunJson from "@/golden/golden_run.json";
import type { EvidenceRecord, OptionId } from "@/lib/contracts";
import { buildSimulateRequest, postSimulate } from "@/lib/simulate-api";
import type { AppState, GoldenRun, LiveSimulation, MockData, ModalState, StageId } from "@/lib/types";
import type { BoardroomState, Day4Failure } from "@/lib/day4-types";
import { probeBackendHealth, type BackendHealthState } from "@/lib/golden-health";
import { boardroomIdentity, createBoardroomRequestId, Day4ApiError, isCurrentBoardroomRun, postBoardroom } from "@/lib/boardroom-api";
import { fetchEvidenceRecord } from "@/lib/evidence-api";
import { saveVerifiedGoldenRun, type BrowserHumanDecision, type VerifiedGoldenRun } from "@/lib/golden-cache";
import { loadAvailableVerifiedGoldenRun, type GoldenSource } from "@/lib/golden-bootstrap";
import { validateMockData, validateGoldenRun, verifyGoldenHash } from "@/lib/validation";
import { money } from "@/lib/metrics";
import { AppShell, stages } from "@/components/app-shell";
import { StageView } from "@/components/stage-views";
import { DetailModal } from "@/components/detail-modal";

const mockData = data as MockData;
const goldenRun = goldenRunJson as GoldenRun;
const DEFAULT_RISK_THRESHOLD = 12;
const DEFAULT_BUDGET_CEILING_USD = 480000;
const HUMAN_DECISION_STORAGE_KEY = "causora.human-decision.v1";
const SIMULATION_HEADER_KEYS = ["x-causora-review-status", "x-causora-execution-mode", "x-causora-trace-contract"] as const;

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
  const [humanDecisionRecord, setHumanDecisionRecord] = useState<BrowserHumanDecision | null>(null);
  const humanDecision = humanDecisionRecord?.decision ?? null;
  const [decisionMoment, setDecisionMoment] = useState<"Approved" | "Rejected" | null>(null);
  const [decisionOptionId, setDecisionOptionId] = useState<OptionId>("D1");
  const [liveRun, setLiveRun] = useState<LiveSimulation | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationError, setSimulationError] = useState<string | null>(null);
  const [simulationHeaders, setSimulationHeaders] = useState<Record<string, string>>({});
  const [boardroomState, setBoardroomState] = useState<BoardroomState>({ status: "idle" });
  const [liveEvidenceRecords, setLiveEvidenceRecords] = useState<Record<string, { requestId: string; evidence: EvidenceRecord }>>({});
  const [verifiedGolden, setVerifiedGolden] = useState<VerifiedGoldenRun | null>(null);
  const [cachedGoldenActive, setCachedGoldenActive] = useState(false);
  const [goldenSource, setGoldenSource] = useState<GoldenSource | null>(null);
  const [goldenCacheError, setGoldenCacheError] = useState<string | null>(null);
  const [backendHealth, setBackendHealth] = useState<BackendHealthState>({ status: "checking" });
  const runSequence = useRef(0);
  const latestRequestKey = useRef("");
  const boardroomSequence = useRef(0);
  const evidenceSequence = useRef(0);
  const boardroomAbortRef = useRef<AbortController | null>(null);
  const evidenceAbortRef = useRef<AbortController | null>(null);
  const healthSequence = useRef(0);

  // While the Golden Run is active the UI reads only the frozen snapshot, never the live mock file.
  const activeData: MockData = runState === "golden" ? goldenRun.snapshot : mockData;

  const refreshBackendHealth = useCallback(async () => {
    const sequence = ++healthSequence.current;
    setBackendHealth({ status: "checking" });
    try {
      const health = await probeBackendHealth();
      if (sequence === healthSequence.current) setBackendHealth({ status: "healthy", health, checkedAt: new Date().toISOString() });
    } catch (error) {
      if (sequence !== healthSequence.current) return;
      const failure = error instanceof Error ? error : new Error("The simulation service is not reachable.");
      const code = "code" in failure && ["timeout", "unavailable", "invalid_response", "network", "not_configured"].includes(String(failure.code)) ? failure.code as "timeout" | "unavailable" | "invalid_response" | "network" | "not_configured" : "network";
      setBackendHealth({ status: "waking", message: failure.message, code });
    }
  }, []);

  useEffect(() => {
    void refreshBackendHealth();
    return () => { healthSequence.current += 1; };
  }, [refreshBackendHealth]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 3800);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    let active = true;
    void loadAvailableVerifiedGoldenRun().then((available) => {
      if (active) {
        setVerifiedGolden(available?.run ?? null);
        setGoldenSource(available?.source ?? null);
        setGoldenCacheError(null);
      }
    }).catch((error) => {
      if (active) { setVerifiedGolden(null); setGoldenCacheError(error instanceof Error ? error.message : "Verified Golden cache failed validation."); }
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!decisionMoment) return;
    const timer = window.setTimeout(() => setDecisionMoment(null), 2900);
    return () => window.clearTimeout(timer);
  }, [decisionMoment]);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [activeStage]);

  const currentScenario = useMemo(() => activeData.scenarios.find((scenario) => scenario.id === scenarioId) ?? activeData.scenarios[0], [activeData, scenarioId]);
  const currentMatrixScenario = useMemo(() => activeData.scenarios.find((scenario) => scenario.id === matrixScenarioId) ?? activeData.scenarios[0], [activeData, matrixScenarioId]);
  const contextScenario = activeStage === "matrix" ? currentMatrixScenario : currentScenario;
  const contextScenarioId = contextScenario.id;
  const datasetId = process.env.NEXT_PUBLIC_CAUSORA_DATASET_ID?.trim() || "ds-001";
  const currentRequest = useMemo(() => buildSimulateRequest({ datasetId, scenarios: activeData.scenarios, options: activeData.options, selectedScenarioId: scenarioId, demandShift, riskThresholdPct: riskThreshold, budgetCeilingUsd, seed: activeData.meta.seed }), [activeData, budgetCeilingUsd, datasetId, demandShift, riskThreshold, scenarioId]);
  const currentRequestKey = JSON.stringify(currentRequest);
  latestRequestKey.current = currentRequestKey;
  const matchingLiveRun = liveRun && JSON.stringify(liveRun.request) === currentRequestKey && runState !== "golden" ? liveRun : null;
  const currentLiveRun = cachedGoldenActive && verifiedGolden ? verifiedGolden.liveRun : matchingLiveRun;
  const optionCosts = useMemo(() => Object.fromEntries((currentLiveRun?.response.data.simulation.matrix[contextScenarioId] ?? activeData.simulation.matrix[contextScenarioId]).map((row) => [row.optionId, money(row.expectedTco)])), [activeData, currentLiveRun, contextScenarioId]);
  const isDraft = !currentLiveRun && (demandShift !== currentScenario.demandShock || riskThreshold !== DEFAULT_RISK_THRESHOLD || budgetCeilingUsd !== DEFAULT_BUDGET_CEILING_USD);
  const currentBoardroomRun = boardroomState.status === "ready" && currentLiveRun && isCurrentBoardroomRun(boardroomState.run, currentLiveRun, scenarioId) ? boardroomState.run : null;
  const boardroomFailureIsCurrent = boardroomState.status === "error" && currentLiveRun && boardroomState.identity.simulationId === currentLiveRun.response.data.simulation.simulationId && boardroomState.identity.dataVersion === currentLiveRun.response.data.simulation.dataVersion && boardroomState.identity.scenarioId === scenarioId && boardroomState.identity.simulationRequestId === currentLiveRun.response.requestId;
  const selectedForDecision = currentLiveRun?.response.data.selections[scenarioId];
  const canRecordDecision = !cachedGoldenActive && !isDraft && currentLiveRun?.integrationMode === "reviewed-v2" && currentLiveRun.development?.executionContext.decisionReady === true && !!currentBoardroomRun && selectedForDecision?.status === "selected" && !!selectedForDecision.recommendedOptionId && currentBoardroomRun.response.data.numericGuardrail.passed === true && currentBoardroomRun.response.data.numericGuardrail.rejectedClaims.length === 0;
  const simulationStatus = isSimulating ? "running" : cachedGoldenActive ? "cached-verified" : runState === "golden" ? "saved-example" : currentLiveRun?.integrationMode === "unreviewed-v2-dev" ? "dev-live" : boardroomFailureIsCurrent ? "ai-unavailable" : currentBoardroomRun?.providerMode === "same-family-fallback" ? "same-family-review" : currentBoardroomRun ? "live" : currentLiveRun ? "simulation-only" : simulationError ? "error" : "idle";

  function clearDecisionRecord() {
    setHumanDecisionRecord(null);
    setDecisionMoment(null);
    try { window.localStorage.removeItem(HUMAN_DECISION_STORAGE_KEY); } catch { /* Browser storage may be disabled; in-memory state is still cleared. */ }
  }

  function clearDownstreamState() {
    boardroomSequence.current += 1;
    evidenceSequence.current += 1;
    boardroomAbortRef.current?.abort();
    evidenceAbortRef.current?.abort();
    boardroomAbortRef.current = null;
    evidenceAbortRef.current = null;
    setBoardroomState({ status: "idle" });
    setLiveEvidenceRecords({});
    if (modal.kind === "live-evidence") setModal({ kind: "closed" });
    clearDecisionRecord();
  }

  function invalidateSimulation() {
    clearDownstreamState();
    runSequence.current += 1;
    setIsSimulating(false);
    setLiveRun(null);
    setSimulationError(null);
    setSimulationHeaders({});
    setCachedGoldenActive(false);
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

  async function openSavedExample() {
    try { await verifyGoldenHash(goldenRun); }
    catch { setToast("Saved example integrity validation failed. No decision action is available."); return; }
    invalidateSimulation();
    setRunState("golden");
    setCachedGoldenActive(false);
    setActiveStage("intake");
    setDecisionMoment(null);
    setScenarioId(goldenRun.request.scenario);
    setMatrixScenarioId(goldenRun.request.scenario);
    setDemandShift(goldenRun.snapshot.scenarios.find((scenario) => scenario.id === goldenRun.request.scenario)?.demandShock ?? 0);
    setRiskThreshold(goldenRun.request.riskThreshold);
    setBudgetCeilingUsd(DEFAULT_BUDGET_CEILING_USD);
    setSelectedOption(goldenRun.response.recommendedOptionId);
    setToast(`Saved example ${goldenRun.dataVersion} loaded and integrity-checked. It is not a live or verified E2E run.`);
  }

  /** Any edit leaves the frozen snapshot: the modified state is no longer the verified Golden Run. */
  function leaveGoldenIfNeeded() {
    if (cachedGoldenActive) {
      invalidateSimulation();
      setRunState("ready");
      setToast("The verified Golden snapshot was closed because an assumption changed. Inputs are editable; the cached record remains stored separately.");
      return;
    }
    if (runState !== "golden") return;
    setRunState("ready");
    setToast("You changed the inputs, so the saved-example label was removed. The workspace is back on editable local inputs.");
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
    setCachedGoldenActive(false);
    setDecisionMoment(null);
    setToast("The local decision workspace has been reset.");
  }

  function previewState(state: AppState) {
    if (currentLiveRun) { setToast("Prototype states cannot replace or conceal a validated live run. Use Matrix or Formula Trace instead."); return; }
    setRunState(state);
    clearDecisionRecord();
    setDecisionMoment(null);
    setToast(`${state.charAt(0).toUpperCase() + state.slice(1)} state preview enabled for ${activeStage}.`);
  }

  function selectScenario(id: string) {
    const scenarioChanged = id !== scenarioId;
    leaveGoldenIfNeeded();
    const nextShift = mockData.scenarios.find((scenario) => scenario.id === id)?.demandShock ?? 0;
    if (nextShift !== demandShift) invalidateSimulation();
    else if (scenarioChanged) clearDownstreamState();
    setScenarioId(id);
    setMatrixScenarioId(id);
    setDemandShift(nextShift);
    setDecisionMoment(null);
  }

  function viewMatrixScenario(id: string) {
    setMatrixScenarioId(id);
  }

  function changeDemandShift(value: number) {
    leaveGoldenIfNeeded();
    invalidateSimulation();
    setDemandShift(value);
    setDecisionMoment(null);
  }

  function changeRiskThreshold(value: number) {
    leaveGoldenIfNeeded();
    invalidateSimulation();
    setRiskThreshold(value);
    setDecisionMoment(null);
  }

  function changeBudgetCeiling(value: number) {
    leaveGoldenIfNeeded();
    invalidateSimulation();
    setBudgetCeilingUsd(Number.isFinite(value) ? Math.max(0, Math.round(value)) : 0);
    setDecisionMoment(null);
  }

  async function runSimulation() {
    if (backendHealth.status !== "healthy") { setToast("Live simulation is unavailable until GET /health confirms the service is ready. Retry the health check or use the clearly labelled local fallback."); return; }
    if (runState === "golden") { setToast("The saved example is read-only. Change an assumption to return to the editable workspace before requesting a simulation."); return; }
    const request = currentRequest;
    const requestKey = currentRequestKey;
    const retainedRun = currentLiveRun;
    const sequence = ++runSequence.current;
    clearDownstreamState();
    setCachedGoldenActive(false);
    setSimulationError(null);
    setIsSimulating(true);
    setRunState("ready");
    const capturedHeaders: Record<string, string> = {};
    try {
      const result = await postSimulate(request, async (input, init) => {
        const response = await fetch(input, init);
        for (const key of SIMULATION_HEADER_KEYS) {
          const value = response.headers.get(key);
          if (value !== null) capturedHeaders[key] = value;
        }
        return response;
      });
      if (sequence !== runSequence.current || latestRequestKey.current !== requestKey) return;
      const response = result.response;
      setLiveRun({ request, response, integrationMode: result.integrationMode, development: result.development, receivedAt: new Date().toISOString() });
      setSimulationHeaders(capturedHeaders);
      setBoardroomState({ status: "idle" });
      const selection = response.data.selections[scenarioId];
      if (selection?.status === "selected") setSelectedOption(selection.recommendedOptionId);
      setToast(result.integrationMode === "unreviewed-v2-dev" ? `UNREVIEWED DEVELOPMENT ONLY · ${response.data.simulation.monteCarloRuns.toLocaleString("en-US")} Monte Carlo runs · NOT DECISION-READY · no approval.` : `Live /api/simulate response validated · ${response.data.simulation.monteCarloRuns.toLocaleString("en-US")} runs · seed ${response.data.simulation.seed}.`);
    } catch (error) {
      if (sequence !== runSequence.current || latestRequestKey.current !== requestKey) return;
      const message = error instanceof Error ? error.message : "Simulation request failed.";
      setSimulationError(message);
      setToast(retainedRun ? "New simulation was not applied. The previous validated live Matrix and Formula Trace remain available." : "Live simulation was not applied. The saved Day 2 example remains clearly labelled.");
    } finally {
      if (sequence === runSequence.current) setIsSimulating(false);
    }
  }

  function isSameActiveRun(run: LiveSimulation, requestKey: string): boolean {
    const active = cachedGoldenActive ? verifiedGolden?.liveRun : liveRun;
    if (!active || active.response.requestId !== run.response.requestId || JSON.stringify(active.request) !== JSON.stringify(run.request)) return false;
    return cachedGoldenActive || latestRequestKey.current === requestKey;
  }

  function asDay4Failure(error: unknown, requestId?: string): Day4Failure {
    if (error instanceof Day4ApiError) return { code: error.code, message: error.message, requestId: error.requestId ?? requestId, retryable: error.retryable };
    return { code: "unknown", message: error instanceof Error ? error.message : "The request failed unexpectedly.", requestId, retryable: true };
  }

  async function runBoardroom() {
    const run = currentLiveRun;
    if (!run) { setToast("Boardroom is unavailable because there is no current validated simulation."); return; }
    const requestedScenarioId = scenarioId;
    const requestKey = JSON.stringify(run.request);
    const identity = boardroomIdentity(run, requestedScenarioId);
    clearDownstreamState();
    const sequence = ++boardroomSequence.current;
    const requestId = createBoardroomRequestId();
    const controller = new AbortController();
    boardroomAbortRef.current = controller;
    setBoardroomState({ status: "loading", identity, requestId });
    try {
      const result = await postBoardroom(run, requestedScenarioId, fetch, controller.signal, requestId);
      if (sequence !== boardroomSequence.current || !isSameActiveRun(run, requestKey) || scenarioId !== requestedScenarioId) return;
      setBoardroomState({ status: "ready", run: result });
      setToast(result.providerMode === "same-family-fallback" ? "Boardroom validated with an explicitly labelled same-family fallback; the simulation was not rerun." : "Matching Boardroom, Critic, and Numeric Guardrail response validated.");
    } catch (error) {
      if (sequence !== boardroomSequence.current || controller.signal.aborted || !isSameActiveRun(run, requestKey) || scenarioId !== requestedScenarioId) return;
      const failure = asDay4Failure(error, requestId);
      setBoardroomState({ status: "error", identity, failure });
      setToast(`Boardroom unavailable (${failure.code}). The validated Matrix and Formula Trace remain available.`);
    } finally {
      if (boardroomAbortRef.current === controller) boardroomAbortRef.current = null;
    }
  }

  async function openLiveEvidence(evidenceId: string) {
    const run = currentLiveRun;
    const boardroom = boardroomState.status === "ready" && run && isCurrentBoardroomRun(boardroomState.run, run, scenarioId) ? boardroomState.run : null;
    // A clearly marked development run may inspect the physical source route to
    // verify a PDF locator, but it cannot call Boardroom, create a Brief, cache
    // a Golden record, or become decision-ready. Reviewed runs still require a
    // matching validated Boardroom response before Evidence is used in G4 flow.
    const developmentInspection = run?.integrationMode === "unreviewed-v2-dev";
    if (!run || (!boardroom && !developmentInspection)) { setToast("Live Evidence requires a matching validated Boardroom response. Saved example evidence is not substituted."); return; }
    const requestedScenarioId = scenarioId;
    const requestKey = JSON.stringify(run.request);
    const identity = boardroomIdentity(run, requestedScenarioId);
    if (cachedGoldenActive && verifiedGolden) {
      const cached = verifiedGolden.evidenceRecords.find((item) => item.evidence.id === evidenceId);
      if (!cached) {
        setModal({ kind: "live-evidence", view: { state: "error", evidenceId, identity, failure: { code: "not_found", message: "This cited record is absent from the complete Golden Evidence set; no live lookup was attempted.", retryable: false } } });
        return;
      }
      setModal({ kind: "live-evidence", view: { state: "ready", evidence: cached.evidence, identity, requestId: cached.requestId, source: "verified-cache" } });
      return;
    }
    const sequence = ++evidenceSequence.current;
    evidenceAbortRef.current?.abort();
    const controller = new AbortController();
    evidenceAbortRef.current = controller;
    setModal({ kind: "live-evidence", view: { state: "loading", evidenceId, identity } });
    try {
      const result = await fetchEvidenceRecord(evidenceId, run.response.data.simulation.dataVersion, fetch, controller.signal);
      if (sequence !== evidenceSequence.current || controller.signal.aborted || !isSameActiveRun(run, requestKey) || scenarioId !== requestedScenarioId) return;
      const nextRecords = { ...liveEvidenceRecords, [evidenceId]: { requestId: result.requestId, evidence: result.evidence } };
      setLiveEvidenceRecords(nextRecords);
      setModal({ kind: "live-evidence", view: { state: "ready", evidence: result.evidence, identity, requestId: result.requestId, source: "live" } });
      if (humanDecisionRecord && boardroomState.status === "ready" && !cachedGoldenActive) void cacheCompleteRun(run, boardroomState.run, nextRecords, humanDecisionRecord);
    } catch (error) {
      if (sequence !== evidenceSequence.current || controller.signal.aborted || !isSameActiveRun(run, requestKey) || scenarioId !== requestedScenarioId) return;
      setModal({ kind: "live-evidence", view: { state: "error", evidenceId, identity, failure: asDay4Failure(error) } });
    } finally {
      if (evidenceAbortRef.current === controller) evidenceAbortRef.current = null;
    }
  }

  async function cacheCompleteRun(run: LiveSimulation, boardroom: Extract<BoardroomState, { status: "ready" }>["run"], records: Record<string, { requestId: string; evidence: EvidenceRecord }>, decision: BrowserHumanDecision) {
    const expectedIds = [...new Set(boardroom.response.data.criticIssues.flatMap((issue) => issue.evidenceIds))];
    if (!expectedIds.length || expectedIds.some((id) => !records[id])) {
      setGoldenCacheError("Not cached yet: open and validate every Evidence ID cited by this Boardroom response, then record/reconfirm the human choice.");
      return;
    }
    try {
      const digest = await saveVerifiedGoldenRun(run, boardroom, new Headers(simulationHeaders), expectedIds.map((id) => records[id]), decision);
      const available = await loadAvailableVerifiedGoldenRun();
      if (!available || available.source !== "browser-cache") throw new Error("The cache write could not be read back.");
      setVerifiedGolden(available.run);
      setGoldenSource(available.source);
      setGoldenCacheError(null);
      setToast(`Complete reviewed E2E cached and revalidated · SHA-256 ${digest.slice(0, 16)}…`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Golden cache validation failed.";
      setGoldenCacheError(message);
    }
  }

  async function exportVerifiedGoldenRun() {
    try {
      const available = await loadAvailableVerifiedGoldenRun();
      if (!available) throw new Error("No complete verified Golden record is available.");
      const { run: verified, json: raw } = available;
      const url = URL.createObjectURL(new Blob([raw], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `causora-verified-golden-${verified.liveRun.response.data.simulation.simulationId}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setToast("Verified Golden snapshot exported with its SHA-256 and complete same-run evidence.");
    } catch (error) {
      setGoldenCacheError(error instanceof Error ? error.message : "Golden export failed.");
    }
  }

  async function decide(decision: string) {
    if (decision !== "Approved" && decision !== "Rejected") return;
    if (cachedGoldenActive) { setToast("Verified Golden snapshots are read-only; the stored human decision cannot be overwritten."); return; }
    const run = currentLiveRun;
    const boardroom = boardroomState.status === "ready" && run && isCurrentBoardroomRun(boardroomState.run, run, scenarioId) ? boardroomState.run : null;
    const selection = run?.response.data.selections[scenarioId];
    if (!run || run.integrationMode !== "reviewed-v2" || run.development?.executionContext.decisionReady !== true || !boardroom || !selection || selection.status !== "selected" || !selection.recommendedOptionId) {
      setToast("Human decision blocked: a reviewed, decision-ready Simulation and matching validated Boardroom response are required.");
      return;
    }
    const record: BrowserHumanDecision = { decision, recordedAt: new Date().toISOString(), scope: "browser-local-only", identity: boardroom.identity, optionId: selection.recommendedOptionId };
    setHumanDecisionRecord(record);
    setDecisionOptionId(selection.recommendedOptionId);
    setDecisionMoment(decision);
    try { window.localStorage.setItem(HUMAN_DECISION_STORAGE_KEY, JSON.stringify(record)); } catch { /* The in-memory browser-local record remains visible if storage is unavailable. */ }
    setGoldenCacheError(null);
    const expectedEvidenceIds = [...new Set(boardroom.response.data.criticIssues.flatMap((issue) => issue.evidenceIds))];
    if (run.integrationMode === "reviewed-v2" && expectedEvidenceIds.length && expectedEvidenceIds.every((id) => liveEvidenceRecords[id])) {
      await cacheCompleteRun(run, boardroom, liveEvidenceRecords, record);
    } else {
      setGoldenCacheError(expectedEvidenceIds.length ? "The local choice is recorded. Verified Golden caching waits until every cited live Evidence record is loaded and validated." : "The local choice is recorded, but no Evidence citation exists to complete a verified Golden record.");
      setToast(`${decision} recorded only in this browser for ${selection.recommendedOptionId} · no supplier action or external approval occurred.`);
    }
  }

  function closeModal() {
    if (modal.kind === "live-evidence" && modal.view.state === "loading") {
      evidenceSequence.current += 1;
      evidenceAbortRef.current?.abort();
      evidenceAbortRef.current = null;
    }
    setModal({ kind: "closed" });
  }

  async function openVerifiedGoldenRun() {
    try {
      const available = await loadAvailableVerifiedGoldenRun();
      if (!available) { setToast("No complete verified Golden E2E run is available in this site bundle or browser cache."); return; }
      const verified = available.run;
      const scenario = verified.liveRun.request.scenarios.find((item) => item.id === verified.boardroomRun.identity.scenarioId);
      if (!scenario) throw new Error("Cached Golden scenario is missing from the validated request.");
      invalidateSimulation();
      setRunState("ready");
      setLiveRun(null);
      setSimulationError(null);
      setIsSimulating(false);
      setCachedGoldenActive(true);
      setVerifiedGolden(verified);
      setGoldenSource(available.source);
      setBoardroomState({ status: "ready", run: verified.boardroomRun });
      setLiveEvidenceRecords(Object.fromEntries(verified.evidenceRecords.map((item) => [item.evidence.id, item])));
      setScenarioId(scenario.id);
      setMatrixScenarioId(scenario.id);
      setDemandShift(scenario.demandShock);
      setRiskThreshold(verified.liveRun.request.riskThreshold * 100);
      setBudgetCeilingUsd(verified.liveRun.request.budgetCeilingUsd);
      setSelectedOption(verified.humanDecision.optionId);
      setHumanDecisionRecord(verified.humanDecision);
      setDecisionOptionId(verified.humanDecision.optionId);
      setActiveStage("brief");
      setGoldenCacheError(null);
      setToast(`Verified Golden loaded · SHA-256 ${verified.sha256.slice(0, 16)}… · read-only; no API request was made.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Verified Golden cache validation failed.";
      setGoldenCacheError(message);
      setToast(`Golden cache rejected: ${message}`);
    }
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
      goldenEvidenceRecords={verifiedGolden?.evidenceRecords ?? []}
      simulationStatus={simulationStatus}
      humanDecision={humanDecision}
      decisionMoment={decisionMoment}
      decisionOptionId={decisionOptionId}
      boardroomState={boardroomState}
      cachedGoldenActive={cachedGoldenActive}
      hasVerifiedGolden={!!verifiedGolden}
      goldenSource={goldenSource}
      backendHealth={backendHealth}
      onDismissMoment={() => setDecisionMoment(null)}
      onStageChange={moveStage}
      onGoldenRun={openSavedExample}
      onOpenVerifiedGolden={openVerifiedGoldenRun}
      onHealthCheck={refreshBackendHealth}
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
        decisionScenarioId={scenarioId}
        demandShift={demandShift}
        riskThreshold={riskThreshold}
        budgetCeilingUsd={budgetCeilingUsd}
        isDraft={isDraft}
        datasetId={datasetId}
        liveRun={currentLiveRun}
        isSimulating={isSimulating}
        serviceReady={backendHealth.status === "healthy"}
        simulationError={simulationError}
        boardroomState={boardroomState}
        canRecordDecision={canRecordDecision}
        cachedGoldenActive={cachedGoldenActive}
        hasVerifiedGolden={!!verifiedGolden}
        goldenCacheError={goldenCacheError}
        selectedOption={selectedOption}
        humanDecision={humanDecision}
        onScenarioChange={selectScenario}
        onDemandShiftChange={changeDemandShift}
        onRiskThresholdChange={changeRiskThreshold}
        onBudgetCeilingChange={changeBudgetCeiling}
        onRunSimulation={runSimulation}
        onOptionSelect={setSelectedOption}
        onScenarioView={viewMatrixScenario}
        onEvidence={(evidence) => {
          if (currentLiveRun) void openLiveEvidence(evidence.id);
          else setModal({ kind: "evidence", evidence });
        }}
        onEvidenceStack={() => setModal({ kind: "stack" })}
        onFormula={openFormula}
        onNext={nextStage}
        onPreviewState={previewState}
        onGoldenRun={openSavedExample}
        onOpenVerifiedGolden={openVerifiedGoldenRun}
        onExportVerifiedGolden={exportVerifiedGoldenRun}
        onDecision={decide}
        onRunBoardroom={runBoardroom}
        onRetryBoardroom={runBoardroom}
        onLiveEvidence={openLiveEvidence}
        onStageChange={moveStage}
      />
      <DetailModal modal={modal} onClose={closeModal} onRetryEvidence={() => { if (modal.kind === "live-evidence" && modal.view.state !== "ready") void openLiveEvidence(modal.view.evidenceId); }} onEvidence={(evidence) => {
        if (currentLiveRun) void openLiveEvidence(evidence.id);
        else setModal({ kind: "evidence", evidence });
      }} data={activeData} liveRun={currentLiveRun} />
    </AppShell>
  );
}
