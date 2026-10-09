# renewalDate Review — Causora Wang Hao Day 2

## Scope and decision

- **Project:** `renewalDate` only
- **Synthetic decision:** `reviewed_synthetic`
- **Reviewed value:** `2026-11-18`
- **Decision basis:** The date is an explicitly configured frozen synthetic contract input, not a date inferred from the agreement PDF. It matches the expected value in `review_request.json` and the frozen mock.
- **Synthetic-data boundary:** The supplier agreement is explicitly labelled synthetic demo data, not signed or enforceable, and the notice register is explicitly a synthetic mock record. This review therefore accepts the field for a clearly labelled demonstration only. It does not establish a real renewal date or a real renewal obligation.

## Expected value and direct source check

The review request specifies `renewalDate` as `2026-11-18`, sourced from a “frozen synthetic contract input (not inferred from PDF)” (`review_request.json`, `assumptions[1]`). The frozen mock contains `contract.renewalDate: "2026-11-18"` (`causora_day1_mock.json`, `contract.renewalDate`). It also contains `contract.decisionDate: "2026-10-04"`, `contract.daysToRenewal: 45`, and `contract.noticeDeadline: "2026-09-19"` (`contract.decisionDate`, `contract.daysToRenewal`, `contract.noticeDeadline`). The 45-day interval is consistent with the configured dates. API contract requirements specify ISO `YYYY-MM-DD` dates and state that these dates are structured demo inputs (`API_CONTRACT.md`, lines 24 and 31).

The PDF does not provide a calendar renewal date. Page 4 provides the renewal rule and the synthetic fixed forecast, but the date is intentionally supplied by the frozen input. This is consistent with the review request and is not a deficiency for a demo assumption.

## Six evidence records reviewed

All six expected evidence items are represented in the request and the frozen mock. The five clause records have exact quote matches (`matchMethod: exact`, `matchScore: 1.0`, `quoteMatched: true`) and point to page 4. The sixth record, `EV-020`, is the conditional auto-renew interpretation.

1. **EV-014 — notice period:** PDF page 4 states, “If written notice is not received at least 60 days before renewal, the agreement automatically renews.” The mock records `extractedValue: "60 days"` and `contract.renewalNoticeDays: 60`. This is a conditional clause, not an unconditional lock.
2. **EV-019 — renewed term:** PDF page 4 states, “The agreement automatically renews for 24 months at a 14% higher unit price.” The mock records `extractedValue: "24 months"` and `contract.renewalTermMonths: 24`.
3. **EV-021 — price increase:** The same exact sentence on PDF page 4 states the `14%` uplift. The mock records `extractedValue: "14%"` and `contract.renewalPriceIncreasePct: 0.14` (wire decimal fraction, rendered as 14%).
4. **EV-024 — minimum purchase share:** PDF page 4 states, “The renewed term has a minimum purchase commitment equal to 60% of forecast demand.” The mock records `extractedValue: "60%"` and `contract.minPurchaseShareA: 0.6`.
5. **EV-027 — termination fee:** PDF page 4 states, “Early exit during the renewed term incurs a fixed termination fee of $25,000.” The mock records `extractedValue: "$25,000"` and `contract.terminationFeeUsd: 25000`.
6. **EV-020 — conditional auto-renew:** The request expects `conditional auto-renew clause present`, and the condition is supported by EV-014 plus the renewal sentence on PDF page 4. The mock's `contract.renewalLocked: true` is only a synthetic scenario outcome based on `daysToRenewal: 45 < renewalNoticeDays: 60` together with `noticeSent: false`. It must not be read as an unconditional contractual lock. API contract language expressly says that an earlier valid written notice would change the outcome and that real-world absence of notice is not established (`API_CONTRACT.md`, line 31).

## Notice and forecast checks relevant to the date scenario

The frozen mock records `contract.noticeSent: false` and identifies `supplier_correspondence_log.csv` as the source. The CSV contains only synthetic rows, including a 2026-09-19 deadline audit with `valid_written_nonrenewal_notice=false` and a 2026-10-04 decision-date audit with the same false value. This supports the demo assumption only. It is not evidence that no notice existed in the real world.

The mock records `forecastBasis: "locked-at-renewal"` and `lockedForecastUnits24m: 26000`. The PDF page 4 says the synthetic renewal-cycle forecast is fixed at 26,000 units. This is not a historical-demand sum and not a model forecast output. The API contract further records historical demand as 25,936 units and explicitly distinguishes it from the locked 26,000-unit synthetic assumption (`API_CONTRACT.md`, line 98). This forecast detail does not alter the configured renewal date.

## Acceptance and limitations

**Accept as `reviewed_synthetic`** for a clearly marked, local synthetic demonstration because the expected date matches the frozen input, the date format is valid, the configured interval is internally consistent, and the surrounding conditional clause evidence is quote-matched and page-specific.

This status is not approval of a live contract or production decision. The source PDF says it is synthetic, unsigned, unenforceable, and not associated with a real supplier (PDF page 1). Page 5 calls the interpretation non-legal. Page 6 requires an authorised machine-readable agreement and source verification for live deployment. Human review remains required for all real-contract verification and for the specification's required manual review. No manual signature or `manually_verified=true` claim is made.

## Source index

- `review_request.json`: `assumptions[1]` (`renewalDate` expected value and synthetic-input provenance). `evidence[0..5]` (EV-014, EV-019, EV-021, EV-024, EV-027, EV-020 expectations).
- `supplier_a_agreement.pdf`: page 1 synthetic/non-real disclaimer. Page 4 conditional renewal, 60-day notice, 24-month term, 14% uplift, 60% minimum, $25,000 fee, and 26,000-unit synthetic forecast. Page 5 interpretive limitation. Page 6 reproducibility/live-verification limitation.
- `causora_day1_mock.json`: `contract.renewalDate`, `contract.decisionDate`, `contract.daysToRenewal`, `contract.noticeDeadline`, `contract.noticeSent`, `contract.forecastBasis`, `contract.lockedForecastUnits24m`, `contract.renewalLocked`. `evidence[]` records EV-014/019/021/024/027.
- `supplier_correspondence_log.csv`: all three synthetic register rows, especially the 2026-09-19 and 2026-10-04 no-notice audit rows.
- `API_CONTRACT.md`: lines 24, 27–31, 40–41, and 98 for date/unit discipline, conditional renewal logic, evidence semantics, and forecast distinction.
