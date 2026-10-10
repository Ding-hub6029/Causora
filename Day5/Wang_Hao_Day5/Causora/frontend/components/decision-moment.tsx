"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Check, X } from "lucide-react";

const nodes = ["EVIDENCE", "CONSTRAINT", "MATRIX", "CHALLENGE", "HUMAN"];

export function DecisionMoment({ decision, optionId, onDismiss }: { optionId: string; decision: "Approved" | "Rejected" | null; onDismiss: () => void }) {
  const reduceMotion = useReducedMotion();
  const approved = decision === "Approved";

  return <AnimatePresence>
    {decision && <motion.div className={`decision-moment ${approved ? "approved" : "rejected"}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: reduceMotion ? 0.05 : 0.25 }} role="status" aria-live="polite">
      <div className="decision-moment-grid" aria-hidden="true" />
      <motion.div className="decision-moment-content" initial={reduceMotion ? false : { opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduceMotion ? 0.05 : 0.45 }}>
        <span className="decision-moment-kicker">CAUSORA / HUMAN DECISION GATE</span>
        <div className="decision-moment-sequence" aria-label="Decision provenance sequence">
          {nodes.map((node, index) => <motion.div key={node} className={`decision-moment-node ${index === nodes.length - 1 ? "last" : ""}`} initial={reduceMotion ? false : { opacity: 0.2, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: reduceMotion ? 0 : index * 0.13, duration: 0.25 }}><span>{String(index + 1).padStart(2, "0")}</span><b>{node}</b></motion.div>)}
        </div>
        <motion.div className="decision-moment-seal" initial={reduceMotion ? false : { scale: 0.72, rotate: -16, opacity: 0 }} animate={{ scale: 1, rotate: 0, opacity: 1 }} transition={{ delay: reduceMotion ? 0 : 0.58, type: "spring", stiffness: 155, damping: 18 }}>
          {approved ? <Check size={44} strokeWidth={1.6} /> : <X size={44} strokeWidth={1.6} />}
        </motion.div>
        <h2>{approved ? "Decision approved." : "Decision rejected."}</h2>
        <p>{approved ? `${optionId} is recorded as approved in this browser for the validated run. No supplier action, contract change, signature, or external approval has occurred.` : `${optionId} is recorded as rejected in this browser for the validated run. No supplier action or external message has occurred; the Evidence remains reviewable.`}</p>
        <button type="button" onClick={onDismiss}>Continue to the brief <span>↗</span></button>
      </motion.div>
    </motion.div>}
  </AnimatePresence>;
}
