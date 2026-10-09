import { AnimatePresence, motion } from "framer-motion";
import { ArrowUpRight, ChevronRight, X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { Evidence, LiveSimulation, ModalState, MockData } from "@/lib/types";
import type { LiveEvidenceModal } from "@/lib/day4-types";
import { cell, moneyExact, money, percent, renderGuarded, signedMoney, signedPp, sumBreakdown, units } from "@/lib/metrics";
import { evidenceSourceHref } from "@/lib/evidence-api";
import { EvidencePdfViewer } from "./evidence-pdf-viewer";
import { Metric, SectionLabel, VerifiedLine } from "./ui";

const FOCUSABLE = 'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

function useDialogFocus(isOpen: boolean, modalKey: string, onClose: () => void) {
  const dialogRef = useRef<HTMLElement | null>(null);
  const restoreRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!isOpen) return;
    restoreRef.current = document.activeElement as HTMLElement | null;
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") { event.preventDefault(); onCloseRef.current(); return; }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!dialogRef.current.contains(document.activeElement)) { event.preventDefault(); (event.shiftKey ? last : first).focus(); }
      else if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }

    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("keydown", handleKey);
      restoreRef.current?.focus?.();
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const frame = window.requestAnimationFrame(() => {
      const first = dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE);
      (first ?? dialogRef.current)?.focus();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [isOpen, modalKey]);

  return dialogRef;
}

export function DetailModal({ modal, onClose, onEvidence, onRetryEvidence, data, liveRun }: { modal: ModalState; onClose: () => void; onEvidence: (evidence: Evidence) => void; onRetryEvidence: () => void; data: MockData; liveRun: LiveSimulation | null }) {
  const isOpen = modal.kind !== "closed";
  const modalKey = modal.kind === "evidence" ? modal.evidence.id : modal.kind === "live-evidence" ? `${modal.view.state}:${modal.view.state === "ready" ? modal.view.evidence.id : modal.view.evidenceId}` : modal.kind;
  const dialogRef = useDialogFocus(isOpen, modalKey, onClose);
  const title = modal.kind === "evidence" || modal.kind === "live-evidence" ? "Evidence detail" : modal.kind === "stack" ? "Evidence stack" : "Formula trace";

  return <AnimatePresence>{isOpen && <motion.div className="modal-layer" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
    <button type="button" className="modal-backdrop" onClick={onClose} aria-label="Close dialog" tabIndex={-1} />
    <motion.section ref={dialogRef} className="detail-modal" role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} initial={{ opacity: 0, y: 18, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 12, scale: 0.98 }} transition={{ type: "spring", duration: 0.42, bounce: 0.1 }}>
      <button type="button" className="modal-close" onClick={onClose} aria-label="Close dialog"><X size={18} /></button>
      {modal.kind === "evidence" && <EvidenceBody evidence={modal.evidence} origin={modal.origin ?? "saved-example"} identity={modal.identity} />}
      {modal.kind === "live-evidence" && <LiveEvidenceBody view={modal.view} onRetry={onRetryEvidence} />}
      {modal.kind === "stack" && <StackBody data={data} onEvidence={onEvidence} />}
      {modal.kind === "formula" && <FormulaBody data={data} scenarioId={modal.scenarioId} optionId={modal.optionId} liveRun={liveRun} />}
    </motion.section>
  </motion.div>}</AnimatePresence>;
}

function LiveEvidenceBody({ view, onRetry }: { view: LiveEvidenceModal; onRetry: () => void }) {
  if (view.state === "loading") return <>
    <SectionLabel index="EV" label="Live evidence lookup" />
    <h2>{view.evidenceId}<span>Requesting the source record for the current run</span></h2>
    <div className="evidence-load-state" role="status" aria-live="polite">Loading evidence from the v1 Evidence endpoint…</div>
    <VerifiedLine>Only a matching record for this run's dataVersion will be shown. No saved-example evidence is substituted.</VerifiedLine>
  </>;
  if (view.state === "error") return <>
    <SectionLabel index="EV" label="Evidence unavailable" />
    <h2>{view.evidenceId}<span>Current simulation is retained; the citation was not substituted.</span></h2>
    <div className="evidence-load-error" role="alert"><b>{view.failure.code.replaceAll("_", " ")}</b><p>{view.failure.message}</p>{view.failure.requestId && <small>Request {view.failure.requestId}</small>}</div>
    {view.failure.retryable && <button type="button" className="evidence-retry-button" onClick={onRetry}>Retry Evidence lookup</button>}
    <VerifiedLine>Retrying Evidence does not rerun or clear the validated simulation.</VerifiedLine>
  </>;
  return <EvidenceBody evidence={view.evidence} origin={view.source} identity={view.identity} requestId={view.requestId} />;
}

