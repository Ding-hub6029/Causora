# Real HTTP Monte Carlo integration runs

All runs used the supplied latest Day3 service, synthetic unreviewed inputs, 1,000 trials per cell, and decisionReady=false. Statistics below are copied from the returned matrix, never inferred from a sample path.

| Run | Simulation ID | Numerical scenario change versus base |
| --- | --- | --- |
| http_base | `sim-dev-unreviewed-9d1891657ae72d846c4e` | False |
| http_demand_changed | `sim-dev-unreviewed-4dc7c8a40a8349ab134e` | True |
| http_lead_changed | `sim-dev-unreviewed-c41106036d3e3cbda147` | True |
| http_browser_numbers | `sim-dev-unreviewed-492e97c52ca86b1f98ae` | False |

DataVersion correctly remains `demo-2026.10.04-v4--UNREVIEWED_DEV_ONLY` because the source dataset is unchanged. Changed computational inputs have new simulation IDs; all new HTTP captures have distinct request IDs and bound request/result hashes. Browser-style integer numeric spelling changes the canonical request identity but not numerical results.

| Run / scenario | Option | Expected TCO (USD) | Cash P90 (USD) | Stockout probability | Service level |
| --- | --- | ---: | ---: | ---: | ---: |
| http_base / baseline | D0 | 365811 | 369631 | 0.919 | 0.9975587333515997 |
| http_base / baseline | D1 | 348040 | 348723 | 0.008 | 0.9999872470571912 |
| http_base / baseline | D2 | 356665 | 361811 | 0.895 | 0.9923284518883901 |
| http_base / demand-drop | D0 | 310547 | 316020 | 0.259 | 0.9997254931734355 |
| http_base / demand-drop | D1 | 358161 | 358829 | 0.0 | 1.0 |
| http_base / demand-drop | D2 | 306401 | 312919 | 0.956 | 0.9898072769330017 |
| http_base / lead-stress | D0 | 361502 | 364775 | 0.881 | 0.9971134174902078 |
| http_base / lead-stress | D1 | 347640 | 348159 | 0.006 | 0.9999973879514729 |
| http_base / lead-stress | D2 | 356665 | 361811 | 0.895 | 0.9923284518883901 |
| http_demand_changed / demand-drop | D0 | 269842 | 279861 | 0.185 | 0.9998045552029955 |
| http_demand_changed / demand-drop | D1 | 364954 | 365538 | 0.0 | 1.0 |
| http_demand_changed / demand-drop | D2 | 272089 | 281830 | 0.947 | 0.9926540156568266 |
| http_lead_changed / lead-stress | D0 | 352411 | 353741 | 1.0 | 0.9504789402243066 |
| http_lead_changed / lead-stress | D1 | 347630 | 347654 | 0.557 | 0.997929336942621 |
| http_lead_changed / lead-stress | D2 | 356665 | 361811 | 0.895 | 0.9923284518883901 |

All three scenarios were analysed for each of the four HTTP captures: twelve scenario analyses, each returning CFO/COO/Risk DEV_ONLY. Those saved OFFLINE_SELECTOR analyses use a deterministic claim selector and are not AI prose. A separate saved MODEL_PROXY analysis used actual concurrent model calls on the base demand-drop result.

The 104-week sample path in each trace is exactly one realised trial. It cannot reproduce the aggregate probability, average costs or P90 by itself; validation checks counter/denominator/rank identities and binds statistics to matrix/trace. No independent full-trial P90 recomputation is claimed.
