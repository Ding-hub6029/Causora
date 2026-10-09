# Causora: Contract and Assumption Verification Results

English translation of Wang Hao's original Chinese audit record. The adjacent `WangHao-human-confirmation.docx` is preserved byte for byte and remains the authoritative evidence. This translation does not add an approval, change its scope or establish an exact signing time. Review date in the original: 2026-10-07.

## I. Contract clauses (six items)

| Check | Conclusion | Content actually seen in source | Evidence source/page |
| --- | --- | --- | --- |
| Is the notice period 60 days? | Confirmed | “If written notice is not received at least 60 days before renewal, the agreement automatically renews.” The agreement renews automatically if written notice is not received at least 60 days before renewal. | supplier_a_agreement.pdf p.4, Renewal and minimum purchase — evidence page. EV-014 |
| Is renewal 24 months? | Confirmed | “The agreement automatically renews for 24 months at a 14% higher unit price.” | Same PDF p.4. EV-019 |
| Is there automatic renewal if timely notice is not received? | Confirmed, but must say conditional | The clause links automatic renewal to the condition that written notice is not received at least 60 days before renewal. This is a conditional automatic-renewal clause, not an unconditional automatic renewal. | Same PDF p.4. Wording as above. EV-014/EV-020 |
| Is renewal uplift 14%? | Confirmed | “at a 14% higher unit price.” The unit price increases by 14% upon renewal. | Same PDF p.4. EV-021 |
| Is minimum purchase share 60%? | Confirmed | “The renewed term has a minimum purchase commitment equal to 60% of forecast demand.” The minimum purchase commitment during the renewed term equals 60% of forecast demand. | Same PDF p.4. EV-024 |
| Is termination fee USD 25,000? | Confirmed | “Early exit during the renewed term incurs a fixed termination fee of $25,000.” Early exit during the renewed term requires payment of a fixed termination fee of $25,000. | Same PDF p.4. EV-027 |

## II. Assumptions (five items)

| Check | Correct statement | Content actually seen in source | Evidence source/page |
| --- | --- | --- | --- |
| Adopt decision date 2026-10-04? | Confirm adoption of this assumption | The frozen project input sets contract.decisionDate to 2026-10-04. This date is not inferred from the contract PDF. | agents/wanghao-day3/fixtures/causora_day1_mock.json lines 115-117. No contract page |
| Adopt renewal date 2026-11-18? | Confirm adoption of this assumption | The frozen project input sets contract.renewalDate to 2026-11-18. This date is not inferred from the contract PDF. | Same JSON lines 115-118. No contract page |
| Is there a record of timely notice being sent? | None found in supplied project records. Whether sent in reality cannot be confirmed | The CSV contains a 2026-09-19 notice_deadline_audit_no_notice_entry record and a 2026-10-04 decision_date_register_audit_no_notice_entry record. Both have valid_written_nonrenewal_notice=false. The CSV provenance is marked synthetic_mock_not_a_real_supplier_record. Therefore, the supplied synthetic records contain no valid notice entry, but it cannot be confirmed whether notice was sent in reality. It must not be stated that notice was sent. | supplier_correspondence_log.csv lines 2-4. No contract page |
| Adopt forecast basis locked-at-renewal? | Confirm adoption of this assumption | The project input sets contract.forecastBasis to locked-at-renewal, meaning the forecast is fixed at renewal. This is a project demonstration assumption, not a fact proven by the contract. | causora_day1_mock.json lines 123-128. PDF p.4 fixes a synthetic-cycle forecast but cannot replace the judgment that this is a team assumption |
| Adopt locked 24-month forecast of 26,000? | Confirm adoption of this assumption | The project input sets contract.lockedForecastUnits24m to 26,000. The PDF states: “For the synthetic scenario only, the renewal-cycle forecast is fixed at 26,000 units for the coming term.” This is a synthetic scenario/team assumption, not a real forecast result or a historical-demand total. | causora_day1_mock.json lines 123-130. Supplier_a_agreement.pdf p.4 |

## III. Item-by-item judgments in the Word document

| Judgment | Correct? | Explanation |
| --- | --- | --- |
| 60-day notice | Yes | Explicit wording on PDF p.4. |
| 24-month renewal | Yes | Explicit wording on PDF p.4. |
| Automatic renewal without timely notice | Yes, but must say conditional | Word document already states this is not unconditional renewal. |
| 14% renewal uplift | Yes | Explicit wording on PDF p.4. |
| 60% minimum purchase | Yes | Explicit wording on PDF p.4. |
| USD 25,000 termination fee | Yes | Explicit wording on PDF p.4. |
| Decision date 2026-10-04 | Yes, as team assumption | Say “Confirm adoption of this assumption.” |
| Renewal date 2026-11-18 | Yes, as team assumption | Say “Confirm adoption of this assumption.” |
| “Notice has been sent” | No | Replace with “No valid notice entry was found in the supplied synthetic project records. Whether notice was sent in reality cannot be confirmed.” |
| Forecast locked at renewal | Yes, as team assumption | Do not describe as contract fact. |
| Locked forecast 26,000 | Yes, as team assumption | Do not describe as an actual forecast result. |

## IV. Sources and limitations

supplier_a_agreement.pdf has six pages. All six reviewed clauses are on p.4. Its first page explicitly labels it synthetic demo data, not a signed or enforceable real contract.

supplier_correspondence_log.csv has three data records. All valid_written_nonrenewal_notice values are false. Provenance identifies a non-real supplier record. It supports only “no valid notice entry in the supplied synthetic records.”

causora_day1_mock.json is the frozen demonstration input, including decisionDate, renewalDate, noticeSent=false, forecastBasis=locked-at-renewal and lockedForecastUnits24m=26000. These are adopted project inputs/assumptions, not facts manually inferred from a real contract.

## Reviewer's confirmation (translated)

“I am Wang Hao. I have personally checked the six contract clauses and five assumptions in this corrected version, confirm the conclusions above, and accept these assumptions for this project's synthetic demonstration. Review date: 2026.10.7.”

Original document SHA-256: `588ea89123cfeb69ad9b904bd0cef4f2272407db39b3ee70ea8c0ae71bd53310`.
