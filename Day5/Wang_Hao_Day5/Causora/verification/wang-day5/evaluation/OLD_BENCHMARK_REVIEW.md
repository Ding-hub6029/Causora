# 既有 Day5 三方案基准复核（原件未改）

## 固定原始证据

本复核**没有改写** `verification/day5-current/` 的 capture、prompt、label、批准或比较结果。关键原件的 SHA-256：

| 原件 | SHA-256 |
| --- | --- |
| `benchmark_actual_comparison.json` | `74dc428f0de6cc24354d0967375e15984a14fbb481ee79d2c1ec294de03a6b3d` |
| `plain_llm_capture.json` | `5b5a2d922cc0f9b2180a4b051e998c4cfae359dab5e232596e36cd2714d16af2` |
| `llm_plus_code_capture.json` | `161b357b321debcbdecbac0df07d607710dc90ae88ec3beeddcb48a78fbf8269` |
| `expected_labels.json`（旧 shared controls） | `eff577407b054fab3f57bea6d8c35e241ffab5c3b33b1a89818bc654027ecc1a` |

## 为什么旧普通 LLM / LLM+code 的 0/6 不是“数学准确率为零”

旧 `score_shared_benchmark.py` 的 `exact_answer_equal()` 对整个 `answer` JSON 对象做严格键集合与递归值比较；`score_completed_capture()` 对每题调用它。可是在旧 prompt 中只要求 `"answer": {}`，并**没有**向两种外部方法冻结每题同一 answer 字段结构；而 Causora 控制 runner 使用已知标签结构。模型自行命名的语义字段因此会被严格对象比较计作不等，即使某些计算或规则判断的语义可能正确。

同样，poison-pill 评分要求固定标识符，而旧提示没有提供完整统一的标识符表。因此 `benchmark_actual_comparison.json` 中普通 LLM 与 LLM+code 的 `answerAccuracy.correctCaseCount = 0 / 6` 是“旧 schema 下完整对象不相等”的结果，**不是**可推广的“数学准确率 0%”数学结论。这个限定也已在原 `Day5-三方案对比报告.md` 中记录。

这不表示所有输出正确：原报告举出至少一个独立于字段名的实际计算错误（持有成本计算）；本次不会掩盖该事实。

## 本次的处理

- 不把旧 LLM capture 映射到新的 schema 后再计算高分。
- 不重贴旧 expected labels，也不称旧 controls 为新 unseen set。
- 新的 `evaluation/day5/fair_answer_schema.json` 为 Causora、plain LLM、LLM+local code 冻结同一输出字段、`precision.scale`、`ROUND_HALF_EVEN` 和 `roundingTrapId`。
- 新测必须使用外部独立的新 inputs，labels 单独保存并绑定输入哈希；未经新授权没有任何真实三方法比较。**当前新真实比较：N/A。**

旧比较只保留为实际发生过的历史试验及评分设计缺陷记录，不能替代新的公平性能测量、完整供应链性能、公开 AI 流程、人工 oracle 审查或团队签认。
