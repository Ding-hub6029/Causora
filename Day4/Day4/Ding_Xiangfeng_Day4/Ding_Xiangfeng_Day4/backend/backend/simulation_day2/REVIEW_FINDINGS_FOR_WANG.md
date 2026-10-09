# Deng's Day 2 Source Notes for Wang Hao (Not Human Sign-off)

**Historical Day 2 status:** 11/11 pending, confirmedValue=null, reviewerName/reviewedAtUtc/acknowledgement empty. These are source comparisons, not Wang's approval, signed statement or promotion. Wang must personally inspect sources and decide. The original bound template is `../evidence_day2/examples/pending_review/review_request.json`. That Wang module is absent from Deng's standalone test package.

Sources: synthetic supplier agreement PDF p.4, correspondence CSV, frozen Day 1 mock and historical demand CSV. PDF p.4 is explicitly SYNTHETIC / NOT A REAL CONTRACT. Coordinates below are PDF points (x0,y0,x1,y1). Each complete sentence occurs once on p.4 and matches the pending ledger location.

| Evidence | Coordinates | Source wording and interpretation |
| --- | --- | --- |
| EV-014 | (54.0,170.2,543.7,185.3) | If written notice is not received at least 60 days before renewal, the agreement automatically renews. The condition is timely receipt of written notice. PDF cannot establish actual sending/receipt. |
| EV-019 | (54.0,198.2,435.5,213.3) | The agreement automatically renews for 24 months at a 14% higher unit price. Read with EV-014's condition. |
| EV-021 | Same as EV-019 | 14% means renewalPriceIncreasePct=.14. Do not uplift base purchase and add premium again. |
| EV-024 | (54.0,226.2,499.7,241.3) | The renewed term has a minimum purchase commitment equal to 60% of forecast demand. minPurchaseShareA=.6. Not sales share or realized demand. |
| EV-027 | (54.0,254.2,423.3,269.3) | Early exit during the renewed term incurs a fixed termination fee of $25,000. Once, not weekly. |
| EV-020 internal ledger | (54.0,198.2,435.5,213.3) | Establishes a renewal clause exists, but its single quoted sentence omits EV-014's condition. Wang must read both. If insufficient alone, keep pending/add notes or jointly revise template and regenerate bound scope. Never silently alter hashes or infer actual renewal from sentence two alone. |

Five separately reviewed demo assumptions: decisionDate=2026-10-04 and renewalDate=2026-11-18 come from mock, not PDF facts. NoticeSent=false means three supplied synthetic CSV rows have valid_written_nonrenewal_notice=false, not proof about real correspondence. ForecastBasis=locked-at-renewal is the team's synthetic interpretation, not legal inference from forecast demand. LockedForecastUnits24m=26000 matches the PDF's explicit synthetic-cycle forecast and mock, not historical total 25,936.

Derived, not new quoted facts: renewal minus decision =45 days. Renewal minus 60 days =2026-09-19. 26,000 x .6=15,600. RenewalLocked requires both timing and synthetic notice=false.

Wang's historical next steps: personally inspect p.4, CSV, mock and original request. Copy the template, enter actual name/current UTC time/acknowledgement and independently decided values. Retain pending or reject with reasons if uncertain. Only after all confirmations generate a separate reviewed synthetic version with `python -m evidence_day2.cli promote ...` and verify. Neither step was performed by Deng. No formal jinzhu_contract_input.json was supplied here.