function EvidenceBody({ evidence, origin, identity, requestId }: { evidence: Evidence; origin: "saved-example" | "live" | "verified-cache"; identity?: { simulationId: string; dataVersion: string; scenarioId: string; simulationRequestId: string }; requestId?: string }) {
  const sourceHref = evidenceSourceHref(evidence);
  return <>
    <SectionLabel index="EV" label="Traceable evidence" />
    <span className="modal-evidence-id">{evidence.id}</span>
    <h2>{evidence.extractedValue}<span>{evidence.extractedField}</span></h2>
    <blockquote className="quote-block">{evidence.quote}</blockquote>
    <div className="evidence-meta"><Metric label="Source" value={evidence.sourceFile} /><Metric label="Source page" value={`p. ${evidence.page}`} /><Metric label="Quote match" value={`${evidence.quoteMatched ? "matched" : "not matched"} · ${evidence.matchMethod} · ${percent(evidence.matchScore)}`} tone={evidence.quoteMatched ? "lime" : "coral"} /><Metric label="Human confirmation" value="Not provided per record" /></div>
    {identity && <div className="evidence-run-identity"><span>Simulation <b>{identity.simulationId}</b></span><span>Data version <b>{identity.dataVersion}</b></span><span>Scenario <b>{identity.scenarioId}</b></span><span>Simulation request <b>{identity.simulationRequestId}</b></span>{requestId && <span>Evidence request <b>{requestId}</b></span>}</div>}
    {sourceHref ? <EvidencePdfViewer key={`${evidence.id}:${evidence.page}`} evidence={evidence} /> : <div className="evidence-load-error" role="alert">No approved local source asset is available for this record. The quote is shown exactly as returned; no alternative file was substituted.</div>}
    {sourceHref && <a className="evidence-source-link" href={sourceHref} target="_blank" rel="noopener noreferrer">Open source PDF · page {evidence.page}<ArrowUpRight size={14} /></a>}
    <div className="evidence-boundary-note"><b>{origin === "live" ? "Live Evidence response" : origin === "verified-cache" ? "Verified Golden Evidence snapshot" : "Saved-example Evidence"}</b><span>{origin === "live" ? "The response is bound to the current dataVersion and run identity. The v1 Evidence DTO has no per-record human-approval field." : origin === "verified-cache" ? "This original API record was stored inside the hash-verified, read-only Golden E2E cache; no Evidence request was made." : "Synthetic frozen example only; not a live Evidence API response and not a human legal approval."}</span><span>Quote match, human confirmation, and model/operating assumption are separate states; a quote match alone is not a fact or legal conclusion.</span></div>
    <VerifiedLine>{evidence.quoteMatched ? "The supplied value is present in the preserved quote according to the recorded match method; interpretive assumptions remain separately sourced." : "The extracted value was not verified against the supplied quote. Treat it as unverified."}</VerifiedLine>
  </>;
}

function StackBody({ data, onEvidence }: { data: MockData; onEvidence: (evidence: Evidence) => void }) {
  const matched = data.evidence.filter((item) => item.quoteMatched).length;
  return <>
    <SectionLabel index="EV" label="Evidence stack" />
    <h2>{matched} / {data.evidence.length} quote-matched<span>Every contract field behind the recommendation</span></h2>
    <div className="stack-list">
      {data.evidence.map((item) => {
        const variable = data.variables.find((entry) => entry.source === item.id);
        return <button type="button" key={item.id} className="stack-row" onClick={() => onEvidence(item)}>
          <span className="stack-id">{item.id}</span>
          <span className="stack-main"><b>{item.extractedField}</b><small>{variable ? `→ ${variable.name}` : "→ not yet mapped"} · p. {item.page}</small></span>
          <strong>{item.extractedValue}</strong>
          <ChevronRight size={15} />
        </button>;
      })}
    </div>
    <VerifiedLine>Each row opens the preserved quote and locator. Unmapped evidence would appear here as “not yet mapped”.</VerifiedLine>
  </>;
}

