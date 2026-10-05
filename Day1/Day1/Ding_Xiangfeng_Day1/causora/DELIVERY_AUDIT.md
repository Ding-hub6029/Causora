> Historical v3 record retained for context. The current release is v4; see V4_DELIVERY_NOTES.md for current checks and remaining human tasks.

# Causora Day 1 — Delivery Audit (Revised)

**Target:** Causora v3.0 Final Build Specification, **Day 1 only**. This is a local static mock and a team interface draft, not a complete G1 or a production decision system. See `FEEDBACK_RESPONSE.md` for responses to all 19 external-audit findings.

## Day 1 scope and evidence

| Obligation | Revised delivery | Status |
| --- | --- | --- |
| Freeze user story and five-stage flow | `plan.md`, five interactive English stages and a consistent Proof Engine | **Day 1 mock complete** |
| Supply four inspectable demo inputs | `public/demo/` has 104-week demand CSV, 48-order XLSX, opening inventory CSV and 6-page searchable synthetic agreement | **Complete as synthetic fixtures** |
| Quote-backed Evidence → Variables | Five records quote-matched to actual PDF page 4; five mapped variables including EV-019; complete Evidence stack and PDF source link | **Complete as local mock; no runtime parser** |
| Renewal constraint | Structured dates, notice deadline, no-notice flag plus synthetic correspondence register | **Explicit scenario assumption; not a real-world finding** |
| Compound risk | Locked 26,000-unit forecast; 15,600-unit Supplier A floor; demand-drop 22,100 units; 2,340-unit difference, and exact D1 procurement ratio of 15,600 A / 10,400 B | **Mechanism consistent; live cost simulation pending** |
| Matrix and Formula Trace | Unique D0/D1/D2 per scenario; every cell follows its declared A/B ratio; nine exact five-component TCO sums; selected scenario/option and unit-price inputs in dialog | **Mock decomposition complete; holding/stockout drivers pending simulator** |
| Versioned integration contract | `API_CONTRACT.md` and `lib/contracts.ts` cover 10 shared objects, proposed endpoints, wire units, errors, versioning and Golden cache discipline | **Draft for three-owner sign-off, not an implemented backend** |
| Boardroom and constrained Brief | Three role views and Critic with guarded numeric tokens, scenario-derived deltas, unsimulated-draft warning and blocked approval | **Local mock behavior complete** |
| Golden fallback and degraded states | Full independent JSON snapshot + SHA-256, actual UTC freeze time, status invalidation on edits, working loading/empty/error previews | **Verified local-mock fallback only** |
| Responsive and accessible interaction | Status badge visible on mobile; complete Evidence stack; modal focus in/trap/Escape/restore; existing no-intersection proof cards | **Targeted checks complete; formal assistive-technology audit pending** |
| Local deployment | Static `out/` export; compatible `npm start` serves the build, with `PORT`/`HOST` support | **Static self-hosting ready; no API services** |
| Day 2 users | `USER_TESTING_KIT.md` contains invite/tracker/script | **Not booked: Xiangfeng needs 2–3 real confirmations** |

## Validation performed

- `npm run typecheck` and `npm run lint` passed; `npm test` passed **14/14** strengthened data/contract/wiring tests, including an actual portable PDF parser assertion. A clean Next.js static export is generated after the final correction.
- `pdftotext` and the Node parser on the synthetic agreement's page 4 located **all five exact evidence quotes**. The automated test also rejects a changed quote and wrong page. Four input fixtures exist in the repository and static public directory; the separate synthetic notice register is downloadable.
- Real browser regressions verified Golden label invalidation, State Studio transitions, five-row Evidence stack/EV-019, Escape/focus restoration and the Demand −15% / D1 `$419k` five-line cost trace. In the **final static build**, a 20% risk-threshold draft disabled approval; restoring preset inputs re-enabled it. A 390px full-page capture confirmed the previously hidden status chip is visible.
- `npm start` successfully served built HTML, JavaScript, icon, source PDF, synthetic notice register and route manifest (HTTP 200). Traversal outside the output directory was not served. The public Preview also returned HTTP 200 after the final build.
- The final v3 ZIP passed `unzip -tq` integrity validation, includes `out/index.html`, all static source fixtures, the complete Golden snapshot, API contract and English documentation, and excludes `.git`, `.next`, `node_modules`, `.work`, secrets and TypeScript build caches. In a **fresh directory extracted from that ZIP**, `npm ci`, typecheck, lint, **14/14 tests** (including parsed PDF source assertions) and a clean static rebuild passed.
- Earlier no-overlap visual regression remains valid; `artifacts/proof-engine-fixed.png` shows three separated source/variable/matrix objects.

## Sign-off conclusion

**Accept as a strengthened Day 1 static mock plus an API v1 proposal; do not sign it off as unconditional full G1.** The three owners must agree on the frozen API and the synthetic contract interpretation before parallel integration. A real 104-week simulator, PDF preprocessing/quote validation, agent pipeline, runtime numeric guardrail, provider-failure handling, live audited Golden Run and 2–3 actual booked test users remain outside this delivery. No result here supports a claim of 100% compliance with the complete build specification.
