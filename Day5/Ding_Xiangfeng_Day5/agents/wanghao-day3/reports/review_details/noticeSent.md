# noticeSent Synthetic Data Review

## Scope and decision

This review covers **only the Causora Wang Hao Day 2 project `noticeSent`**. The submitted material is acceptable as **explicitly labelled synthetic demonstration data**, not as evidence of a real contract or a real-world absence of notice.

**Synthetic decision: `reviewed_synthetic`**

The supplied PDF is visibly labelled “Supplier A Agreement — Synthetic Demo,” “SYNTHETIC SOURCE FILE,” and “not signed, enforceable or associated with any real supplier.” The notice register is also explicitly marked `synthetic_mock_not_a_real_supplier_record`. The API contract states that the synthetic notice status is an explicit mock input and that uploading a PDF cannot establish notice status.

## Expected value and source check

| Item | Expected / reviewed value | Source and result |
|---|---:|---|
| `noticeSent` | `false` (boolean) | `public/demo/supplier_correspondence_log.csv`; all three dated rows have `valid_written_nonrenewal_notice=false`. The 2026-09-19 row is the deadline audit and the 2026-10-04 row is the decision-date audit. This supports only the frozen synthetic record. |
| `decisionDate` | `2026-10-04` | `demo_data/causora_day1_mock.json` → `contract.decisionDate`; explicitly described in `API_CONTRACT.md` §2 as a demo assumption. |
| `renewalDate` | `2026-11-18` | `demo_data/causora_day1_mock.json` → `contract.renewalDate`; explicitly described in `API_CONTRACT.md` §2 as a demo assumption. |
| `forecastBasis` | `locked-at-renewal` | `demo_data/causora_day1_mock.json` → `contract.forecastBasis`; `API_CONTRACT.md` §2 calls this a demo assumption. |
| `lockedForecastUnits24m` | `26000` units | `supplier_a_agreement.pdf` p.4: “For the synthetic scenario only, the renewal-cycle forecast is fixed at 26,000 units for the coming term”; also `demo_data/causora_day1_mock.json` → `contract.lockedForecastUnits24m`. This is not a historical-demand sum and not a model-produced forecast. |

## Six evidence records

All six requested records are supported by the synthetic agreement text on **PDF page 4**, with the following exact clauses and units:

1. **EV-014 — `renewal_notice_days`: 60 days**  
   Quote: “If written notice is not received at least 60 days before renewal, the agreement automatically renews.” Exact page/quote match.
2. **EV-019 — `renewal_term_months`: 24 months**  
   Quote: “The agreement automatically renews for 24 months at a 14% higher unit price.” Exact page/quote match.
3. **EV-021 — `renewal_price_increase_pct`: 14%**  
   Same exact page-4 sentence as EV-019; the separate extracted field is the percentage uplift. Exact page/quote match.
4. **EV-024 — `min_purchase_share_A`: 60%**  
   Quote: “The renewed term has a minimum purchase commitment equal to 60% of forecast demand.” Exact page/quote match.
5. **EV-027 — `termination_fee`: $25,000**  
   Quote: “Early exit during the renewed term incurs a fixed termination fee of $25,000.” Exact page/quote match; the API wire unit is integer USD when represented as a metric.
6. **EV-020 — `auto_renew`: conditional auto-renew clause present**  
   The page-4 clause makes renewal conditional on written notice not being received at least 60 days before renewal. This must be interpreted as a **conditional auto-renew clause**, not an unconditional lock. The frozen mock evidence array lists EV-014, EV-019, EV-021, EV-024, and EV-027 but does not include a separate EV-020 record; this review therefore traces EV-020 directly to the page-4 conditional sentence and the review request’s expected field. That record-structure omission does not contradict the clause, but it should be repaired before live integration.

## Notice logic and boundaries

The synthetic inputs use `decisionDate=2026-10-04`, `renewalDate=2026-11-18`, and a 60-day notice period. The frozen mock derives `daysToRenewal=45` and `noticeDeadline=2026-09-19`; the API contract says the renewal is treated as locked only because `45 < 60` **and** the synthetic `noticeSent=false`. An earlier valid written notice would change the outcome even within the 60-day window. Therefore, the correct reviewed statement is: **the synthetic record contains no timely written non-renewal notice; it does not establish that no notice existed in the real world.**

The 26,000-unit locked forecast is a synthetic renewal-cycle assumption. It must not be described as the sum of historical demand (the API contract separately states historical demand totals 25,936 units) or as an output of a forecast model. Likewise, `noticeSent=false` is not a claim about actual supplier communications.

## Limitations and required follow-up

- The PDF is synthetic, unsigned, unenforceable, and has no real supplier or buyer; no real contract verification has occurred.
- The notice CSV is synthetic and explicitly not a real supplier record; no mailbox, register, or authoritative correspondence system was checked.
- The PDF itself cannot prove notice status; status comes only from the supplied synthetic notice register.
- `decisionDate` and `renewalDate` are explicit frozen demonstration assumptions, not values inferred from the PDF.
- The auto-renew conclusion is conditional on the notice condition and must not be presented as an unconditional automatic renewal.
- The frozen mock does not carry a separate EV-020 evidence object even though the review request requires six evidence items; the source clause is present, but the evidence-record/schema mapping needs manual remediation.
- PDF locator bounding boxes are null, so no precise visual-region highlight is supported.
- All real contract validation, authoritative notice verification, legal interpretation, and remaining specification-required manual review remain **pending**. No `manually_verified=true` claim is made.

## Final assessment

`noticeSent=false` is accepted as a **reviewed synthetic field** with preserved boolean type and explicit provenance. The project is not approved as a real-world contract or notice determination. The proper deployment label remains **synthetic demo / local mock** until authoritative documents and notice records are manually verified.
