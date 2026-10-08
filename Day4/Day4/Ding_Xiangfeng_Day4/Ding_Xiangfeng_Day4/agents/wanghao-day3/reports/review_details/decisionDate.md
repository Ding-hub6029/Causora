# decisionDate Review — Causora Wang Hao Day 2

## Scope and decision

**Project reviewed:** `decisionDate` only. No other project is reviewed.

**Synthetic decision:** `reviewed_synthetic`

The field is acceptable as an explicitly labelled synthetic demonstration value. The requested value is `2026-10-04`, and the frozen mock carries the same value at `contract.decisionDate`. The PDF is clearly marked synthetic, unsigned, unenforceable, and not associated with a real supplier; therefore this review does not assert a real contract fact, a real notice status, or a production approval.

## Expected value and provenance

- Expected value: `2026-10-04` (date string).
- Frozen mock: `causora_day1_mock.json` → `contract.decisionDate` = `2026-10-04`.
- Review request: `review_request.json` → `assumptions[key=decisionDate].expectedValue` = `2026-10-04`; source says frozen synthetic contract input and explicitly says it is not inferred from the PDF.
- API contract: `API_CONTRACT.md`, section 2, states that `decisionDate` is a structured demo assumption and gives `2026-10-04` as the demo value.

The date is therefore reviewed as a configured demo assumption, not as a date extracted from the agreement.

## Six evidence checks

All six requested evidence items have exact quote matches to page 4 of `supplier_a_agreement.pdf`, with matching values in the frozen mock where represented:

| Evidence | Expected / confirmed value | Source and check |
|---|---|---|
| EV-014 | `60 days` | `supplier_a_agreement.pdf` p.4: written notice must be received at least 60 days before renewal; frozen mock `evidence[EV-014].extractedValue` = `60 days`, exact match. This is conditional logic, not an unconditional lock. |
| EV-019 | `24 months` | `supplier_a_agreement.pdf` p.4: automatic renewal for 24 months; frozen mock `evidence[EV-019].extractedValue` = `24 months`, exact match. |
| EV-021 | `14%` | `supplier_a_agreement.pdf` p.4: renewal is at a 14% higher unit price; frozen mock `evidence[EV-021].extractedValue` = `14%`, exact match. |
| EV-024 | `60%` | `supplier_a_agreement.pdf` p.4: minimum purchase equals 60% of forecast demand; frozen mock `evidence[EV-024].extractedValue` = `60%`, exact match. |
| EV-027 | `$25,000` | `supplier_a_agreement.pdf` p.4: early exit during the renewed term incurs a fixed $25,000 fee; frozen mock `evidence[EV-027].extractedValue` = `$25,000`, exact match. |
| EV-020 | Conditional auto-renew clause present | `supplier_a_agreement.pdf` p.4: automatic renewal applies only if written notice is not received at least 60 days before renewal. The review request quotes this as EV-020. The frozen mock does not include EV-020 in its `evidence[]` array or `contract.evidenceIds`; this is a traceability gap, not a contradiction. |

The PDF itself says the notice register supplies the notice-sent assumption and that the PDF alone cannot prove whether notice was sent.

## Date, notice, and forecast consistency

- `decisionDate` = `2026-10-04` and `renewalDate` = `2026-11-18` are explicit frozen synthetic inputs, not PDF-derived facts (`causora_day1_mock.json:contract.decisionDate`, `contract.renewalDate`).
- The frozen mock reports `daysToRenewal` = `45` and `noticeDeadline` = `2026-09-19`; these are consistent with the supplied dates.
- The notice register contains only synthetic rows, all with `valid_written_nonrenewal_notice=false`, including the 2026-10-04 decision-date audit row (`supplier_correspondence_log.csv`, rows dated 2026-09-01, 2026-09-19, and 2026-10-04). This supports only the synthetic assumption `noticeSent=false`; it does not establish that no notice existed in the real world.
- The renewal conclusion is conditional: `45 < 60` **and** synthetic `noticeSent=false`. An earlier valid written notice would change the outcome, as stated in `API_CONTRACT.md` section 2.
- `forecastBasis` = `locked-at-renewal` and `lockedForecastUnits24m` = `26,000` are explicit synthetic assumptions (`causora_day1_mock.json:contract.forecastBasis`, `contract.lockedForecastUnits24m`; PDF p.4). The 26,000 units are not historical-demand summation and are not claimed to be a model forecast output. `API_CONTRACT.md` section 2 states historical demand totals 25,936 and makes this distinction explicit.

## Limitations and required follow-up

1. The agreement is synthetic demo data, unsigned, unenforceable, and not associated with a real supplier (`supplier_a_agreement.pdf` p.1); no real contract verification is complete.
2. `decisionDate` and `renewalDate` are configured demo assumptions and are not independently established by the PDF.
3. `noticeSent=false` is supported only by the supplied synthetic notice register; it must not be interpreted as proof that no real-world notice was sent.
4. The conditional auto-renew logic must not be represented as an unconditional lock. Real notice timing, validity, receipt, and contractual interpretation require human/legal review.
5. EV-020 is supported by the page-4 quote and review request but is omitted from the frozen mock evidence array and `contract.evidenceIds`; the schema/provenance linkage should be repaired before production use.
6. The locked 26,000-unit figure is a fixed synthetic assumption, not a historical-demand sum or claimed model output. All real contract, source, implementation, and specification manual checks remain pending.
7. This review does not claim `manually_verified=true`, does not impersonate Wang Hao, and does not constitute a signature or approval for procurement.

## Conclusion

`decisionDate = 2026-10-04` is **reviewed_synthetic** for the narrowly scoped demo field. The value is consistent across the request, frozen mock, and API-contract demo assumption, while the associated six evidence items are quote-consistent on PDF page 4. The result is not a real-world contract verification and retains the limitations above.
