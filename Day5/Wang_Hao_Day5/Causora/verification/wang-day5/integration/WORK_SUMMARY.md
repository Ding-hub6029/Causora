# Wang Hao Day 5 集成与回归工作摘要

## 范围与边界

- 主工程：`/home/ubuntu/causora_day5/main/Causora`
- 部署基线：`4da7c5f8ed4939390b230e8de02bd513b11d96a8`
- 已先阅读 `DAY5_FINAL_STATUS.md` 与 `WANG_HAO_DAY5_HANDOFF.md`；`verification/wang-day5/version_comparison.json` 保持不覆盖。该比较记录为 **Deng 包唯一 authoritative source**、Ding 仅 reference，当前记录仍列出 235 个相同、16 个不同、71 个 main-only、446 个 reference-only 路径。
- 未改动 `frontend/lib/contracts-v2.ts`、`API_CONTRACT_V2.md`、`backend/backend/app/contracts_v2.py`、release 批准绑定、`agent_day4` 或 `evaluation`。
- 未调用模型、未调用任何密钥/外部 AI Provider、未部署、未购买服务器、未执行前端 build（最终 build 由主 agent 负责）。所有新增回归均为本地 `TEST_FIXTURE_ONLY` 文件门禁夹具或本地注入 fetch/await 边界。

## 修改内容

| 文件 | 修改 |
|---|---|
| `backend/backend/app/boardroom_adapter.py` | 对已注册且已做 source verification 的 `no_feasible_option` 在进入 `agent_day4` import、runtime/provider factory 前直接返回 typed no-feasible Brief：空 `agentOutputs` / `criticIssues`、`recommendedOptionId: null`、保留 Matrix 的 `constraintViolations`。因此不 dispatch AI、不构造假推荐。修复从不可变 record 取约束时须 `_thaw` 的本地序列化问题。|
| `backend/backend/tests/test_day5_wang_lifecycle.py` | 新增 3 个后端运行时测试：AI await 中新 simulation 完成后旧 Boardroom 响应被 recheck 以 `422 stale_simulation` 拒绝；provider setup 失败后 Matrix/Formula Trace 保留且 source-backed Evidence 可读取；no-feasible 真实本地分支不触发 provider factory、无 recommendation。覆盖 simulationId、dataVersion、scenario、requestId header/body 与 current-simulation header 关联。|
| `frontend/lib/boardroom-api.ts` | 入口即检查已取消的外部 `AbortSignal`，取消前不调用 fetch；成功 HTTP 响应要求 `x-request-id` 精确等于 outbound Boardroom request ID，避免 header 与 envelope/当前请求脱钩的迟到响应进入 UI。|
| `frontend/lib/evidence-api.ts` | 入口即检查已取消的外部 `AbortSignal`，取消前不调用 fetch；成功 Evidence 响应要求 `x-request-id` 与 validated envelope `requestId` 相同。保留既有 Evidence 的内部生成 request-id 兼容语义。|
| `frontend/tests/day5-wang-request-lifecycle.test.mjs` | 新增 4 个前端运行时测试：预先 aborted 的 Boardroom/Evidence 均零 fetch；Boardroom 的 header/envelope/outbound correlation mismatch 被拒绝；Evidence 的 header/envelope mismatch 被拒绝；形状正确但 server 不支持的 `EV-999` 必须到达 server 并以 404/not_found 收束。仅使用明确标记 `TEST_FIXTURE_ONLY` 夹具。|
| `verification/wang-day5/testcases/day5-wang-lifecycle.json` | 机器可读的 7 项 Wang Day 5 测试用例、范围和断言清单。|

`frontend/app/page.tsx` / `components/app-shell.tsx` 已复核：既有 `sequence`、AbortController 与 `isSameActiveRun` 检查会丢弃迟到的 Boardroom/Evidence 结果，因此此次无需改动 UI state shell；本次补齐的是 API helper 在 **signal 已先行取消** 时仍可能发出 fetch 的边界，以及 header/envelope request-id 关联。

## 红灯 → 修复 → 绿灯证据

| 阶段 | 实际结果 | 原始日志 |
|---|---:|---|
| 修改前前端回归 | **57 pass / 3 fail**（新增的 pre-aborted fetch 与两项 request-id mismatch 均如预期暴露问题） | `verification/wang-day5/logs/frontend-day5-wang-prefx-red.log` |
| 后端首次回归 | **1 pass / 2 fail**：一项测试最初误用了原本已为 -15% 的 fixture；另一个实际暴露 no-feasible 在 input validation 前未 short-circuit、返回 `simulation_source_unverified`，未能证明 no-dispatch | `verification/wang-day5/logs/backend-day5-wang-prefx-red.log` |
| 修复后 Wang 后端定向 | **3 passed** | `verification/wang-day5/logs/backend-day5-wang-green.log` |
| 修复后完整后端 | **98 passed，37 subtests passed** | `verification/wang-day5/logs/backend-full-suite-green.log` |
| 修复后前端 configured suite + Wang 文件 | **61 passed** | `verification/wang-day5/logs/frontend-full-plus-wang-green.log` |
| 修复后前端 configured suite | **57 passed** | `verification/wang-day5/logs/frontend-full-suite-green.log` |
| 前端 TypeScript | **pass** | `verification/wang-day5/logs/frontend-typecheck-green.log` |
| 前端 ESLint (`--max-warnings=0`) | **pass** | `verification/wang-day5/logs/frontend-lint-green.log` |

## 关键行为结论

1. **旧 AI 响应不会覆盖新 simulation**：测试在旧 Boardroom await 边界暂停，完成带不同 simulationId 的新 simulation 后才放行；旧请求得到 `422 / stale_simulation`，并且 header/body 的 `requestId` 均为旧 Boardroom request，`X-Causora-Current-Simulation` 指向 replacement。
2. **AI 失败不会抹除完成的 simulation**：provider setup 的本地失败后，原 simulation 的 Matrix、其 D1 Formula Trace、当前 run 及 EV-024 均仍可用，Evidence envelope 的 dataVersion 和 response header 均绑定原 run。
3. **无可行方案不派发 AI、也不产生推荐**：新的 adapter short-circuit 在 provider factory 前发生；formal typed response 明确为 `no_feasible_option`、`recommendedOptionId: null`，没有 agent output、Critic issue 或 fake recommendation。
4. **前端取消和关联 fail-closed**：外部 signal 在调用前已 aborted 时，两种 client 均不进入 fetch；Boardroom 成功响应还必须匹配 outbound ID，Evidence 成功 response header 必须与 envelope ID 一致。形状正确但未受 server 支持的 Evidence ID 不在客户端另造 DTO allowlist，仍由 server 的 404/not_found 决定。

## 限制与后续

- 此工作是本地、离线、无 provider 的生命周期/边界验证，**不构成公开完整 AI 成功、真实用户测试、团队签认或 release 批准**。
- 后端 no-feasible 测试使用现有 file-backed `TEST_FIXTURE_ONLY` reviewed fixture；慢 AI 仅为本地 coroutine 等待桩，用来复现并验证真正 route 的 await 后 recheck，未执行模型。
- 本次没有运行 production build，避免与主 agent 的最终 build 并发；也没有改动主 agent 的 baseline setup 修复或其 `test_day5_launcher_safety.py`。
