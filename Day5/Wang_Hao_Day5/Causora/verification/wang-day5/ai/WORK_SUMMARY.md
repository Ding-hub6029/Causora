# Wang Hao Day 5：AI 可靠性工程工作总结

## 执行边界

- 主工程：`/home/ubuntu/causora_day5/main/Causora`
- 已先阅读：`DAY5_FINAL_STATUS.md`、`WANG_HAO_DAY5_HANDOFF.md`，以及 `agent_day4` 的 `pipeline.py`、`wire.py`、`numeric.py`、`evidence.py`、`inputs.py`、`business.py`、`allocation.py`。
- **全部新增评估均为 `TEST_FIXTURE_ONLY`**：运行前清空 `OPENAI_API_KEY`、`OPENAI_API_BASE`、`OPENAI_BASE_URL`、`OPENROUTER_API_KEY`；没有真实模型调用、真实密钥、Manus 代理或网络 provider 调用。
- 未修改 release 批准状态、已绑定哈希、部署、MC Matrix、Formula Trace 或业务重算逻辑；也没有虚构人工审批、参与者或真实模型检出率。

## 实际修复

| 文件 | 修改 | 修复原因 |
| --- | --- | --- |
| `agents/wanghao-day3/agent_day4/pipeline.py` | Synthesizer 的 `options` 与 `selectedOption` 仅保留 `id`、`shareA`、`terminateA`，不再转发未受信任的 `label`、`description`。 | 修复经验证的 option description 提示注入可抵达 Synthesizer payload。修复前后原始日志见 `red-option-description-injection-before-fix.log` 与 `green-option-description-injection-after-fix.log`。 |
| `agents/wanghao-day3/agent_day4/numeric.py` | 增加 `percentage_points` 数字表面形式识别；此类型不能绑定普通 `percent`/概率 fraction registry 引用。 | 修复 `8.7 percentage points` 被错误当作 `8.7%` 接受的单位混淆。修复前后原始日志见 `red-percentage-points-before-fix.log` 与 `green-percentage-points-after-fix.log`。 |

`business.py`、`allocation.py`、`evidence.py`、`inputs.py` 与 `wire.py` 经逐项检查后没有作 runtime 修改：现有严格 DTO、源 PDF/哈希绑定、D1/D2 分配事实、身份校验和 no-feasible 零调用路径满足本轮覆盖；不因测试而降低守卫。

## 选择性测试引入

新增目录：`agents/wanghao-day3/tests_day5/`。

- `day5_fixtures.py`：重写的窄范围 reviewed fixture 与内存 provider；所有响应带 `TEST_FIXTURE_ONLY` 标记并被记录用于审计。
- `test_day5_pipeline_reliability.py`：新增完整 CFO → COO → Risk → Critic → Synthesizer fixture 流程和 Day 5 负例。
- `test_day5_budget_portability.py`：按父代理要求，从参考包 **逐文件** 引入；使用本地 journal、真实 portalocker sidecar lock、spawn/thread 竞争，不发 HTTP、不初始化 SDK dispatch，未改预算 runtime。
- `test_day5_openrouter.py`：按父代理要求，从参考包 **逐文件** 引入；唯一调整是将两个 `day4_fixtures` 导入指向本目录的窄 fixture。文件内 `/models`、`/key` 和 completions 全为内存 fake；`unit-test-not-a-real-key` 仅是 mock 字符串。
- 参考与引入选择明细、未引入 live/historical 项目的理由记录于 `agents/wanghao-day3/tests_day5/README.md`。没有整目录覆盖。

## 覆盖与实测结果

最终命令：

```bash
cd /home/ubuntu/causora_day5/main/Causora/agents/wanghao-day3
unset OPENAI_API_KEY OPENAI_API_BASE OPENAI_BASE_URL OPENROUTER_API_KEY
/home/ubuntu/causora_day5/.venv/bin/python -m pytest tests_day5 -q -p no:cacheprovider \
  --basetemp /home/ubuntu/jobs/job_kANwFy9M/pytest-final
/home/ubuntu/causora_day5/.venv/bin/python -m compileall -q agent_day4 tests_day5
```

- **57 passed in 16.75s**；`57 tests collected`；没有子测试计数被并入该数字。
- `compileall` 成功；完整绿灯日志：`green-tests-day5.log`、`green-compileall.log`。
- 包含：百分比/百分点单位篡改、错误 evidence ID、已存在但不支持声明的 citation 样本、源 evidence/contract/option 描述提示注入、Critic 缺字段/超时/畸形 JSON fallback、角色 JSON 缺字段、身份不匹配、no-feasible 零调用、MC Matrix/Trace 不变、D1 混合最低 A 和 D2 B-only 非多元化。

## 逐样本离线评估证据

- `offline-ai-evidence.jsonl`：14 条逐样本标签、fixture 原始响应、实际结果与原因。
- 每个样本同时有独立 JSON（例如 `critic_timeout.json`、`no_feasible_zero_calls.json`、`d2_b_only_not_diversified.json`）。
- `offline-ai-summary.json`：`networkCalls: 0`、`realModelCalls: 0`、14 个样本、13 个符合预期的安全/流程结果、无失败的预期结果。

> 这些数字是确定性离线 fixture 覆盖，**不是**真实模型检出率、误报率、模型质量分数或公开 AI 成功率。

## 诚实保留的局限

`unsupported_existing_evidence_citation.json` 明确记录一个未解决的 **semantic false acceptance**：使用有效 `EV-024` 证据 ID 的任意文本“`The contract guarantees unlimited supply.`”仍可通过当前 ID/数字/已知业务语义守卫。`EV-024` 实际只支持最低采购承诺，不能蕴含“无限供应”。

因此该样本在 JSONL 中的 verdict 是 `UNRESOLVED_SEMANTIC_FALSE_ACCEPTANCE`，不被计为安全拒绝。要解决它，需要一个独立、可审计的**声明—证据蕴含规则/人工审核**机制；本轮未以宽松规则、假模型分数或虚构人工审核掩盖该缺口。
