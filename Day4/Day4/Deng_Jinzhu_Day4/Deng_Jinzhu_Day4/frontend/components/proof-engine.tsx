import { AnimatePresence, motion, useMotionValue, useReducedMotion, useSpring } from "framer-motion";
import { ArrowDownRight, ArrowUpRight, Check, FileText, Fingerprint, GitBranch, LockKeyhole, ScanLine, ShieldCheck, X } from "lucide-react";
import type { PointerEvent } from "react";
import type { OptionId } from "@/lib/contracts";
import type { LiveSimulation, MockData, StageId } from "@/lib/types";
import type { BoardroomState } from "@/lib/day4-types";
import { isCurrentBoardroomRun } from "@/lib/boardroom-api";
import { percent } from "@/lib/metrics";

const narrative: Record<StageId, { eyebrow: string; top: string; highlight: string; detail: string; signal: string }> = {
  intake: {
    eyebrow: "THE PROOF ENGINE / 01",
    top: "From evidence",
    highlight: "to a decision.",
    detail: "One contract clause can change a 24-month choice. Watch the claim travel from source to constraint to comparison.",
    signal: "SOURCE CAPTURED"
  },
  scenario: {
    eyebrow: "THE PROOF ENGINE / 02",
    top: "A clause becomes",
    highlight: "a constraint.",
    detail: "The notice window, minimum purchase share and renewal premium are separated from external demand pressure.",
    signal: "VARIABLES MAPPED"
  },
  matrix: {
    eyebrow: "THE PROOF ENGINE / 03",
    top: "Three options.",
    highlight: "One clear choice.",
    detail: "D0, D1 and D2 are compared under the selected scenario. Values remain local mock results, never model-written numbers.",
    signal: "OPTIONS COMPARED"
  },
  boardroom: {
    eyebrow: "THE PROOF ENGINE / 04",
    top: "Let the numbers",
    highlight: "be challenged.",
    detail: "Different roles examine different slices. The Critic connects renewal, demand decline and cash pressure.",
    signal: "REVIEW IN PROGRESS"
  },
  brief: {
    eyebrow: "THE PROOF ENGINE / 05",
    top: "The last word",
    highlight: "is human.",
    detail: "Every recommendation carries its evidence and computed references. Approve, reject or change the assumptions.",
    signal: "AWAITING HUMAN DECISION"
  }
};

const order: StageId[] = ["intake", "scenario", "matrix", "boardroom", "brief"];

