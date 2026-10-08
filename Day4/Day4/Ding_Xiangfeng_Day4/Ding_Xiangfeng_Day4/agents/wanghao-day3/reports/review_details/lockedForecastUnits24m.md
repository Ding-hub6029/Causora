# lockedForecastUnits24m — Synthetic Evidence Review

## Scope and decision

**Project:** `lockedForecastUnits24m` only  
**Review basis:** `review_request.json`, `supplier_a_agreement.pdf`, the frozen Day 1 mock JSON, the synthetic notice CSV, and `API_CONTRACT.md`. No external or live-source investigation was performed.

**Synthetic decision: `reviewed_synthetic`**

The project is acceptable as a **clearly labelled synthetic demonstration dataset**. The supplied PDF explicitly states that it is synthetic, unsigned, unenforceable, and not associated with a real supplier. The frozen mock and API contract consistently preserve the distinction between demo assumptions and real-world facts. This is not approval of a real contract, a real renewal, or a production forecast.

## Evidence review

All six requested evidence items match the expected quote, page, field, value, and condition in the review request and frozen mock:

| Evidence ID | Field | Expected / confirmed value | Source and verification | Assessment |
|---|---|---|---|---|
| EV-014 | `renewal_notice_days` | `60 days` | `supplier_a_agreement.pdf`, p. 4: “If written notice is not received at least 60 days before renewal, the agreement automatically renews.” Frozen mock `evidence[0]` and `contract.renewalNoticeDays`. | Exact quote match. This is a **conditional** auto-renewal rule, not an unconditional lock. |
| EV-019 | `renewal_term_months` | `24 months` | `supplier_a_agreement.pdf`, p. 4: “The agreement automatically renews for 24 months at a 14% higher unit price.” Frozen mock `evidence[1]` and `contract.renewalTermMonths`. | Exact quote match. Applies only if the conditional renewal clause is triggered. |
| EV-021 | `renewal_price_increase_pct` | `14%` | `supplier_a_agreement.pdf`, p. 4; frozen mock `evidence[2]` and `contract.renewalPriceIncreasePct = 0.14`. | Exact quote and unit representation are consistent. |
| EV-024 | `min_purchase_share_A` | `60%` | `supplier_a_agreement.pdf`, p. 4: minimum purchase equals 60% of forecast demand; frozen mock `evidence[3]` and `contract.minPurchaseShareA = 0.6`. | Exact quote and decimal wire value are consistent. The demo applies this to the locked forecast, not realised demand. |
| EV-027 | `termination_fee` | `$25,000` | `supplier_a_agreement.pdf`, p. 4: early exit during the renewed term incurs a fixed termination fee; frozen mock `evidence[4]` and `contract.terminationFeeUsd = 25000`. | Exact quote and integer-USD wire value are consistent. It is conditional on early exit during the renewed term. |
| EV-020 | `auto_renew` | `conditional auto-renew clause present` | `supplier_a_agreement.pdf`, p. 4, together with EV-014: renewal occurs if written notice is not received at least 60 days before renewal. Frozen mock `contract.renewalLocked` and API contract §2 Renewal lock. | Supported as a **conditional clause** only. It must not be described as unconditional auto-renewal or as a real-world locked renewal. |

The frozen mock records exact quote matches (`matchMethod: exact`, `matchScore: 1.0`, `quoteMatched: true`) for EV-014, EV-019, EV-021, EV-024, and EV-027. Per `API_CONTRACT.md` §2, a quote match is not by itself proof of a business fact, and `locatorBbox: null` means no PDF-region highlight is claimed.

## Assumption review

- `decisionDate = 2026-10-04` and `renewalDate = 2026-11-18` are accepted as explicit frozen synthetic inputs, not values inferred from the PDF (`review_request.json` assumptions; frozen mock `contract.decisionDate` and `contract.renewalDate`).
- `noticeSent = false` is accepted only for the supplied synthetic notice record. The CSV rows on `2026-09-19` and `2026-10-04` say `notice_deadline_audit_no_notice_entry` / `notice...no_notice_entry`, with provenance `synthetic_mock_not_a_real_supplier_record`. This does **not** establish that no notice existed in the real world.
- The demo lock is conditional: `45 < 60` days and `noticeSent = false` in the synthetic record (`API_CONTRACT.md` §2; frozen mock `contract.daysToRenewal`, `contract.renewalNoticeDays`, `contract.noticeSent`). An earlier valid written notice would change the outcome even within the 60-day window.
- `forecastBasis = locked-at-renewal` and `lockedForecastUnits24m = 26000` are accepted as a synthetic renewal-cycle assumption (`supplier_a_agreement.pdf`, p. 4; frozen mock `contract.forecastBasis` and `contract.lockedForecastUnits24m`; API contract §2). The 26,000 units are **not** a sum of historical demand and are **not** claimed to be a model-produced forecast. `API_CONTRACT.md` §5 states historical demand totals 25,936 units and explicitly rejects an estimator claim turning history into 26,000.
- The resulting synthetic Supplier A floor is `15,600 units` (`60% × 26,000`), consistent with the frozen mock `contract.minPurchaseUnitsA` and the PDF p. 5 operational interpretation. This is an illustrative synthetic mechanism, not an audited legal interpretation.

## API and unit consistency

The mock follows the relevant contract discipline: 24 months is 104 weekly steps; quantities are whole units; `minPurchaseShareA` is a decimal fraction (`0.6`); `renewalPriceIncreasePct` is `0.14`; and `terminationFeeUsd` is integer USD (`25000`). The API contract also requires the renewal premium to be booked once and distinguishes forecast units, realised demand, and ordered units.

The frozen mock's Day 1 scenarios are labelled mock data, with `monteCarloRuns: 0`; they must not be represented as a production simulation or live model result. In particular, the demand-drop scenario's `22,100` realised units does not replace the locked `26,000` commitment basis.

## Limitations and pending real-world work

1. The PDF is explicitly not a real, signed, enforceable contract. Real contract verification, counterparties, signatures, legal interpretation, and counsel/source verification remain pending.
2. The notice CSV is synthetic and cannot establish the absence, timing, validity, or receipt of a real notice. `noticeSent=false` is only a reviewed synthetic-record value.
3. This review does not claim `manually_verified=true`, does not impersonate Wang Hao, and does not provide a human signature or acknowledgement.
4. The evidence review validates quote/value/source alignment for the demo; it does not independently prove that the quoted clauses govern any real transaction.
5. The locked 26,000 is a configured synthetic assumption and not historical-demand summation or model output. Historical, delivery, inventory, and cost figures in the mock are illustrative static data unless separately audited.
6. Any production approval or real renewal decision remains pending and requires human review of authentic contract and notice sources, plus implementation/testing against the API contract.

## Conclusion

`lockedForecastUnits24m` passes as a **reviewed synthetic demonstration field** with the conditional auto-renewal semantics preserved. It must remain visibly labelled synthetic/local mock data, and all real contract, notice, legal, and production-model claims remain pending.
