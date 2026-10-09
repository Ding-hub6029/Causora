> Historical v3 record retained for context. The current release is v4. See V4_DELIVERY_NOTES.md for current checks and remaining human tasks.

# Causora Day 1 — Verification Record (External Audit Remediation)

This record covers the **revised Day 1 static mock only**. It does not certify a real PDF parser, live simulator, agent orchestration, provider fallback or real-user study.

## Automated checks

From `causora/` run:

```bash
npm ci
npm run typecheck
npm run lint
npm test
npm run build
npm start
```

The revised suite reports **14/14 passing** checks (previous ZIP: 8/8). Its substantive data assertions include:

- All five source values appear in their preserved quotes. EV-019 maps to a renewal-term Business Variable. The Node test suite **parses the actual six-page PDF** and proves that all five complete quotes appear on their cited page 4, with wrong-page and tampered-value negative controls.
- Synthetic source files physically exist. 104-week CSV and inventory CSV row counts, PDF signature, XLSX signature and identical notice registers are checked. Separately, `pdftotext -f 4 -l 4 -layout public/demo/supplier_a_agreement.pdf -` was run and **all five complete source quotes were found on page 4**.
- Decision/renewal/deadline date arithmetic, `noticeSent=false`, and the renewal-lock rule are tested as separate inputs. The notice register is **synthetic**, not real-world negative evidence.
- Forecast basis 26,000 units × 60% = 15,600 Supplier A minimum. A −15% shock yields 22,100 realised demand and 2,340 units over the rolling-minimum benchmark. Critic holding deltas match the cost cells.
- Every scenario contains exactly one each of D0, D1 and D2 and one recommended cell. Every cell's actual A/(A+B) procurement ratio matches its option definition — **D1 is exactly 60/40 in all three scenarios**, including demand drop. All **9 TCO cost breakdowns add exactly to their cell**, purchase uses actual base unit prices, and the 14% renewal premium is counted exactly once. Termination fee applies to D2 only.
- Code-computed Decision Delta is compared against cells for **all scenarios**, not merely baseline. Agent and Critic numeric token templates resolve without a free-form numeric claim (except the symbolic option IDs D0/D1/D2).
- Golden Run has a complete independent snapshot of all 11 data groups, SHA-256 hash, matching data/seed/options and a UTC freeze timestamp not in the future. A mutated copy of the main mock data cannot change the frozen result.
- Contract/UI wiring tests check Golden status invalidation, disabled approval on uncomputed draft, scenario/option Formula Modal identity, modal keyboard handlers, State Studio forwarding, static `start` script and mobile status rule. These wiring tests supplement — do not replace — browser checks.

## Browser regressions exercised in the revised build

1. **Frozen Golden vs changed scenario:** after clicking Open Golden Run the visible badge read `CACHED · VERIFIED GOLDEN RUN`. Selecting lead-time stress removed it and showed `LOCAL MOCK · TRACEABLE`. The UI switched from the frozen snapshot back to normal mock data.
2. **State Studio:** within the same stage, clicking error → empty → loading produced the corresponding visible state cards. Restore local state returned to the dataset.
3. **Complete Evidence stack:** it displayed five rows. EV-019 opened the 24-month detail. With keyboard focus on the original trigger, the modal focused its close button. Escape closed the detail and restored focus to the Evidence stack trigger. An earlier programmatic `.click()` test did not focus its opener and therefore could not demonstrate restoration. The focused-keyboard regression did.
4. **Cell-specific Formula Trace:** Demand −15% / D1 remains `$419k`. After the independent allocation audit its corrected five lines are purchase **`$318,240`** (`15,600 A + 10,400 B`), illustrative holding **`$48,000`**, illustrative stockout loss **`$26,552`**, renewal premium **`$26,208`**, termination **`$0`**, totaling **`$419,000 ✓`**. These revised numbers, 60/40 share and data-derived note were reconfirmed in the r2 static browser. The earlier keyboard run verified Escape focus restoration.
5. **Draft disclosure and approval:** setting the risk threshold to 20% while Demand −15% was selected displayed the exact unsimulated assumptions in Decision Brief and **disabled Approve**. Returning to Scenario Lab and clicking **Restore preset inputs to enable approval** removed the warning and re-enabled Approve in the final static build.
6. **Mobile:** full 390px capture shows the `LOCAL MOCK · TRACEABLE` status chip at the top. Previous ZIP hid this badge. The proof cards remain stacked and readable.
7. **Static serving:** `npm start` served `/`, `/manus-routes.json`, `/icon.svg`, and an exported JavaScript chunk with HTTP 200. A path outside the output directory returned 404. The static host does not expose source files.

The **final v3 archive** was extracted into a fresh isolated directory. Using only files from that ZIP, `npm ci`, `npm run typecheck`, `npm run lint`, all **14/14 tests** and `npm run build` succeeded. Its export contained `out/index.html` and the searchable source PDF, establishing that the package is sufficient for a clean static rebuild rather than relying on this working directory's dependencies.

The first revision's perspective-collision check remains relevant: at 1280px, **five stages × three pointer positions** showed zero card intersections and zero sampled connector-card intersections. 1200/1199, 1024, 768 and 390px were inspected separately. The focused screenshot remains `artifacts/proof-engine-fixed.png`.

## Manual replay steps

1. Unzip and publish the **contents** of `out/` as a static site root, or run `npm ci && npm run build && npm start` (Node 22). Visit `/`.
2. Open each file in Data Intake (PDF, XLSX, two CSV files). Open EV-014 and click **Open synthetic source PDF · page 4**. Verify the five full quote sentences on that page. Open EV-019 from the Scenario Lab variable row and the full Evidence stack.
3. Select Demand −15%. Inspect D0/D1/D2 and open Formula Trace for each selected option. Verify that the five displayed amounts add up and the unit-price and premium convention are clear.
4. Move to Boardroom. Expand/collapse each role and compare guarded figures with the selected preset. Examine the Critic's forecast/commitment/demand structure and evidence buttons.
5. Change a demand or risk slider. Move to Brief. Verify that the draft warning appears and Approve is **disabled**. Return to Scenario Lab, restore preset inputs, and confirm approval is enabled again.
6. Open Golden Run. Observe the local-mock cache label. Change a scenario or slider. Observe it disappear. Test loading → empty → error directly inside State Studio.
7. Open Evidence stack with the keyboard. Tab and Shift+Tab must remain within the dialog, Escape must close it and return to the original button. Repeat with Formula Trace.
8. Review at desktop, 1200/1199px boundary, 1024px, tablet and 390px mobile, plus the OS reduced-motion setting if available. A **formal screen-reader audit has not been performed**.

## Candid limitations

The source PDF and register are **generated synthetic examples**. Matching their quotes is not a runtime validator. Holding and stockout cost components are illustrative preset aggregates rather than outputs from a 104-week simulation. `monteCarloRuns=0` explicitly signals this. The versioned backend API is an interface proposal, not running endpoints. No live Agent or Critic performance, backend health, provider timeout, actual supplier contact, real participant booking or production compliance was tested. **Full G1 should not be signed off on this basis.**
