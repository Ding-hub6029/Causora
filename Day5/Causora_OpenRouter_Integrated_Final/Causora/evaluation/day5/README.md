# Day5 公平评测（离线、可冻结、不可伪造）

> **本模块不调用模型、不读取密钥、不联网，也不默认配置付费 runner。** 它只生成/校验本地评测工件；真实执行必须由另获授权的外部运行方完成后再导入。

## 当前状态

- **真实 Critic / 三方法比较：N/A。** 本次没有新的授权、模型调用、网络请求或真实 prediction capture。
- `fixtures/` 是**作者可见开发夹具**，其标签状态为 `AUTHOR_DRAFT_NEEDS_INDEPENDENT_REVIEW`，只能验证 loader/scorer；绝不能称为正式未见集、hidden set 或模型性能。
- `historical/ding_day3_synthetic_layer_c/` 是逐文件归档的旧 `12 dev / 30 heldout` 语料，状态为 **INELIGIBLE / UNVERIFIED**；见 `verification/wang-day5/evaluation/corpus_audit.*`。它不得重用为新的未见评测。

## 安全边界

| 边界 | 实现 |
| --- | --- |
| 输入与标签分离 | `load_inputs()` 递归拒绝 `expected`、`labels`、`answer`、`ground_truth` 等输入侧泄露字段；`load_labels()` 只在 scorer 侧读取。 |
| Dispatch 不泄露 ID / 标签 | `build_dispatch_bundle()` 仅导出有序 `input` payload 数组；没有 `caseId`、split、source、单条哈希或标签。导入时才按顺序恢复内部 ID。 |
| Freeze | `create_freeze()` 哈希 inputs、labels、prompt、无密钥 model config、scoring source、source-corpus identity **和 independent evidence registry**；`verify_freeze()` 对任一变化 fail closed。 |
| 证据支持 | `evidence_registry.json` 冻结每个 `evidenceRef + claimId` 的实际 source quote 与 `supportStatus`。模型答案没有、也不允许伪造 `supported` 布尔；scorer 只读取 registry。 |
| 输出防篡改 | 导入与封存都记录 raw capture、provider audit receipt、stage-validation receipt 的**相对路径 + SHA-256**。封存后评分入口重新打开并哈希这些物理文件，而不信任单独的 hash 字符串。 |
| 不把夹具当性能 | `TEST_FIXTURE_ONLY` 收据可走 contract-validation 路径，却标记 `TEST_FIXTURE_ONLY_VALIDATION_NOT_PERFORMANCE`，不能生成模型性能指标。非测试 `ACTUAL_CAPTURE` 可生成逐样本 metrics，但固定标记 `SCORED_EXTERNAL_CAPTURE_UNVERIFIED_NOT_OFFICIAL`；文件绑定不能单凭自身证明真实网络调用。 |
| 审批真实 | Freeze 一律标记 `AUTHOR_PROGRAM_DRAFT_PENDING_INDEPENDENT_REVIEW`。来源字段、`labelStatus: INDEPENDENTLY_REVIEWED` 和 caller/author 都只是导入声明，离线工具没有可信独立审核身份根，故不会自动产生 official candidate 或把 unverified metrics 说成 official score。 |

## 统一的三方法答案合同

`fair_answer_schema.json` 对下列方法使用同一 `causora.day5.fair-answer.v1`：

1. `causora_pipeline`
2. `plain_llm`
3. `llm_plus_code`

每个 case 输出同一字段：`criticVerdict`、`criticReasons`、`numericStatements`、`evidenceCitations`、`stageStatus`。每一个数值 statement 都必须有：

```json
{
  "statementId": "prompt-visible neutral id",
  "value": "decimal string",
  "precision": {"scale": 2, "rounding": "ROUND_HALF_EVEN"},
  "roundingTrapId": "prompt-visible trap id"
}
```

因此旧三方案控制题中「输出字段自行命名」或「陷阱标识未统一」造成的严格对象匹配 0/6，不能再被误报为数学准确率 0%。旧结果仍是历史证据，不能重贴标签、映射成新分数或用旧 LLM 输出灌入新计分器。

## 外部独立 hidden corpus 的交接合同

评测供应方必须在**本实现者和模型执行方不可见答案**的边界下，分别交付：

- `inputs.jsonl`：每行仅 `caseId`、可选 `split`/`source`、和无答案 `input`。正式 set 的 `source` 应写明外部独立来源、生成日期及未用于调试的声明。
- `labels.jsonl`：每行 `caseId`、该整条 input 的 canonical SHA-256、`labelStatus`、以及独立 `expected`。`expected` 需要 `criticShouldReject`、数字 statement（值/scale/ROUND_HALF_EVEN/roundingTrapId）、需支持的 citation、所有必经 stages。
- `prompt.md`：三方法都使用的、只描述 schema 和可见规则的冻结提示；不得含 expected labels。
- `model_config.json`：无任何 API key、token、secret 的模型 ID 与参数。三个方法各有单独 freeze，比较时应控制相同的新 inputs / answer schema / scoring revision。
- `source_corpus_identity.json`：`causora.day5.source-corpus-identity.v1`，记录 corpus 状态与身份；它会被 freeze 哈希。
- `evidence_registry.json`：`causora.day5.independent-evidence-registry.v1`；每条必须有 `evidenceRef`、`claimId`、非空的 source `quote` 和 `SUPPORTS`/`DOES_NOT_SUPPORT`。每个 label 所要求的 citation 都必须能在此找到 `SUPPORTS` 的实际 quote。

