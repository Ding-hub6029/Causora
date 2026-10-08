"use client";

import { motion } from "framer-motion";
import { Check, ChevronRight, CircleAlert, FileSearch, Sparkles } from "lucide-react";
import type { ReactNode } from "react";

export function CausoraMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className="brand" aria-label="Causora">
      <div className="brand-mark" aria-hidden="true"><span /><i /></div>
      {!compact && <span className="brand-word">CAUSORA</span>}
    </div>
  );
}

export function StatusChip({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "success" | "warning" | "signal" }) {
  return <span className={`status-chip ${tone}`}><span className="status-dot" />{children}</span>;
}

export function SectionLabel({ index, label }: { index: string; label: string }) {
  return <div className="section-label"><span>{index}</span><i />{label}</div>;
}

export function Panel({ children, className = "", title, action }: { children: ReactNode; className?: string; title?: string; action?: ReactNode }) {
  return (
    <section className={`panel ${className}`}>
      {(title || action) && <div className="panel-topline"><h3>{title}</h3>{action}</div>}
      {children}
    </section>
  );
}

export function Metric({ label, value, detail, tone = "light" }: { label: string; value: string; detail?: string; tone?: "light" | "lime" | "coral" | "blue" }) {
  return <div className={`metric ${tone}`}><span>{label}</span><strong>{value}</strong>{detail && <small>{detail}</small>}</div>;
}

export function PrimaryButton({ children, onClick, disabled = false, className = "", icon = true }: { children: ReactNode; onClick?: () => void; disabled?: boolean; className?: string; icon?: boolean }) {
  return <motion.button whileTap={{ scale: 0.98 }} className={`button primary ${className}`} type="button" onClick={onClick} disabled={disabled}>
    {children}{icon && <ChevronRight size={16} aria-hidden="true" />}
  </motion.button>;
}

export function GhostButton({ children, onClick, className = "", ariaLabel }: { children: ReactNode; onClick?: () => void; className?: string; ariaLabel?: string }) {
  return <motion.button whileTap={{ scale: 0.98 }} className={`button ghost ${className}`} type="button" onClick={onClick} aria-label={ariaLabel}>{children}</motion.button>;
}

export function TraceLink({ children, onClick, kind = "formula" }: { children: ReactNode; onClick: () => void; kind?: "formula" | "evidence" }) {
  return <button className="trace-link" type="button" onClick={onClick}>{kind === "formula" ? <Sparkles size={14} /> : <FileSearch size={14} />}{children}<ChevronRight size={14} /></button>;
}

export function StateCard({ state, stage }: { state: "loading" | "empty" | "error"; stage: string }) {
  const content = {
    loading: { icon: <span className="loader" />, title: `${stage} is preparing`, body: "The local demo is sequencing this stage. Nothing has been sent to a provider." },
    empty: { icon: <FileSearch size={24} />, title: `${stage} has no input yet`, body: "Load the verified Golden Run or return to Data Intake to restore the local mock dataset." },
    error: { icon: <CircleAlert size={24} />, title: `${stage} is unavailable`, body: "The live connection is intentionally unavailable in this Day 1 prototype. Your local Golden Run remains safe to inspect." }
  }[state];
  return <div className={`state-card ${state}`}><div className="state-icon">{content.icon}</div><div><p>{content.title}</p><span>{content.body}</span></div></div>;
}

export function VerifiedLine({ children }: { children: ReactNode }) {
  return <div className="verified-line"><Check size={14} /><span>{children}</span></div>;
}
