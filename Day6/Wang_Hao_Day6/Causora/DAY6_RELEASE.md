# Causora - Day6 Release and Handoff

All three packages contain the same source snapshot. Deploy one project, not three competing copies.

Live: https://causora-one.vercel.app/
API: https://causora-api.onrender.com
Repository: https://github.com/Ding-hub6029/Causora

## Frozen interpretation

- Horizon: 104 weeks / 24 months. Dataset ds-001. Seed 1042026. Formula tco-v1. Reviewed synthetic demonstration data.
- Public simulation and Golden use 1,000 Monte Carlo runs. The 10,000-run benchmark is a local mathematical preview, not a production upgrade.
- D0 keeps A. D1 keeps A's minimum share and introduces B. D2 exits A, pays the USD 25,000 termination fee, and purchases from B only. D2 is not diversification.
- Contract: 60-day notice, 24-month renewal, 60% minimum share, 14% renewal premium. Demand falls 15% to 22,100 while A's locked minimum remains 15,600. Distinguish locked forecast from rolling demand.
- Code computes numbers. OpenRouter generates qualitative role reviews, Critic and Brief. Validation does not expose a model's internal reasoning. Outputs may vary.
- Distinguish LIVE, CACHED historical real runs and Day2 MOCK. Cache replay is read-only and makes no new model call. A review cannot be reused for a different simulation, scenario or data version.
- Approve and Reject record browser-local choices. They are not legal signatures, supplier commitments or permanent server approvals.

## Verified evidence

Backend: 24 tests. AI and evaluation: 125 tests. Frontend: 62 tests plus 3 static deployment tests. Type checking, lint and live/static builds passed. Admission tests: 3 passed, including 2 already counted in the 149 combined tests.

Golden passed the production validator with four Evidence records. Scenario tampering was rejected. Provider receipts are archived separately from 14 offline TEST_FIXTURE_ONLY cases. Offline success is not model recall.

Public admission allows one concurrent review and a 15-second minimum start interval in one worker. Rejected requests return 429 without entering the model and retain the Matrix. Exceptions release the slot. Multi-worker deployment needs distributed admission control.

The 10,000-run preview reproduced the same matrix hash for the same seed. Maximum stockout variation across three seeds was 0.78 percentage points. All nine Golden cost decompositions reconcile. Local computation took approximately 0.51 seconds. Windows peak RSS was not measured.

## Freeze rules and boundaries

Fix reproducible bugs only. Changes to formulas, contract interpretation, prompts, models, timeouts or identity fields require relevant regression and a new Golden export. Follow Causora/DEPLOYMENT_GUIDE.md. Credentials remain in backend environment variables. Packages exclude credentials and private budget files. The free database expires on 2026-11-09 and needs maintenance for longer operation.

G6 is not fully green. The final 2-4 minute video has not been recorded or uploaded. Formal Devpost submission and member-account verification remain Day7 work. This round has no recorded genuine incognito or unfamiliar-device acceptance. Only Wang Hao provided real user feedback. No additional participants or signatures are invented.

Real AI under 45 seconds, ten complete online successes and independently unseen Critic recall of at least 80% are not established by qualified evidence. Preserve historical failures and run the full live flow before recording.
