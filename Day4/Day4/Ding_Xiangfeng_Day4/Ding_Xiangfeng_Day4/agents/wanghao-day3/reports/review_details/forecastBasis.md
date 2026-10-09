# forecastBasis Review — Causora Wang Hao Day 2

## Scope and conclusion

This review covers **only** the `forecastBasis` item in the `forecastBasis` project. The material is acceptable as **explicitly labelled synthetic demonstration data**. The synthetic review decision is `reviewed_synthetic`: the requested value is supported by the stated PDF text and the frozen mock, with no substantive contradiction found for this field.

This is not a real contract verification, procurement approval, legal interpretation, or manually signed review. The agreement itself repeatedly identifies the data as synthetic and not enforceable.

## Requested value and decision

- **Field:** `forecastBasis`
- **Expected value:** `locked-at-renewal`
- **Confirmed synthetic value:** `locked-at-renewal`
- **Decision:** `reviewed_synthetic`
- **Primary source:** `supplier_a_agreement.pdf`, p. 4, final paragraph: “For the synthetic scenario only, the renewal-cycle forecast is fixed at 26,000 units for the coming term.”
- **Structured source:** `causora_day1_mock.json`, `contract.forecastBasis` = `locked-at-renewal`. `contract.lockedForecastUnits24m` = `26000`.

The 26,000-unit value is a frozen renewal-cycle demonstration assumption. It is **not** represented as a sum of historical demand and is not claimed to be the output of a forecasting model. The API contract further states that historical demand totals 25,936 units and that no estimator turning that history into 26,000 is claimed (`API_CONTRACT.md`, v4 boundary-correction text).

## Six evidence records audited

All six requested evidence items point to page 4 and match the supplied synthetic source text. The sixth item, `EV-020`, is treated as a **conditional auto-renew clause**, not an unconditional lock.

| ID | Field | Expected value | Synthetic source check | Result |
|---|---|---|---|---|
| `EV-014` | `renewal_notice_days` | 60 days | `supplier_a_agreement.pdf`, p. 4: “If written notice is not received at least 60 days before renewal, the agreement automatically renews.” | Supported |
| `EV-019` | `renewal_term_months` | 24 months | `supplier_a_agreement.pdf`, p. 4: “The agreement automatically renews for 24 months at a 14% higher unit price.” | Supported |
| `EV-021` | `renewal_price_increase_pct` | 14% | Same p. 4 sentence as `EV-019`. The uplift is 14%. | Supported |
| `EV-024` | `min_purchase_share_A` | 60% | `supplier_a_agreement.pdf`, p. 4: “The renewed term has a minimum purchase commitment equal to 60% of forecast demand.” | Supported |
| `EV-027` | `termination_fee` | $25,000 | `supplier_a_agreement.pdf`, p. 4: “Early exit during the renewed term incurs a fixed termination fee of $25,000.” | Supported |
| `EV-020` | `auto_renew` | conditional auto-renew clause present | The clause is conditional on written notice not being received at least 60 days before renewal. It must not be described as unconditional automatic locking. The frozen mock links `contract.renewalLocked` to the synthetic dates and notice record. | Supported as conditional only |

The frozen mock records exact quote matches for `EV-014`, `EV-019`, `EV-021`, `EV-024`, and `EV-027` under `evidence[*]`, each with `matchMethod: exact`, `matchScore: 1.0`, `page: 4`, and `quoteMatched: true`. `EV-020` is the requested conditional interpretation of the auto-renew language and is not evidence of an unconditional renewal.

## Assumption checks relevant to this field

- `decisionDate` = `2026-10-04` and `renewalDate` = `2026-11-18` are explicit frozen synthetic contract inputs (`causora_day1_mock.json`, `contract.decisionDate` and `contract.renewalDate`). They are not inferred from the PDF and were not required to be derived from it.
- `noticeSent` = `false` is supported only by the supplied synthetic notice register: `supplier_correspondence_log.csv`, rows dated `2026-09-01`, `2026-09-19`, and `2026-10-04`, each with `valid_written_nonrenewal_notice=false` and provenance `synthetic_mock_not_a_real_supplier_record`. This does not establish that no real-world notice was sent.
- The frozen mock calculates `minPurchaseUnitsA` as 15,600 (= 60% × 26,000), while the demand-drop scenario shows 22,100 units. This is consistent with the stated locked-at-renewal basis and does not turn 26,000 into historical demand or model output.
- `lockedForecastUnits24m` is `26000` in the frozen mock and is explicitly described in the PDF as fixed for the synthetic scenario only. The API contract also warns that holding/stockout values are mock aggregates rather than audited physical inventory costs.

## Limitations and required follow-up

1. The PDF is expressly marked “SYNTHETIC DEMO DATA,” “not signed, enforceable or associated with any real supplier” (p. 1), and “SYNTHETIC / NOT A REAL CONTRACT” on its pages. No real contract, counterparty, signature, or legal enforceability was verified.
2. `noticeSent=false` is only a conclusion about the supplied synthetic notice register. It is not a statement about the real world or proof that no notice exists.
3. The renewal result is conditional: an earlier valid written notice would change the outcome even within the 60-day window. Real notice ingestion and verification remain pending.
4. `decisionDate` and `renewalDate` are configured demonstration assumptions. This review does not independently substantiate them from the PDF.
5. Human review required by the specification, real contract verification, counsel review, and any production or procurement sign-off remain pending. No claim of `manually_verified=true` is made.
6. The 26,000 locked forecast is not a historical-demand sum and not a model forecast output. Any real forecasting or sourcing decision requires independently verified data and methodology.

## Source files reviewed

- `review_request.json`: evidence expectations, assumptions, and source hashes.
- `supplier_a_agreement.pdf`: pp. 1–5 reviewed. P. 4 contains the renewal, minimum-purchase, termination-fee, and fixed 26,000-unit synthetic scenario language.
- `causora_day1_mock.json`: `contract`, `evidence`, `variables`, and relevant scenario/constraint fields reviewed.
- `supplier_correspondence_log.csv`: all three synthetic notice-register rows reviewed.
- `API_CONTRACT.md`: evidence provenance, synthetic notice handling, conditional renewal-lock logic, and 26,000-unit boundary correction reviewed.