> 不要把任何已经被本实现者、模型开发者或调试人员看过答案的候选语料称为正式独立未见。此仓库目前**没有**新正式 hidden corpus；未来外部提供的新 corpus 才可成为 `reserved future candidate`，且仍须独立标签核查与未用于调试证明。

## 离线运行顺序

以下命令没有任何网络/provider 代码。请在仓库根目录并使用 `/home/ubuntu/causora_day5/.venv/bin/python`：

```bash
# 1) 冻结（路径必须指向外部独立供应的实际文件；freeze 文件不可覆盖）
python -m evaluation.day5.cli freeze \
  --inputs /secure/inputs.jsonl --labels /secure/labels.jsonl \
  --prompt /secure/prompt.md --model-config /secure/model_config.json \
  --scoring-source evaluation/day5/core.py --source-corpus /secure/source_corpus_identity.json \
  --evidence-registry /secure/evidence_registry.json \
  --author external-corpus-custodian --output /secure/freeze.json \
  --authorization-status PENDING_SEPARATE_PROVIDER_AUTHORIZATION

# 2) 仅生成模型可见的 payload（无 case ID / labels）
python -m evaluation.day5.cli dispatch --freeze /secure/freeze.json --output /secure/model_dispatch.json

# 3) 获得单独授权后，由外部 runner 实际执行；本模块不提供自动 runner 或凭据。
#    runner 回传 ordered responses 的 external-actual-capture JSON；capture 必须相对路径绑定可读取的
#    provider audit receipt 和独立 stage-validation receipt（两者均含 SHA-256）。
python -m evaluation.day5.cli import-actual --freeze /secure/freeze.json \
  --capture /secure/external_actual_capture.json --output /secure/bound_predictions.jsonl

# 4) 固化外部 attestation；任一篡改都会被拒绝。score 输出可复现的逐样本 metrics，
#    但状态固定为 SCORED_EXTERNAL_CAPTURE_UNVERIFIED_NOT_OFFICIAL，不自动提升为 official performance。
python -m evaluation.day5.cli seal --freeze /secure/freeze.json \
  --predictions /secure/bound_predictions.jsonl --output /secure/prediction_seal.json
python -m evaluation.day5.cli score --freeze /secure/freeze.json \
  --predictions /secure/bound_predictions.jsonl --seal /secure/prediction_seal.json \
  --output /secure/metrics.json
```

未授权时只可生成真实 N/A，不得创作预测：

```bash
python -m evaluation.day5.cli pending-metrics --output verification/wang-day5/evaluation/metrics.json
```

## 指标和失败处理

每个 case（包括 `timeout`、`error`、`cancelled`）都有 `expected`、实测 `actual`、`reasons` 和严格 provenance；不会因失败而悄悄从样本中删除。

| 指标 | 分子 / 分母 | 失败规则 |
| --- | --- | --- |
| Critic 检出率 | `TP / (TP + FN)` | 对应 faulty case 未完成视为 `FN_EXECUTION_FAILURE`。 |
| 误报率 | `FP / (FP + TN)` | clean timeout/error 是不确定执行失败，单列 `cleanExecutionFailuresExcludedFromFPR`，不伪装为 TN。 |
| 数字忠实率 | `validated statements / checked statements` | 标签 obligations 与模型额外 statement 的并集都进入分母；缺失、超时、未知 extra 均失败。value、precision 和 trap ID 均须匹配。 |
| 证据实际支持率 | `registry-supported citations / checked citations` | 标签 obligations 与模型额外 citation/claim 的并集都进入分母；`citationId + evidenceRef` 只由 frozen registry 的 source quote/claim 判断，未知 extra 失败。 |
| 完整流程成功率 | `all required stages PASSED / independently validated attempts` | 只有独立的 physical stage-validation receipt 可进入分母；没有该 receipt 时为 `NA`，模型自填 `stageStatus` 不算 proof。 |

任意分母为 0，结果为 `status: "NA"`、`value: null`，并带原因，而不是填 0% 或 100%。

## 回归自测

```bash
PYTHONDONTWRITEBYTECODE=1 /home/ubuntu/causora_day5/.venv/bin/python \
  -m pytest evaluation/day5/tests/test_day5_evaluation.py -q -p no:cacheprovider
```

最近实际运行：**18 passed**（本仓库指定 venv；无网络、无 provider、无密钥）。测试覆盖 registry quote/claim 绑定、递归 input label leakage、错误 JSON、输入/source hash 篡改、模型 `supported` 自证拒绝、actual extra 数字/claim 分母、clean failure 的 FPR 分离、模型自报 stages 只能得到 workflow `NA`、外部 modelId 不匹配、每必经 stage 的独立 receipt、portable copy、封存后物理 receipt 重读篡改拒绝、import 后 failure log 保留、self-declared corpus/labels 不能自签 official candidate，以及 `agent_day4/eval_interface.py` 无缺失的 `agent_day3.evals.scoring` 依赖。