export function ProofEngine({ data, activeStage, scenarioLabel, scenarioId, selectedOption, optionCosts, liveRun, boardroomState, decision, decisionOptionId, onStageChange }: {
  data: MockData;
  activeStage: StageId;
  scenarioLabel: string;
  scenarioId: string;
  selectedOption: OptionId;
  optionCosts: Record<string, string>;
  liveRun: LiveSimulation | null;
  boardroomState: BoardroomState;
  decision: string | null;
  decisionOptionId: OptionId;
  onStageChange: (stage: StageId) => void;
}) {
  const reduceMotion = useReducedMotion();
  const rawX = useMotionValue(0);
  const rawY = useMotionValue(0);
  const springX = useSpring(rawX, { stiffness: 85, damping: 25, mass: 0.75 });
  const springY = useSpring(rawY, { stiffness: 85, damping: 25, mass: 0.75 });
  const index = order.indexOf(activeStage);
  const liveSelection = liveRun?.response.data.selections[scenarioId];
  const isUnreviewedDev = liveRun?.integrationMode === "unreviewed-v2-dev";
  const currentBoardroom = liveRun && boardroomState.status === "ready" && isCurrentBoardroomRun(boardroomState.run, liveRun, scenarioId) ? boardroomState.run : null;
  const currentBoardroomError = liveRun && boardroomState.status === "error" && boardroomState.identity.simulationId === liveRun.response.data.simulation.simulationId && boardroomState.identity.dataVersion === liveRun.response.data.simulation.dataVersion && boardroomState.identity.scenarioId === scenarioId && boardroomState.identity.simulationRequestId === liveRun.response.requestId;
  const story = isUnreviewedDev && activeStage === "matrix" ? { ...narrative.matrix, highlight: "No reviewed choice.", detail: `UNREVIEWED DEVELOPMENT ONLY. ${liveRun.response.data.simulation.monteCarloRuns.toLocaleString("en-US")} Monte Carlo runs are shown for integration inspection; no result is decision-ready or a formal recommendation.`, signal: "UNREVIEWED DEV · NOT DECISION-READY" }
    : liveRun && activeStage === "matrix" ? { ...narrative.matrix, detail: `Validated POST /api/simulate response for dataset ${liveRun.request.datasetId}: ${liveRun.response.data.simulation.monteCarloRuns.toLocaleString("en-US")} Monte Carlo runs, seed ${liveRun.response.data.simulation.seed}. The nine matrix cells are server values.`, signal: "LIVE API RESPONSE VALIDATED" }
    : liveRun && activeStage === "boardroom" ? { ...narrative.boardroom, detail: currentBoardroom ? `Validated ${currentBoardroom.providerMode} Boardroom and complete Critic response are bound to ${currentBoardroom.identity.simulationId} · ${currentBoardroom.identity.scenarioId}.` : boardroomState.status === "loading" ? "The matching Boardroom request is running; the validated Matrix remains available." : currentBoardroomError ? "AI review is unavailable. The successful Matrix and Formula Trace are retained; no saved Boardroom sample is substituted." : isUnreviewedDev ? "This simulation is not decision-ready. The formal Boardroom route remains closed while required human and release Gates are pending." : "Run the Boardroom for this exact simulation and scenario; no saved sample is substituted.", signal: currentBoardroom ? "LIVE BOARDROOM VALIDATED" : boardroomState.status === "loading" ? "BOARDROOM IN PROGRESS" : currentBoardroomError ? "AI REVIEW UNAVAILABLE · MATRIX RETAINED" : "WAITING FOR MATCHING BOARDROOM" }
    : liveRun && activeStage === "brief" ? { ...narrative.brief, detail: currentBoardroom ? "The Brief is bound to the same simulation, dataVersion, scenario, Critic, and Numeric Guardrail. Final choice stays browser-local and human-controlled." : "No formal Brief is shown until a validated Boardroom response matches this exact simulation and scenario.", signal: currentBoardroom ? "MATCHED BRIEF · HUMAN DECISION" : "WAITING FOR MATCHING BOARDROOM" }
    : narrative[activeStage];
  const isResolved = activeStage === "brief" && (decision === "Approved" || decision === "Rejected");
  const source = data.evidence[0];
  const sourceQuote = source.quote.length > 52 ? `${source.quote.slice(0, 52).trimEnd()}...` : source.quote;
  const noticeVariable = data.variables.find((item) => item.key === "renewal_locked");
  const minShare = data.evidence.find((item) => item.id === "EV-024");
  const premium = data.evidence.find((item) => item.id === "EV-021");
  const recommended = liveRun ? (!isUnreviewedDev && liveSelection?.status === "selected" ? liveSelection.recommendedOptionId : null) : data.brief.recommendedOptionId;
  const proofOptions = liveRun?.request.options ?? data.options;

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (reduceMotion || event.pointerType !== "mouse") return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const relativeX = (event.clientX - bounds.left) / bounds.width - 0.5;
    const relativeY = (event.clientY - bounds.top) / bounds.height - 0.5;
    rawX.set(relativeY * -5);
    rawY.set(relativeX * 7);
  }

  return (
    <section className={`proof-engine proof-${activeStage} ${isResolved ? `proof-${decision?.toLowerCase()}` : ""}`} aria-label="Evidence to decision visual narrative">
      <div className="proof-atmosphere" aria-hidden="true" />
      <div className="proof-grid" aria-hidden="true" />
      <div className="proof-copy">
        <div className="proof-kicker"><span className="proof-kicker-icon"><Fingerprint size={15} /></span><span>{story.eyebrow}</span><i /></div>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={activeStage} initial={{ opacity: 0, y: 13 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: reduceMotion ? 0.05 : 0.30, ease: [0.22, 1, 0.36, 1] }}>
            <h2>{story.top}<br /><em>{story.highlight}</em></h2>
            <p>{story.detail}</p>
          </motion.div>
        </AnimatePresence>
        <div className="proof-controls" role="group" aria-label="Follow the evidence chain">
          <button type="button" onClick={() => onStageChange("intake")} className={activeStage === "intake" ? "on" : ""} aria-pressed={activeStage === "intake"}><span>01</span> Evidence</button>
          <span className={`proof-connector ${index > 0 ? "lit" : ""}`} aria-hidden="true" />
          <button type="button" onClick={() => onStageChange("scenario")} className={activeStage === "scenario" ? "on" : ""} aria-pressed={activeStage === "scenario"}><span>02</span> Variable</button>
          <span className={`proof-connector ${index > 1 ? "lit" : ""}`} aria-hidden="true" />
          <button type="button" onClick={() => onStageChange("matrix")} className={activeStage === "matrix" ? "on" : ""} aria-pressed={activeStage === "matrix"}><span>03</span> Matrix</button>
        </div>
      </div>

      <div className="proof-viewport" onPointerMove={handlePointerMove} onPointerLeave={() => { rawX.set(0); rawY.set(0); }}>
        <motion.div className="proof-scene" style={{ rotateX: springX, rotateY: springY }}>
          <div className="proof-halo halo-a" aria-hidden="true" /><div className="proof-halo halo-b" aria-hidden="true" />
          <svg className="proof-trajectory" viewBox="0 0 680 360" fill="none" preserveAspectRatio="none" aria-hidden="true">
            <path className="trajectory-base" d="M216 180 C218 172 222 153 225 145 M453 145 C458 152 462 171 465 180" />
            <motion.path className="trajectory-signal" d="M216 180 C218 172 222 153 225 145 M453 145 C458 152 462 171 465 180" initial={false} animate={{ pathLength: [0.08, 0.5, 1, 1, 1][index] }} transition={{ duration: reduceMotion ? 0.05 : 0.8, ease: [0.16, 1, 0.3, 1] }} />
          </svg>
          <motion.div className={`proof-plane source ${index === 0 ? "is-primary" : ""}`} animate={{ x: 0, y: index === 0 ? -6 : 5, rotateY: 6, rotateZ: -2, scale: index === 0 ? 1.025 : 0.985, opacity: index > 2 ? 0.72 : 1 }} transition={reduceMotion ? { duration: 0.05 } : { type: "spring", stiffness: 115, damping: 22 }}>
            <div className="plane-top"><span><FileText size={13} /> {liveRun ? "SAVED DEMO SOURCE · NOT LIVE" : "SOURCE / PDF"}</span><ScanLine size={14} /></div>
            <div className="plane-rule"><span>{source.id}</span><b>{source.extractedValue}</b></div>
            <p>“{sourceQuote}”</p>
            <div className="plane-foot"><span>{source.sourceFile}</span><span>p. {source.page}</span></div>
          </motion.div>
          <motion.div className={`proof-plane variable ${index === 1 ? "is-primary" : ""}`} animate={{ x: 0, y: index === 1 ? -8 : 0, rotateY: -5, rotateZ: 2, scale: index === 1 ? 1.025 : 0.985, opacity: index === 0 ? 0.88 : 1 }} transition={reduceMotion ? { duration: 0.05 } : { type: "spring", stiffness: 115, damping: 22 }}>
            <div className="plane-top"><span><GitBranch size={13} /> {liveRun ? "SAVED DEMO CONTRACT · NOT LIVE" : "BUSINESS VARIABLE"}</span><ArrowDownRight size={14} /></div>
            <div className="plane-rule"><span>NOTICE WINDOW</span><b>{data.contract.renewalNoticeDays}d</b></div>
            <div className="plane-variable-row"><span>minimum share A</span><strong>{minShare?.extractedValue ?? percent(data.contract.minPurchaseShareA)}</strong></div>
            <div className="plane-variable-row"><span>renewal premium</span><strong>+{premium?.extractedValue ?? percent(data.contract.renewalPriceIncreasePct)}</strong></div>
            <div className="plane-foot"><span>{liveRun ? "SAVED EXAMPLE · NOT IN LIVE DTO" : "CONTRACT → MODEL"}</span><LockKeyhole size={12} /></div>
          </motion.div>
          <motion.div className={`proof-plane matrix ${index >= 2 ? "is-primary" : ""}`} animate={{ x: 0, y: index >= 2 ? -7 : 5, rotateY: -6, rotateZ: 2, scale: index >= 2 ? 1.025 : 0.985, opacity: index < 2 ? 0.84 : 1 }} transition={reduceMotion ? { duration: 0.05 } : { type: "spring", stiffness: 115, damping: 22 }}>
            <div className="plane-top"><span><ShieldCheck size={13} /> OPTION × SCENARIO</span><ArrowUpRight size={14} /></div>
            <div className="plane-caption">{scenarioLabel.toUpperCase()} <span>· {isUnreviewedDev ? "UNREVIEWED DEV" : liveRun ? "LIVE API" : "DAY 2 MOCK"}</span></div>
            {proofOptions.map((option) => <div className={`plane-matrix-row ${option.id === recommended ? "selected" : ""} ${liveRun && option.id === selectedOption ? "inspected" : ""}`} key={option.id}><span>{option.id} / {option.id === "D0" ? "KEEP A" : option.id === "D1" ? "DIVERSIFY" : "EXIT A"}</span><b>{optionCosts[option.id]}</b></div>)}
            <div className="plane-foot"><span>{isUnreviewedDev ? "CONSTRAINT SCREEN · NO RECOMMENDATION" : liveRun ? (recommended ? `SELECTED ${recommended} · ${liveRun.response.data.simulation.monteCarloRuns.toLocaleString("en-US")} RUNS` : "NO FEASIBLE OPTION") : "NO FOURTH OPTION"}</span><Check size={12} /></div>
          </motion.div>
          <AnimatePresence>
            {isResolved && <motion.div className={`proof-resolution ${decision?.toLowerCase()}`} initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.72, rotate: -12 }} animate={{ opacity: 1, scale: 1, rotate: 0 }} exit={{ opacity: 0, scale: 0.8 }} transition={{ type: "spring", stiffness: 175, damping: 19 }} role="status"><span>{decision === "Approved" ? <Check size={27} /> : <X size={27} />}</span><b>{decision === "Approved" ? "HUMAN APPROVED" : "HUMAN REJECTED"}</b><small>{decisionOptionId} · browser-local only · no external action</small></motion.div>}
          </AnimatePresence>
        </motion.div>
      </div>
      <div className="proof-mobile-stage" aria-label="Inspectable evidence chain">
        <button type="button" className={index === 0 ? "active" : ""} onClick={() => onStageChange("intake")}><span>01 / EVIDENCE</span><strong>{source.id}</strong><small>{source.extractedValue} · contract p. {source.page}</small></button>
        <button type="button" className={index === 1 ? "active" : ""} onClick={() => onStageChange("scenario")}><span>02 / VARIABLE</span><strong>{minShare?.extractedValue ?? "—"} min A</strong><small>{noticeVariable ? `${noticeVariable.name}: ${noticeVariable.value}` : "Constraint applied"}</small></button>
        <button type="button" className={index >= 2 ? "active" : ""} onClick={() => onStageChange("matrix")}><span>03 / MATRIX</span><strong>{isUnreviewedDev ? "Unreviewed dev · no recommendation" : recommended ? `${recommended} · ${optionCosts[recommended]}` : "No feasible option"}</strong><small>{scenarioLabel} · {isUnreviewedDev ? "not decision-ready" : liveRun ? "live API" : "Day 2 mock"}</small></button>
        {isResolved && <div className={`proof-mobile-resolution ${decision?.toLowerCase()}`} role="status">{decision === "Approved" ? "✓" : "×"} {decisionOptionId} · browser-local {decision?.toLowerCase()}</div>}
      </div>
      <div className="proof-footer"><span><i className="signal-beacon" />{isResolved ? `${decision?.toUpperCase()} BY HUMAN REVIEWER` : story.signal}</span><span>DATA VERSION / {liveRun?.response.data.simulation.dataVersion ?? data.meta.dataVersion} <b>·</b> {liveRun ? `${liveRun.response.data.simulation.monteCarloRuns.toLocaleString("en-US")} RUNS · SEED ${liveRun.response.data.simulation.seed} · DATASET ${liveRun.request.datasetId}` : "NO LIVE COMPUTATION"}</span></div>
    </section>
  );
}
