# Wang Hao — Causora Day5 实际交付报告

日期：2026-10-10（UTC+8）。交付范围为当前唯一主工程上的技术完成、离线可靠性验证与可复核评测工具；**未声称新增真实模型、公开 AI 或人工签认成功**。

## 1. 唯一主工程与版本比较

- 主工程：`Deng_Jinzhu_Day5.zip/Causora`。
- 原交接所记部署基线：`4da7c5f8ed4939390b230e8de02bd513b11d96a8`。本次修订没有重新部署此线上工程。
- 先读取当前 `DAY5_FINAL_STATUS.md` 与 `WANG_HAO_DAY5_HANDOFF.md`。Ding Day5 只作前端及历史验收参考，Hackathon 只作 Day1–3 历史参考。
- 准备阶段逐文件 SHA 比较：235 相同、16 不同、71 main-only、446 reference-only。不同公共路径先保留主版本；选择性恢复测试/审计原件逐项记录，**没有旧包整目录覆盖**。
- 详见 `DAY5_WANG_CHANGELOG.md`、`verification/wang-day5/version_comparison.json` 和 `merge-and-change-record.json`。

## 2. 已复现的原始基线

在独立未改动副本实际执行：

| 原基线项目 | 实际结果 | 原始证据 |
| --- | --- | --- |
| 后端 + Day1/2/3 仿真测试 | **91 passed + 37 subtests passed** | `logs/baseline-backend.log` / `.xml` |
| 默认前端测试 | **57 passed** | `logs/baseline-frontend.log` |
| TypeScript 类型检查 | 通过 | `logs/baseline-typecheck.log` |
| ESLint | 通过 | `logs/baseline-lint.log` |
| Windows `.cmd` 目标脚本检查 | 三个入口引用的两个脚本缺失 | `logs/baseline-missing-launchers.json` |

未照抄历史数量。当前环境实际 Python3.12.3 / Node22.13.0 / npm10.9.2，精确依赖版本随包保存。

## 3. 实际生产修复

| 问题 | 修复 | 失败和复测记录 |
| --- | --- | --- |
| 概率百分比被错误标为百分点 | 独立识别 percentage points/pp/ppt，拒绝作为 percent/fraction 绑定 | AI 原红/绿日志 |
| 相同整数配不同时间或数量单位 | 数字后缀 weeks/days/months/units 与 registry 单位核对 | `ai/time-unit-original-vs-final.json`；19 个数字声明样本 |
| 不受信任 option 说明被传给 Synthesizer | 下游只保留 id/shareA/terminateA，不转发 label/description | option 注入 red/green |
| 已取消请求仍 fetch，或旧响应字段互相一致而非属于本次请求 | pre-aborted 零 fetch；Boardroom/Evidence header/envelope/outbound requestId 一致 | frontend 原 **57 pass/3 fail** → 当前绿灯；新增旧 Evidence 响应测试 |
| 无可行方案仍依赖 provider import/runtime | source-verified register 后先走 typed code-only 分支，零模型、无推荐；约束列表解冻为 JSON | backend 首次红灯、修复后 no-dispatch |
| 有效 EV 被配上合同不支持的无限供货保证 | targeted evidence_support guard 拒绝供货保证/退出费豁免等英文模式；只有合法回退可接替坏 Critic | **9 failed/2 passed** → 两文件 **27 passed**；原 false acceptance 完整保留 |
| 评测入口依赖主包缺失旧模块 | standalone answer-free loader + 新公平评测工具 | 独立 loader tests |
| Windows 安装/启动入口缺失 | 当前跨平台与 Windows 脚本补齐；模拟专用启动不继承密钥、付费授权或创建新预算 | launcher安全 **4 passed**；实际本地 launcher health/page 成功 |

**残余限制：** targeted evidence_support 是已测英文规则，不是通用、多语言自然语言蕴含证明；保留数字/证据校验与审核门禁，不能宣称任意证据都能判定结论支持。

## 4. 完整离线 AI 路径与故障覆盖

实际运行 CFO、COO、Risk → Critic → Synthesizer/Brief 的 `TEST_FIXTURE_ONLY` 流程。覆盖数字篡改/单位/百分点、未知 EV、现有 EV 不支持结论、来源/合同/option 提示注入、Critic 缺失/超时/畸形及合法同族回退、JSON 缺字段/异常形状、simulationId/dataVersion/scenario/schema/request 关联、等待期间新模拟完成旧响应迟到、失败后的 Matrix/Trace/Evidence 保留以及 no-feasible 零模型。

