import { AnimatePresence, motion } from "framer-motion";
import { ArrowUpRight, ChevronRight, X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { Evidence, ModalState, MockData } from "@/lib/types";
import { cell, moneyExact, money, percent, renderGuarded, sumBreakdown, units } from "@/lib/metrics";
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

export function DetailModal({ modal, onClose, onEvidence, data }: { modal: ModalState; onClose: () => void; onEvidence: (evidence: Evidence) => void; data: MockData }) {
  const isOpen = modal.kind !== "closed";
  const dialogRef = useDialogFocus(isOpen, modal.kind === "evidence" ? modal.evidence.id : modal.kind, onClose);
  const title = modal.kind === "evidence" ? "Evidence detail" : modal.kind === "stack" ? "Evidence stack" : "Formula trace";

  return <AnimatePresence>{isOpen && <motion.div className="modal-layer" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
    <button type="button" className="modal-backdrop" onClick={onClose} aria-label="Close dialog" tabIndex={-1} />
    <motion.section ref={dialogRef} className="detail-modal" role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} initial={{ opacity: 0, y: 18, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 12, scale: 0.98 }} transition={{ type: "spring", duration: 0.42, bounce: 0.1 }}>
      <button type="button" className="modal-close" onClick={onClose} aria-label="Close dialog"><X size={18} /></button>
      {modal.kind === "evidence" && <EvidenceBody evidence={modal.evidence} />}
      {modal.kind === "stack" && <StackBody data={data} onEvidence={onEvidence} />}
      {modal.kind === "formula" && <FormulaBody data={data} scenarioId={modal.scenarioId} optionId={modal.optionId} />}
    </motion.section>
  </motion.div>}</AnimatePresence>;
}

function EvidenceBody({ evidence }: { evidence: Evidence }) {
  return <>
    <SectionLabel index="EV" label="Traceable evidence" />
    <span className="modal-evidence-id">{evidence.id}</span>
    <h2>{evidence.extractedValue}<span>{evidence.extractedField}</span></h2>
    <div className="quote-block">“{evidence.quote}”</div>
    <div className="evidence-meta"><Metric label="Source" value={evidence.sourceFile} /><Metric label="Locator" value={`p. ${evidence.page}${evidence.locatorBbox ? " · bbox" : ""}`} /><Metric label="Quote match" value={`${evidence.matchMethod} · ${percent(evidence.matchScore)}`} tone={evidence.quoteMatched ? "lime" : "coral"} /></div>
    <a className="evidence-source-link" href={`/demo/${encodeURIComponent(evidence.sourceFile)}#page=${evidence.page}`} target="_blank" rel="noopener noreferrer">Open synthetic source PDF · page {evidence.page}<ArrowUpRight size={14} /></a>
    <VerifiedLine>{evidence.quoteMatched ? "This value appears in the preserved quote. It is a quote match, not an autonomous fact claim." : "The extracted value was not found in the quote. Treat it as unverified."}</VerifiedLine>
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

function FormulaBody({ data, scenarioId, optionId }: { data: MockData; scenarioId: string; optionId: MockData["options"][number]["id"] }) {
  const metrics = cell(data, scenarioId, optionId);
  const option = data.options.find((item) => item.id === optionId)!;
  const scenario = data.scenarios.find((item) => item.id === scenarioId)!;
  const basePriceA = `$${data.simulation.unitPricesUsd.A.toFixed(2)}`;
  const basePriceB = `$${data.simulation.unitPricesUsd.B.toFixed(2)}`;
  const rows = [
    { label: "Purchase cost", how: `${units(metrics.unitsFromA)} from A at ${basePriceA} + ${units(metrics.unitsFromB)} from B at ${basePriceB}`, value: metrics.breakdown.purchase },
    { label: "Holding cost", how: "Day 1 preset aggregate; the future simulator will expose inventory × weekly rate", value: metrics.breakdown.holding },
    { label: "Stockout loss", how: "Day 1 preset aggregate; the future simulator will expose lost units × contribution", value: metrics.breakdown.stockoutLoss },
    { label: "Renewal premium", how: `${units(metrics.unitsFromA)} from A × ${basePriceA} × ${percent(data.contract.renewalPriceIncreasePct)} (counted once, here)`, value: metrics.breakdown.renewalPremium },
    { label: "Termination fee", how: option.terminateA ? "fixed fee, renewed agreement exited" : "not applicable for this option", value: metrics.breakdown.terminationFee }
  ];
  const total = sumBreakdown(metrics.breakdown);
  return <>
    <SectionLabel index="FX" label={`Formula trace · ${data.brief.formulaVersion}`} />
    <h2>{money(metrics.expectedTco)}<span>Expected 24m TCO · {option.id} {option.label} · {scenario.label}</span></h2>
    <div className="formula-block">{renderGuarded(data.brief.formula, data)}</div>
    <div className="formula-rows">
      {rows.map((row) => <div key={row.label}><span>{row.label}<small>{row.how}</small></span><b>{moneyExact(row.value)}</b></div>)}
      <div className="formula-total"><span>Sum of lines<small>must equal the cell value</small></span><b>{moneyExact(total)} {total === metrics.expectedTco ? "✓" : "✗"}</b></div>
    </div>
    <div className="formula-aside"><Metric label="Stockout probability" value={percent(metrics.stockoutProbability)} /><Metric label="Service level" value={percent(metrics.serviceLevel, 1)} /><Metric label="P90 cash outflow" value={money(metrics.cashOutflowP90)} /></div>
    <ul className="formula-notes">{data.brief.formulaNotes.map((note) => <li key={note}>{renderGuarded(note, data)}</li>)}</ul>
    <VerifiedLine>Day 1 shows mock components bound to this cell ({data.simulation.simulationId}, seed {data.simulation.seed}). Purchase and premium use displayed inputs; holding and stockout are illustrative preset aggregates until the live simulator supplies their drivers.</VerifiedLine>
  </>;
}
