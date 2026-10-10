# Causora - Ten-Minute Core Code Walkthrough

All narration and presenter instructions are English. Use Day5/Causora production source. Code links pin commit 1c558f50c400f9fd46acbd363be8bfeaa17cbc3f.

Code excerpts reproduce the pinned source. They are not screenshots of the GitHub interface. Website captures show historical verified results.

Target duration: 10 minutes. The schedule includes pauses and browser switching. Read the narration, not presenter instructions, filenames, URLs or source code.

## Page 01: The decision problem

00:00-00:40

Presenter only: Show the Matrix. Introduce the case, then open the production source folder Day5/Causora.

Hello, we are Ding Xiangfeng, Deng Jinzhu and Wang Hao. Causora helps procurement teams review a supplier renewal with finance and operations. A cheaper quote can hide a locked purchase obligation when demand falls. This demonstration uses reviewed synthetic data. I will show the actual production source, including simulation, real AI requests, and the conditions that enable a human decision. The website shows the result. The code explains its basis.

After saying "The code explains its basis." turn to page 02.



## Page 02: Input validation and source identity

00:40-01:10

Presenter only: Open lines 59-78. Point to model validation, read_source_manifest and the frozen source hash.

This function validates the typed request and loads the source manifest. It checks the frozen contract hash, dataset identity, and renewal date. Demand and Supplier A orders must meet sample thresholds. Supplier B lacks sufficient history, so its fallback remains an explicit assumption. These checks prevent an edited source or a different dataset from silently becoming the published calculation input.

After saying "These checks prevent an edited source or a different dataset from silently becoming the published calculation input." turn to page 03.

