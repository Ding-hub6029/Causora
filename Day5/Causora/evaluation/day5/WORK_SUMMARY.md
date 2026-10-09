# Wang Day5 评测工程工作总结

## 本次实际完成

1. 完成 `evaluation/day5/` 离线评测合同；**没有网络、模型 SDK、密钥、自动 provider runner 或模型调用**。
   - 输入与 labels 分离；`load_inputs()` 递归拒绝 answer/label/ground-truth 等泄露字段，labels 按完整 input 的 canonical SHA-256 绑定。
   - 三种方法共用 `causora.day5.fair-answer.v1`。citation 只有 `citationId + evidenceRef`；模型没有且不能提交 `supported` 自证字段。
   - `evidence_registry.json` 冻结 `evidenceRef + claimId + quote + supportStatus`。每个 label 要求的 citation 必须有 registry 中的实际 quote 支持；numeric/citation 评分使用 **expected obligations 与模型实际 extra 的并集**，未知 extra 进入分母并失败。
   - critic FPR 仅以可判定 clean verdict 的 `FP / (FP + TN)` 计算；clean timeout/error/cancelled 单列 `cleanExecutionFailuresExcludedFromFPR`，不伪作 TN。
   - workflow 只读取物理、独立 `stageValidationReceipt`：它必须按顺序覆盖每个 response、绑定 freeze/response hash，并列出每个 required stage。模型 `stageStatus` 仅显示；无独立 receipt 的 test harness workflow 为 **N/A**，不会得到自报 100%。
2. Freeze 现必需 `evidence_registry_path`，CLI 的 `freeze --evidence-registry` 与 README 已同步。freeze 哈希 inputs、labels、prompt、无凭据 config、scoring source、source corpus 和 evidence registry；任一 source/input/label/registry 改动均 fail closed。
3. 外部 capture 现在要求并验证真实存在的相对路径文件记录：
   - raw capture 的 `execution.auditReceipt` 与 `stageValidationReceipt` 均为 `{path, sha256}`；路径相对 raw capture。
   - import 后 prediction provenance 为相对 prediction 文件的 `rawCapture`、`providerAuditReceipt`、`stageValidationReceipt` 文件记录；可随完整目录 portable copy。
   - import/seal/score 均重新读取、哈希并校验物理 raw/receipt，且 score 在任何 eligibility 判断前重读它们；不只相信声明的 hash 字符串。
   - `execution.modelId` 必须等于冻结 `model_config.modelId`，同时绑定 config hash、run ID、provider call count、responses 与 stage 结果。
4. 真实性与审批边界已明确：文件 SHA 与 audit receipt 只能证明本地文件绑定，**不能证明 provider 外部网络调用真实发生**。普通外部 `ACTUAL_CAPTURE` 可输出逐样本、可复算的指标，但固定标记 `SCORED_EXTERNAL_CAPTURE_UNVERIFIED_NOT_OFFICIAL` 且 `officialEligible: false`；其 provenance 仍标记 `EXTERNAL_CAPTURE_ATTESTED_UNVERIFIED`。含 `TEST_FIXTURE_ONLY` 的收据仅用于 validation，标记 `TEST_FIXTURE_ONLY_VALIDATION_NOT_PERFORMANCE`，绝不输出 model-performance metrics。
5. source identity 的 `formalEligibility`、label 的 `INDEPENDENTLY_REVIEWED` 字符串和 freeze caller/author 都只是导入声明，不是可信独立人工批准。离线模块没有身份/信任根，故不会把它们自动提升为 official candidate，也不会把 unverified metrics 称为 official score。现有 author-seen fixtures 与 Ding 历史 synthetic corpus 都保持 **INELIGIBLE / UNVERIFIED**；未改旧原始评分/归档。
6. 保持 `agents/wanghao-day3/agent_day4/eval_interface.py` 的独立 answer-free loader；没有恢复任何缺失 `agent_day3.evals.scoring` 依赖。

## 本地实际验证

| 项目 | 实际结果 |
| --- | --- |
| 指定解释器 | `/home/ubuntu/causora_day5/.venv/bin/python` |
| 编译检查 | `core.py`、`cli.py` 通过 `py_compile` |
| 模块 pytest | **18 passed**（0.16s） |
| 命令日志 | `verification/wang-day5/evaluation/day5_evaluation_pytest.log` |
| 新模型/provider/网络调用 | **0 / 0 / 0** |
| 新真实 Critic prediction | **0** |
| 新真实三方法性能 score | **0；N/A** |

回归覆盖：registry quote/claim 绑定、错误 JSON、input label leakage、freeze input/source 篡改、模型 `supported` 自证拒绝、numeric/evidence actual extra 分母、FPR clean failure 分离、workflow 自报 N/A、external model mismatch、required stage receipt coverage、portable copy、seal 后物理 receipt 重读、test-only 永不评分、self-declared formal corpus/labels 不自签 official candidate、failure log 保留，以及 Day4 独立 loader。

## 当前限制（如实保留）

- 本仓库没有新的外部独立 hidden corpus、可信独立人工审核记录、真实 provider 授权或可信外部执行 read record。
- 不应把 `fixtures/`、`TEST_FIXTURE_ONLY` 收据、Ding 旧 12/30 synthetic 语料、或上述 contract test 输出称为模型性能。
- 未来若获得单独授权与可信外部审核/执行证据，应由授权方保存可审计原件；本模块仍不读取密钥、不执行 provider 调用，也不会代替人工批准。
