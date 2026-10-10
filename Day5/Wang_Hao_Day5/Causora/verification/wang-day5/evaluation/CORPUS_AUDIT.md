# Wang Day5 语料身份与重叠审计

**审计时间：2026-10-10（离线）。** 本报告没有读取或披露旧标签的完整 expected 值；完整机器可读的计数、ID、输入 payload 指纹和标签文件哈希在同目录 `corpus_audit.json`。未修改任何批准记录或 `verification/day5-current/` 原始证据。

## 结论

| 项目 | 结果 | 判定 |
| --- | ---: | --- |
| Ding 旧开发语料 | 12 条（`d001`–`d012`） | 作者可见的 synthetic development corpus；不可称未见。 |
| Ding 旧所谓 heldout 输入 | 30 条（`h001`–`h030`） | **INELIGIBLE / UNVERIFIED**，不纳入新评测。 |
| 旧 heldout labels | 30 条 | `AUTHOR_DRAFT_NEEDS_INDEPENDENT_REVIEW`；没有独立人工 oracle 批准。 |
| 旧 dev 与旧 heldout 的 case ID 交集 | 0 | 无重复 ID。 |
| 旧 dev 与旧 heldout 的规范化 model payload SHA-256 交集 | 0 | 无逐 payload 内容重复。 |
| 旧 heldout 与当前 shared/oracle controls | ID 与规范化 payload 均无交集 | 仅代表这几份文件比对；不等于证明旧语料未被历史调试。 |
| 当前主工程运行时是否引用旧 12/30 文件 | 未发现语料文件或 Python import | 唯一命中 `verification/wang-day5/version_comparison.json` 的历史文件清单（第 441–444 行），不是运行时调用。 |

**关键限制：** “无本工作副本 runtime 引用”不能证明旧 12/30 从未在其他历史副本、生成器或调试阶段暴露给人/模型。因此按要求保守标为 **INELIGIBLE_FOR_NEW_HELDOUT_AND_UNVERIFIED_FOR_HISTORICAL_PERFORMANCE**，不能沿用、不能称为新的 formal unseen，也不能用来补报 Critic 分数。

## 来源、标签与调试/历史使用证据

Ding 参考包的 `agents/wanghao-day3/agent_day3/evals/build_fixtures.py` 是该语料的生成器：

- 文件首注释明说是 **Synthetic layer-C draft corpus**、`LOCAL MOCK`、**not a Critic result or oracle**。
- `LABEL_STATUS` 固定为 `AUTHOR_DRAFT_NEEDS_INDEPENDENT_REVIEW`；生成 labels 时直接写入该状态。
- 生成器显式产出 `critic_dev.jsonl`、`critic_heldout_inputs.jsonl`、`critic_heldout_labels.jsonl`，并含开发/heldout 划分与随机打散。它既证明语料不是外部独立地面真值，也表明旧集的生成/调试路径可见。
- 参考版 `scoring.py` 明确写着：正式评分要求 `INDEPENDENTLY_REVIEWED`；Day3 draft labels 只能在显式 `--draft-rehearsal` 模式使用，不能产出 official heldout score。
- Ding 的 Day5 handoff 也要求新的 actual evaluation numbers；没有把这套草稿标签升级为独立审查批准。未发现可验证的 “从未调试/从未曝光” 声明或记录。

因此不能以“opaque IDs”或零交集作为独立未见证明。零交集仅是一个必要的文件级去重检查，不是充分的泄露审计。

## 历史归档（不覆盖 runtime）

保留了逐文件原始字节到：

`evaluation/day5/historical/ding_day3_synthetic_layer_c/`

| 文件 | SHA-256 |
| --- | --- |
| `build_fixtures.py` | `7803b928019f9b3957c67c81387118fd29f85942e0daa345fdfd5f68edaf9566` |
| `critic_dev.jsonl` | `3caebdb73919a304d63171c36eb19d2d3dd0baba26cc39cb790496407d86c53c` |
| `critic_heldout_inputs.jsonl` | `a412d5c3af6b4860aefb61801bcf83ab3c77c8f7e5d4a3808c4c7a1c9545084a` |
| `critic_heldout_labels.jsonl` | `06e76cd137eb8f59fa67d623fb379fed4438fbb1e7dd78e7a89fbf8fa6c75e7e` |

同目录 `SHA256SUMS` 是可复核清单。归档目录不在任何 runtime 路径，也不是 Day5 评测工具的默认输入。

## 正式新语料门槛

只有外部独立 custodian 在本实现者/模型开发者不可见答案的边界下新建 inputs 与 labels，并能提供：来源身份哈希、未用于调试说明、`INDEPENDENTLY_REVIEWED` 标签及审批记录，才能成为 **reserved future candidate**；完成 freeze 后仍需单独授权真实执行。当前没有符合这些条件的新 formal hidden corpus。