[monte_carlo.py L59-L78](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/backend/backend/simulation_day3/monte_carlo.py#L59-L78)

## Page 03: Shared Monte Carlo draws

01:10-01:45

Presenter only: Stay in monte_carlo.py. Scroll to lines 81-97 and point to PCG64, the array dimensions and the digest.

PCG64 creates master draws using the recorded seed. Demand samples come from weekly history, A lead times from observed orders, and B from an explicit triangular distribution. Each trial has a path of one hundred and four weeks. Options share these external-world draws. Common random numbers reduce comparison noise caused by separate lucky samples. The digest supports repeatability checks. This still relies on historical representativeness and does not capture every future dependency.

After saying "This still relies on historical representativeness and does not capture every future dependency." turn to page 04.

[monte_carlo.py L81-L97](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/backend/backend/simulation_day3/monte_carlo.py#L81-L97)

## Page 04: Inventory state and replenishment

01:45-02:30

Presenter only: Show lines 141-172. Point to available, filled, shortage, position and fixed_a. Explain the operations rather than reading every line.

Each trial advances inventory weekly. Arrivals join opening stock. Filled demand is the smaller of demand and available inventory. Remaining demand becomes shortage. Inventory position includes stock already on order, so replenishment accounts for future deliveries. D1 respects fixed A and B purchase quotas. The other branch applies the retained-A minimum. The obligation uses the locked forecast when demand contracts. The code simulates inventory and ordering consequences rather than asking an LLM to guess cost.

After saying "The code simulates inventory and ordering consequences rather than asking an LLM to guess cost." turn to page 05.

[monte_carlo.py L141-L172](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/backend/backend/simulation_day3/monte_carlo.py#L141-L172) [monte_carlo.py L205-L207](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/backend/backend/simulation_day3/monte_carlo.py#L205-L207)

## Page 05: Cost aggregation and risk metrics

02:30-03:00

Presenter only: Show lines 223-237. Mention lines 209-213 and 50-55 for the cash percentile. Point to stockoutProbability and serviceLevel separately.

The displayed total reconciles purchase, holding, shortage loss, renewal premium, and termination fee. Currency uses integer micro-dollars and explicit rounding. Cash P90 comes from trial cash spending and excludes shortage loss. Stockout probability counts trials with any lost units. Service level measures filled units divided by demand. The trace keeps component means and a sample path. A sample realised path must not be confused with the aggregate result.

After saying "A sample realised path must not be confused with the aggregate result." turn to page 06.

[monte_carlo.py L223-L237](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/backend/backend/simulation_day3/monte_carlo.py#L223-L237) [monte_carlo.py L209-L213](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/backend/backend/simulation_day3/monte_carlo.py#L209-L213) [monte_carlo.py L50-L55](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/backend/backend/simulation_day3/monte_carlo.py#L50-L55)

## Page 06: Feasibility before ranking

03:00-03:35

Presenter only: Open select_by_scenario, lines 193-217. Point to failed, eligible and min.

Selection belongs to code. Each option must satisfy contract feasibility, the stockout threshold, and the cash ceiling. Only surviving options enter the cost ranking. Minimum expected TCO wins, with an identifier as the tie break. If nothing survives, the response says no feasible option. In the recorded baseline, D1 is eligible. This explains why the cheapest cell in a stressed scenario need not win. The AI cannot replace constraint screening.

After saying "The AI cannot replace constraint screening." turn to page 07.

[interfaces.py L193-L217](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/backend/backend/simulation_day1/interfaces.py#L193-L217)

## Page 07: Evidence verification against source

03:35-04:05

Presenter only: Open lines 280-298. Point to _source_text, quote matching and _value_matches_contract.

The verifier reads the source page again. It requires the quotation to appear there and checks the extracted value against the simulation contract. Earlier checks restrict evidence identifiers and required records. It derives success after verification instead of trusting a caller-provided quoteMatched flag. This connects a claim to a specific source. It verifies the reviewed case and does not guarantee interpretation of arbitrary contracts.

After saying "It verifies the reviewed case and does not guarantee interpretation of arbitrary contracts." turn to page 08.

[boardroom_adapter.py L280-L298](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/backend/backend/app/boardroom_adapter.py#L280-L298) [boardroom_adapter.py L239-L267](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/backend/backend/app/boardroom_adapter.py#L239-L267)

## Page 08: Backend admission to the AI pipeline

04:05-04:35

Presenter only: Show lines 795-823. Point to repository.resolve_formal before and after the awaited pipeline.

The Boardroom route validates the request and resolves the exact reviewed simulation. It then awaits the formal AI pipeline. Afterwards, it resolves the simulation again. That second check matters because a newer simulation may arrive during model calls. An outdated review must not return as current. The route returns a typed envelope with simulation and provider status headers, or a structured failure for the frontend.

After saying "The route returns a typed envelope with simulation and provider status headers, or a structured failure for the frontend." turn to page 09.

[boardroom_adapter.py L795-L823](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/backend/backend/app/boardroom_adapter.py#L795-L823)

## Page 09: Parallel roles and bounded inputs

04:35-05:10

Presenter only: Show lines 202-203, then briefly show SYSTEM at line 16. Use the role names to explain assigned responsibilities.

CFO, COO, and Risk run in parallel. Each receives verified facts projected for its role. The system instruction treats document text as data and binds numeric claims to code-controlled references. Every role draft passes validation. A bounded correction can repair a returned invalid draft when the budget allows. A transport failure cannot become a valid opinion. Roles contribute perspectives, while the simulator remains responsible for numerical comparison.

After saying "Roles contribute perspectives, while the simulator remains responsible for numerical comparison." turn to page 10.

[pipeline.py L202-L203](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/agents/wanghao-day3/agent_day4/pipeline.py#L202-L203) [pipeline.py L16-L16](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/agents/wanghao-day3/agent_day4/pipeline.py#L16-L16) [pipeline.py L208-L217](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/agents/wanghao-day3/agent_day4/pipeline.py#L208-L217)

## Page 10: Critic coverage and compound risk

05:10-05:40

Presenter only: Show lines 240-249. Point to required coverage and compound_required.

The Critic examines the roles together. The checker requires coverage of renewal, locked forecast, minimum commitment, demand, cash, holding cost, omissions, and conflicts. Falling demand with excess locked commitment requires a compound risk involving multiple functions. Issue references and prose pass further checks. Gemini is the preferred Critic, with a labelled fallback. Different model families diversify the review process but do not prove independent judgement or a measured detection rate.

After saying "Different model families diversify the review process but do not prove independent judgement or a measured detection rate." turn to page 11.

[pipeline.py L240-L249](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/agents/wanghao-day3/agent_day4/pipeline.py#L240-L249) [pipeline.py L257-L276](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/agents/wanghao-day3/agent_day4/pipeline.py#L257-L276)

## Page 11: Numeric and business guardrails

05:40-06:20

Presenter only: Show lines 305-328. Then point to _scan_fields at lines 37-48 and business_check. Keep the speech on these mechanisms.

The Synthesizer must use an existing eligible option and structured response. Numeric validation scans its recommendation and rationale against the current registry. A rejected numeric draft gets at most one correction here and passes the same checks again. Business checks separately reject semantic mistakes, such as calling B-only sourcing diversification. The response exposes a passed guardrail after relevant checks succeed. These mechanisms reject specific errors. They cannot certify every qualitative sentence.

After saying "They cannot certify every qualitative sentence." turn to page 12.

[pipeline.py L305-L328](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/agents/wanghao-day3/agent_day4/pipeline.py#L305-L328) [pipeline.py L37-L48](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/agents/wanghao-day3/agent_day4/pipeline.py#L37-L48) [numeric.py L116-L135](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/agents/wanghao-day3/agent_day4/numeric.py#L116-L135)

## Page 12: The real OpenRouter request

06:20-06:55

Presenter only: Show lines 824-841. Point directly to chat.completions.create and returned model, usage and identifier fields. Never show environment values.

This is the real provider call. The provider reserves a conservative cost bound before dispatch. The awaited chat completions request goes to OpenRouter. The transport records returned model, call identifier, usage, and verified cost. The response still needs schema and content validation. The key comes from the backend environment and stays out of frontend code. We can show external execution, but cannot inspect a model hidden thought process.

After saying "We can show external execution, but cannot inspect a model hidden thought process." turn to page 13.

[openrouter_provider.py L824-L841](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/agents/wanghao-day3/agent_day4/openrouter_provider.py#L824-L841) [openrouter_provider.py L919-L950](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/agents/wanghao-day3/agent_day4/openrouter_provider.py#L919-L950)

## Page 13: Persistent cost accounting

06:55-07:25

Presenter only: Open lines 70-96 and show SELECT ... FOR UPDATE. Mention the reserve and mark methods without exposing database credentials.

PostgreSQL stores the public budget ledger. The transaction locks its shared row before updates, preventing concurrent requests from assuming the same available budget. Reservations precede dispatch. Verified usage settles returned cost, while uncertain remote outcomes retain conservative reservations. Current key availability bounds spend. A normal review has five stages and a six-call whole-run cap. Removing a cumulative test count does not remove this per-review bound or trigger a recharge.

After saying "Removing a cumulative test count does not remove this per-review bound or trigger a recharge." turn to page 14.

[postgres_budget.py L70-L96](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/agents/wanghao-day3/agent_day4/postgres_budget.py#L70-L96) [postgres_budget.py L99-L125](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/agents/wanghao-day3/agent_day4/postgres_budget.py#L99-L125) [openrouter_provider.py L412-L437](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/agents/wanghao-day3/agent_day4/openrouter_provider.py#L412-L437)

## Page 14: Frontend request and stale-result control

07:25-08:00

Presenter only: Show runSimulation, lines 268-305. Then show the result check at lines 332-341 for runBoardroom.

The frontend captures request identity and a sequence counter before simulation. It applies a response only when that sequence and the current request still match. Boardroom also checks the selected scenario. Editing assumptions during an outstanding request prevents its old response from overwriting the workspace. These conditions explain why input changes require fresh simulation and why navigation must not silently combine an old brief with a new matrix.

After saying "These conditions explain why input changes require fresh simulation and why navigation must not silently combine an old brief with a new matrix." turn to page 15.

[page.tsx L268-L305](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/frontend/app/page.tsx#L268-L305) [page.tsx L332-L341](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/frontend/app/page.tsx#L332-L341)

## Page 15: Approval conditions and local scope

08:00-08:35

Presenter only: Show lines 128-135, then decide at lines 426-444. Point to browser-local-only and localStorage.

Approval requires a reviewed, decision-ready simulation, matching Boardroom, eligible selection, and passed numeric guardrail without rejected claims. Cached and draft states remain outside the gate. The click handler checks again. It records the option and identity with browser-local-only scope and local storage. This is a demo human review record. It executes no purchase or supplier contract. A disabled button indicates a missing prerequisite.

After saying "A disabled button indicates a missing prerequisite." turn to page 16.

[page.tsx L128-L135](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/frontend/app/page.tsx#L128-L135) [page.tsx L426-L444](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/frontend/app/page.tsx#L426-L444)

## Page 16: Production startup and traffic control

08:35-09:00

Presenter only: Show lines 21-30 and 35-43, then review_admission.py lines 20-44. Do not open secret settings.

The launcher forces OpenRouter and rejects development overrides before serving the API. Vercel serves the frontend and Render runs Python. Admission allows one active review in the configured worker and a short cooldown. Busy requests receive a structured response before provider dispatch. The finally block releases admission on failure. This limits overlapping reviews alongside persistent cost accounting.

After saying "This limits overlapping reviews alongside persistent cost accounting." turn to page 17.

[render_start.py L21-L43](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/deployment/render_start.py#L21-L43) [review_admission.py L20-L44](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/backend/backend/app/review_admission.py#L20-L44)

## Page 17: Failure preservation and evidence of execution

09:00-09:30

Presenter only: Show lines 332-343, then switch to the recorded successful Brief screenshot. Describe historical evidence honestly.

The failure branch changes Boardroom state and preserves the validated matrix and formula trace. Retrying AI does not discard simulation. Recorded verification returned all five stages for about two cents. That proves a complete real review executed. The supplied screenshot shows a historical success, not a fresh call in this video. Cached results stay read only. Public services can still fail, so retained results need clear labels.

After saying "Public services can still fail, so retained results need clear labels." turn to page 18.

[page.tsx L332-L343](https://github.com/Ding-hub6029/Causora/blob/1c558f50c400f9fd46acbd363be8bfeaa17cbc3f/Day5/Causora/frontend/app/page.tsx#L332-L343)

## Page 18: What makes the implementation distinctive

09:30-10:00

Presenter only: Return to the recorded Brief or your current validated run. End after the final sentence. Do not request another AI run just to fill time.

Causora connects procurement decisions to repeatable simulation, source evidence, constrained AI review, and a matching human record. Its distinction lies in these connected mechanisms and their inspectable code. This case uses synthetic data and limited user testing. Wider testing and independent benchmarks remain next. Today we can show real model calls and a clear boundary between computed facts, model interpretation, and human choice. Thank you.

End recording after thanking the audience.


