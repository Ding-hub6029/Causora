# Deng Jinzhu - Day6 Delivery Report

## Frozen numbers

Baseline TCO: D0 USD 365,811, D1 USD 348,040, D2 USD 356,665. D1 minus D0: TCO -17,771 and P90 -20,908.

D1 decomposition: procurement 318,240 + holding 3,590 + shortage loss 2 + renewal 26,208 + exit 0 = 348,040.

Raw stockout probability: D0 .919, D1 .008, D2 .895. Display: 92%, 1%, 90%. The exact D1-D0 delta is -91.1 percentage points, not the difference between rounded labels.

Demand -15% TCO: D0 310,547, D1 358,161, D2 306,401. Lowest cost alone does not establish feasibility. Lead-time stress: D0 361,502, D1 347,640, D2 356,665. See final-numbers.csv. Service level is not 1 minus stockout probability.

## Reproducibility and performance

The 10,000-run local preview took approximately 0.51 seconds. Repeating a fixed seed produced the same matrix hash. Seeds 1042026, 1042027 and 1042028 differed by at most 0.78 percentage points in stockout probability. This does not replace the reviewed 1,000-run public result. Peak RSS was not measured. AI network latency is separate from pure simulation time.

## Regression and handoff

Backend 24 tests, AI/evaluation 125 tests, frontend 62 tests and static deployment 3 tests passed. Four Golden Evidence records and tamper rejection passed. Fourteen offline failure cases passed. Automated checks do not constitute a participant's signature.

Wang Hao's historical feedback is provided as a labelled English summary. Deng's unperformed user tests are not reported as completed. Follow Recording_Script.md and Screenshot_Checklist.md. Keep LIVE/CACHED labels visible. Do not splice mock outputs into a live demonstration. The 160-second script is ready, but final recording and upload remain Day7 work.