- 14 个已见 fixture 场景：**14/14 符合各自预期控制结果**。
- 其中 8 个恶意/畸形预期拒绝场景：**8/8 拒绝**。
- 2 个 clean fixture 控制：**0/2 误拒绝**。
- 13 个 AI fixture 尝试（不含 no-feasible code-only）：**5/13 完整五阶段成功**；8 个故意故障安全失败仍在分母，未删除提高分数。
- 19 个数字声明：**5/19 通过数值校验**，5 个有效控制均正确接受、14 个故意错误正确拒绝，**19/19 预期控制结果符合**。这不是实际模型数字忠实率。
- 6 个 source-backed Evidence lookup：**6/6 来源 quoteMatched**；不等于支持任意模型结论。

逐样本完整输入、预期、模型桩原始草稿/实际输出、失败理由、输入哈希及执行前配置/提示/源码哈希在 `ai/final-offline-evaluation/`；数字声明在 `ai/numeric-statements.json`。旧语义失败和前次结果/冻结在 `ai/prior-semantic-failure/`，未删除原样本。

## 5. 新真实模型指标（未执行）

| 指标 | 分子 | 分母 | 当前值 | 样本范围 |
| --- | ---: | ---: | --- | --- |
| Critic 检出率 TP/(TP+FN) | 0 | 0 | **N/A** | 无新增实际模型 Critic 未见样本 |
| 误报率 FP/(FP+TN) | 0 | 0 | **N/A** | 无新增实际模型 clean 样本 |
| 数字忠实率 | 0 | 0 | **N/A** | 无受检新增实际模型数字声明 |
| 证据有效率 | 0 | 0 | **N/A** | 无受检新增实际模型引用与独立蕴含核查 |
| 完整流程成功率 | 0 | 0 | **N/A** | 无新增实际模型完整流程尝试 |

完整机读分子、分母、样本范围与离线/真实分离：`OFFLINE_AND_REAL_METRICS.json`。不能把离线注入检出当真实 Critic 检出率，不能把公开模拟成功当完整公开 AI 成功。

## 6. 语料审计与公平比较

实际文件核查确认 Ding 历史开发 **12 条**、heldout inputs **30 条**、heldout labels **30 条**。dev/heldout ID 与规范化 payload 无交集，但标签为 `AUTHOR_DRAFT_NEEDS_INDEPENDENT_REVIEW`，synthetic 生成器与历史暴露不能证明未见，也未找到可信独立审批/未调试记录。因此 **INELIGIBLE / UNVERIFIED**，不重用于新的正式未见评测。

旧普通 LLM、LLM+代码、Causora 回答及评分全部保留原字节。旧 0/6 是提示未统一字段/陷阱 ID 而评分严格对象匹配的设计缺陷，不能写成 LLM 数学准确率为零；真实算错项也没有抹去。

新 `evaluation/day5` 已统一答案字段、精度、half-even 和 trap ID；输入/标签隔离、来源引用 registry、哈希冻结、无答案 dispatch、物理收据验证、输出封存、逐样本及失败保留。模型 `supported=true`、`stageStatus=PASSED` 自述不能作为证据/完整流程通过依据；新增数字或引用也纳入分母。离线文件绑定不能证明真实网络或真人审批，必须明确 imported-attestation 限制。

**真正新未见模型评测尚未完成**：没有新调用授权或符合条件的独立未知样本。本次不生成假答案/假标签/假外部收据。正式评测所需条件与最大调用数/硬费用上限提案单列在 `DAY5_EXTERNAL_REQUIREMENTS.md`。

## 7. 当前本地与公开运行事实

- 本地正式启动保留原 reviewed/policy/release 全部门禁；真实 HTTP reviewed Simulation v2 成功、完整三情景九 Trace 可用。
- 本地 smoke 两次同输入模拟确定性一致；六项来源 lookup 成功；模型未配置 Boardroom 明确 **503 provider_unavailable**，原 Matrix/Trace 和 Evidence 仍保留。这不是 AI 成功。
- 便捷 `start_day5.py --mode live` 实际前端 HTTP200、代理 `/health` reviewed simulation ready；**live 指模拟**。
- 公开主页与 `/health` 本次只读 HTTP200。没有向公开 Boardroom 发起模型调用，没有重新部署。本次不声称公开完整 AI 成功。
- 原包当时一次本地真实 AI 及旧三方案捕获在 `verification/day5-current/`，29 文件未改原字节；不当作当前修订真实模型复测。

