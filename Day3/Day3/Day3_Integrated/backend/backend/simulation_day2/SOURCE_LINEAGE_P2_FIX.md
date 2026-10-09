# P2 Fix: Intermediate Weekly Demand Must Match Raw Sources

The Deng Day 2 fix strengthens `read_source_manifest()` without changing shared v1 or Day 1 originals. It does not approve data/policy or release official results.

The old code checked five source hashes and manifest Pydantic shape. Swapping demands [250,279] to [279,250] on 2024-10-07/14 preserved 104-week continuity, total, dataVersion and raw hashes, yet changed weekly simulation.

1. Before parsing, require whole original manifest SHA-256 `607ae2aedc059b1b9bea8fe46874ebee1868b4569132e94e2319072dc751fc3a`, derived from Deng's supplied Day 1 snapshot. This covers every demand/PO/inventory/notice/assumption field. It is a frozen source digest, not Wang's signature.
2. After checking five raw sources, independently parse UTF-8 historical CSV in physical order and compare all 104 week_start/units_demanded/provenance rows. Even replacing the allowed manifest hash in a test cannot hide a row swap against unchanged CSV.
3. Mismatch raises ValueError and produces no internal preview. Public boundary emits v1 503 ApiFailure/dataset_unavailable. Valid preview includes intermediateManifestSha256 in its identity. No old mock or no-feasible substitution.
4. Original five sources and manifest remain unchanged under demo-2026.10.04-v4. Engine SHA and regenerated previewId change. Future real snapshot changes require team review, new dataVersion, baseline and tests. Editing only the accepted hash cannot bypass row checks.

| Case | Verified result |
| --- | --- |
| Rebuild original manifest | All fields match. First demands [250,279]. |
| Swap [279,250], retain CSV/hashes/total/version | Whole-manifest rejection, no result, public 503. |
| Test accepts tampered manifest hash but CSV unchanged | Independent row-level rejection. |
| Change quote, inventory, notice or forecast provenance | Whole-manifest rejection. |
| Change raw CSV only | Existing five-source hash rejection. |

Historical outstanding gates: six clauses + five assumptions 11/11 pending. Inventory bridge/price/lost margin/holding/replenishment remain UNAPPROVED_TEST_INPUT. This fix alone supplies no probability/P90 or approvable recommendation.
