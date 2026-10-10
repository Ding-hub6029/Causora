# Wang AI Day5 最终补充复核

初次子任务报告 `WORK_SUMMARY.md` 是中间状态：57 tests、14 fixture samples 中一个 arbitrary-prose false acceptance。该报告与原始错误都保留，不改写成当时已通过。

## 后续实际修复

- 原 `unsupported_existing_evidence_citation` 接受了有 EV-024 但不受支持的“无限供货保证”。原输入/输出与摘要保存在 `prior-semantic-failure/`。
- 新 `test_day5_evidence_support.py` 首次 **9 failed / 2 passed**；日志 `red-evidence-support-before-fix.log`。
- 新 `agent_day4/evidence_support.py` 增加对当前合同没有支持的 unlimited/uninterrupted supply guarantee、zero stockout guarantee、exit/termination fee waiver 的**限定英文模式拒绝**。
- 在 `_scan_fields` 公共校验入口接入，对 Risk、Critic、Synthesizer 文本共同适用。首选 Critic 坏草稿被拒绝时仅允许合法回退；首选与回退都坏时失败，不生成假简报。
- 两个测试文件复测 **27 passed**，日志 `green-evidence-support-after-fix.log`。
- 时间/数量 suffix 单位错配也补充，`104 weeks` 不能配成 `104 days` 或 `104 units`；19 条数字声明 **19 expected outcomes met**，其中 **5/19 声明通过**数值校验，余下 14 条故意错误正确拒绝。不能写成真实模型数字忠实率 100%。
- simulation 的 dataVersion、scenarioId、schemaVersion 和 simulation request correlation 错配，新增四项零调用测试；测试首次错误使用冻结 dataclass 的日志保留，此为**测试代码错误而非产品故障**；修正后 4 passed。

## 最终逐样本记录

`final-offline-evaluation/` 内有 14 个作者已见的 fixture 样本，每条包含完整当前输入、输入哈希、预期、实际草稿/输出或错误、判定理由。`freeze.json` 在执行前绑定提示、源码、数据 fixture 和配置。旧16条 numeric结果与前次freeze均保留在 `prior-semantic-failure/`。

14/14 正确完成预期控制结果，不代表14/14全部流程成功。其中13个实际 fixture AI尝试仅5个完整成功，其余8个故障被安全拒绝；另1个 no-feasible 是正确零模型 code-only结果。请读 `OFFLINE_AND_REAL_METRICS.json` 的分子/分母与样本范围。

本次真实模型请求仍 **0**，Critic 真实检出率/误报率/数值忠实率/证据有效率/完整真实流程成功率均 **0/0、N/A**。所有 fixture 会显式 TEST_FIXTURE_ONLY，不能装成 teacher API、public AI 或真人审核。

## 残余限制

英文限定规则不覆盖任意语言、复杂否定或所有同义改写，也不是通用自然语言证据蕴含证明；不能把 quoteMatched 或 ID 有效当成结论支持。新增评测工具需要独立 statement—citation 标签与来源校验证据，而不是模型自称 `supported=true`。正式未知模型评测需外部新语料及独立授权，本次没有伪造。