## 8. 发布门禁、预算、人工边界

全部 `release/*` 和 Simulation v2 绑定文件原字节保留；没有改批准哈希、关闭守卫或代签人工审核。`security-and-release-audit.json` 记录未变更绑定与交付敏感形式扫描。

本次真实模型请求 **0**，费用 **0 USD**；没有教师密钥/Manus代理替代，没有购买服务器。预算 JSON+portalocker 的本地多进程/额度/损坏/未知费用保守锁定测试可证明本地行为，**不能证明免费 Render 重启持久性**。公开 AI 在可信共享持久预算解决前继续未启用；便捷启动不创建/重置/切换 journal。

真实参与者仅 Wang Hao；没有虚构额外用户或新增 Deng/Ding/Wang 本人签认。

## 9. 安装、启动、测试和文件完整性

详细可复制命令在 `DAY5_RUNBOOK.md`；Python3.12、Node22+，pip 安装 `requirements-day5-tested.txt`，前端 `npm ci`。一键复核：

```bash
python scripts/test_day5.py --build --local-http
python scripts/verify_package.py
```

ZIP 是完整工程，包含源码/数据/测试/既有批准/当前构建/原始失败与复测/冻结/报告；排除密钥、真实 `.env`、依赖目录、缓存。当前文件与 SHA 清单在根目录。压缩后核验 CRC、文件清单与每文件字节，并在独立目录重新解压复核。

原生 Windows 本次未实机执行，不能把设计兼容或 Linux spawn tests 写成 Windows 实测。

## 10. 最终一键验收

最终各命令退出码、真实数量与重解压验收结果保存在 `verification/wang-day5/final-one-command/summary.json` 和最终包完整性收据。下节记录最终实测；先前中间测试数量不能冒充最终验收。

### 最终已完成实测（非历史照抄）

最终命令 `python scripts/test_day5.py --build --local-http --output verification/wang-day5/final-one-command` **退出 0**，全部 10 个子命令退出码为 0：

| 当前最终项目 | 实际结果 | 原始日志（相对 verification/wang-day5/final-one-command） |
| --- | --- | --- |
| 后端 / Simulation / 接口 | **98 passed + 37 subtests passed** | `backend.log` |
| AI / 数字 / 证据 / 预算 / 故障回归 | **91 passed** | `ai-tests_day5.log` |
| 新评测工具 | **18 passed**；最后追加复核也是18 passed | `evaluation.log`、`evaluation-final.log`、`.xml` |
| 前端原测试与 Wang 新回归 | **62 passed** | `frontend.log` |
| TypeScript | 通过 | `frontend-typecheck.log` |
| ESLint | 通过 | `frontend-lint.log` |
| static / live 前端生产构建 | 两种均成功 | `frontend-build.log` |
| 实际静态 HTTP / proxy / 静态阻断 | **3 passed** | `frontend-production.log` |
| reviewed 发布配置原绑定 | 通过，不修改批准 | `release-config.log` |
| 本地真实 HTTP 模拟与 Evidence | 通过；两次确定性模拟、六项原文匹配、AI未配置503且数据保留 | `local-http.log`、`local-http/http-smoke.json` |

后端有一项 Starlette/httpx 弃用警告；另有 PyMuPDF `fitz` 弃用提示，不影响上述测试通过，未把警告静默成不存在。原生 Windows 与公开完整 AI 未执行。

正式未见条件与新模型授权仍未满足，不能用这些本地测试数字替代真实 Critic 检出率。

### 压缩后独立目录复核

实际将完整 ZIP 解压到新目录，在没有工作目录依赖路径的情况下执行：

- SHA 清单验证通过；ZIP CRC 和每文件字节检查通过。
- 相对路径开发 fixture freeze 在搬移后验证通过。
- 从重新解压工程启动 reviewed 后端，真实本地 HTTP 模拟、Evidence、未配置AI失败和数据保留通过。
- 解压后 AI 91 项 + 评测18项，合并 **109 passed**，未使用密钥/网络模型。
- 原始日志与 HTTP 响应纳入 `verification/wang-day5/zip-retest/`。

最终 ZIP 在纳入这些验收材料和报告修正后重打包；运行源码、模型提示、数据、release批准、评测冻结未改变。包外 `.integrity.json` / `.sha256` 是最终包CRC、字节、SHA和文件数收据，避免让ZIP自引用自身哈希。