function FormulaBody({ data, scenarioId, optionId, liveRun }: { data: MockData; scenarioId: string; optionId: MockData["options"][number]["id"]; liveRun: LiveSimulation | null }) {
  const simulation = liveRun?.response.data.simulation ?? data.simulation;
  const metrics = liveRun ? simulation.matrix[scenarioId]?.find((row) => row.optionId === optionId) : cell(data, scenarioId, optionId);
  if (!metrics) return <VerifiedLine>No metric cell is available for this scenario and option.</VerifiedLine>;
  const option = data.options.find((item) => item.id === optionId)!;
  const scenario = liveRun?.request.scenarios.find((item) => item.id === scenarioId) ?? data.scenarios.find((item) => item.id === scenarioId)!;
  const basePriceA = simulation.unitPricesUsd.A;
  const basePriceB = simulation.unitPricesUsd.B;
  const fixtureTermsMatch = simulation.dataVersion === data.meta.dataVersion;
  const delta = liveRun?.response.data.deltas.find((item) => item.scenarioId === scenarioId && item.optionId === optionId);
  const v2Trace = liveRun?.development?.traces[scenarioId]?.[optionId];
  const traceHow = (key: NonNullable<typeof v2Trace>["components"][number]["key"], fallback: string) => {
    const component = v2Trace?.components.find((item) => item.key === key);
    return component ? `${component.formula} · inputs: ${component.inputKeys.join(" + ")}` : fallback;
  };
  const rows = [
    { label: "Purchase cost", how: traceHow("purchase", `round(${units(metrics.unitsFromA)} from A × ${moneyExact(basePriceA)} + ${units(metrics.unitsFromB)} from B × ${moneyExact(basePriceB)})`), value: metrics.breakdown.purchase },
    { label: "Holding cost", how: traceHow("holding", liveRun ? "Server-returned breakdown.holding; v1 exposes this aggregate, not each weekly inventory driver." : "Saved Day 2 aggregate; not calculated by the browser."), value: metrics.breakdown.holding },
    { label: "Stockout loss", how: traceHow("stockoutLoss", liveRun ? "Server-returned breakdown.stockoutLoss; v1 exposes this aggregate, not individual lost-unit traces." : "Saved Day 2 aggregate; not calculated by the browser."), value: metrics.breakdown.stockoutLoss },
    { label: "Renewal premium", how: traceHow("renewalPremium", fixtureTermsMatch ? `${units(metrics.unitsFromA)} from A × ${moneyExact(basePriceA)} × ${percent(data.contract.renewalPriceIncreasePct)}; counted once in this component.` : "Server-returned breakdown.renewalPremium; the response does not expose this dataset's uplift parameter."), value: metrics.breakdown.renewalPremium },
    { label: "Termination fee", how: traceHow("terminationFee", fixtureTermsMatch ? (option.terminateA ? `Fixed ${moneyExact(data.contract.terminationFeeUsd)} exit fee for this Day 2 synthetic contract.` : "Not applicable for this option under the Day 2 synthetic contract.") : "Server-returned breakdown.terminationFee; no local fixture contract value is substituted."), value: metrics.breakdown.terminationFee }
  ];
  const total = sumBreakdown(metrics.breakdown);
  return <>
    <SectionLabel index="FX" label={`Formula trace · ${simulation.formulaVersion}`} />
    <h2>{money(metrics.expectedTco)}<span>Expected 24m TCO · {option.id} {option.label} · {scenario.label}</span></h2>
    <div className="formula-block">Expected TCO = Purchase + Holding + Stockout loss + Renewal premium + Termination fee</div>
    <div className="formula-rows">
      {rows.map((row) => <div key={row.label}><span>{row.label}<small>{row.how}</small></span><b>{moneyExact(row.value)}</b></div>)}
      <div className="formula-total"><span>Sum of lines<small>must equal the cell value</small></span><b>{moneyExact(total)} {total === metrics.expectedTco ? "✓" : "✗"}</b></div>
    </div>
    <div className="formula-aside"><Metric label="Stockout probability" value={percent(metrics.stockoutProbability)} /><Metric label="Service level" value={percent(metrics.serviceLevel, 1)} /><Metric label="P90 cash outflow" value={money(metrics.cashOutflowP90)} /></div>
    {liveRun && delta && <div className="live-delta-trace"><b>Decision Delta · {optionId} − D0 · {scenario.label}</b><span>TCO {signedMoney(delta.deltaTco)} · Stockout {signedPp(delta.deltaStockoutPp)} · Service {signedPp(delta.deltaServicePp)} · P90 cash {signedMoney(delta.deltaCashP90)}</span></div>}
    {liveRun && <div className="live-run-meta"><span>Simulation <b>{simulation.simulationId}</b></span><span>Data version <b>{simulation.dataVersion}</b></span><span>Seed <b>{simulation.seed}</b></span><span>Runs <b>{simulation.monteCarloRuns.toLocaleString("en-US")}</b></span><span>Horizon <b>{simulation.weeks} weeks</b></span><span>Request <b>{liveRun.response.requestId}</b></span><span>Received <b>{liveRun.receivedAt}</b></span></div>}
    {v2Trace && <section className="dev-trace" aria-label={liveRun?.integrationMode === "reviewed-v2" ? "Reviewed Formula Trace" : "Unreviewed development Formula Trace"}>
      <div className="dev-trace-warning" role="note"><b>{liveRun?.integrationMode === "reviewed-v2" ? "Reviewed calculation · policy and trace release verified" : "UNREVIEWED — DEVELOPMENT ONLY · decisionReady=false"}</b><span>{liveRun?.development?.executionContext.banner} {liveRun?.integrationMode === "reviewed-v2" ? "AI Boardroom and the final decision brief remain separate steps. No supplier action has been taken." : "This trace cannot support a formal recommendation or approval."}</span></div>
      <h3>Formula inputs and provenance</h3>
      <div className="dev-trace-components">{v2Trace.components.map((component) => <article key={component.key}><b>{component.key}</b><code>{component.formula}</code><small>Inputs: {component.inputKeys.join(" · ")}</small><span>Raw mean {moneyExact(Number(component.roundingAudit.rawMeanUsd))} · displayed {moneyExact(component.roundingAudit.displayedValueUsd)} · Δ {component.roundingAudit.displayedMinusRawMeanUsd} · {component.roundingAudit.method}</span></article>)}</div>
      <ul className="dev-trace-provenance">{v2Trace.parameters.map((parameter) => <li key={parameter.key}><code>{parameter.key}</code> = {String(parameter.value)} {parameter.unit} · <b>{parameter.provenance.kind}/{parameter.provenance.status}</b> · {parameter.provenance.sourceId}: {parameter.provenance.note}</li>)}</ul>
      <p className="dev-trace-run-identity">Run identity: {v2Trace.runIdentity.executionMode} · contract SHA {v2Trace.runIdentity.contractPayloadSha256} · policy SHA {v2Trace.runIdentity.policySha256} · review record: {v2Trace.runIdentity.reviewRecordId ?? "none"} · policy approval: {v2Trace.runIdentity.policyApprovalReference} · v2 release: {v2Trace.runIdentity.contractApprovalReference}</p>
      <details className="dev-week-disclosure"><summary>Inspect 104-week sample path · one realised trial, not an average/aggregate</summary><p>{v2Trace.samplePath.note}</p><ol>{v2Trace.samplePath.weeks.map((week) => <li key={week.week}><details><summary>Week {week.week} · {week.startDate} · demand {week.demandUnits} · fulfilled {week.fulfilledUnits} · lost {week.lostUnits}</summary><dl>{Object.entries(week).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value === null ? "—" : String(value)}</dd></div>)}</dl></details></li>)}</ol></details>
    </section>}
    {!liveRun && <ul className="formula-notes">{data.brief.formulaNotes.map((note) => <li key={note}>{renderGuarded(note, data)}</li>)}</ul>}
    <VerifiedLine>{v2Trace ? `This Formula Trace is the validated ${liveRun?.integrationMode === "reviewed-v2" ? "reviewed v2" : "unreviewed v2 development"} response. Component values reconcile to expectedTco; probability counts, service totals, P90 rank, formula rounding, provenance and all 104 sample-path weeks were checked. The sample path is one realised trial, not an aggregate.` : liveRun ? "This view uses the validated /api/simulate v1 response. The five returned breakdown values reconcile exactly to expectedTco; purchase reconciles to units and returned unit prices. Weekly holding/stockout drivers are not present in the shared v1 DTO." : `Saved Day 2 example only (${simulation.simulationId}, seed ${simulation.seed}); no live simulation has produced this cell.`}</VerifiedLine>
  </>;
}
