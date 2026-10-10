# Day5 数据、身份与业务含义复核

## 来源与不可改动范围

唯一工程来自 `Deng_Jinzhu_Day5.zip/Causora`，公开部署基线由交接文件记载为 `4da7c5f8ed4939390b230e8de02bd513b11d96a8`。本次交付是该包上的技术修订，**未部署到 Vercel/Render**，不能把修订源码冒充线上版本。Ding 包与 Hackathon 是参考而非覆盖源。

Simulation 请求维持 v1，成功响应维持 `causora.contract.v2`；Boardroom 与 Evidence 维持 v1；Formula Trace 维持 `causora.formula-trace.v1`、`tco-v1`。本文件是解释材料，不替代或重签 `API_CONTRACT_V2.md` 与 release 记录。

## 身份绑定

| 字段 | 用途 | 拒绝条件 |
| --- | --- | --- |
| simulationId | 已完成模拟的身份；AI 仅解释这个保留结果 | 未找到、已被同 dataset 新模拟取代，或上下文不符合正式路径 |
| dataVersion | 来源/审核数据版本；不是单独的运行 ID | 请求、Simulation、Trace 或 Boardroom 版本不一致 |
| scenarioId | 当前情景，baseline / demand-drop / lead-stress | 结果来自其他情景，或未在当前请求中定义 |
| requestId | 单次 HTTP 请求关联；模拟请求与 Boardroom 请求各自拥有独立 ID | 响应 envelope 与本次 outbound ID 不一致；客户端读取的 header 也必须一致 |
| sourceSha256 | 原文件物理字节身份，内部证据/Trace 验证使用 | 来源文件缺失、内容变动、与 Trace 来源不符 |
| pin_snapshot_sha256 | AI 输入快照的内部绑定，不是人工批准 | 已冻结输入与当次使用数据不一致 |

Evidence v1 公共 DTO 不随意新增哈希字段；内部验证会从实际 PDF 计算来源哈希。页码一基；定位 bbox 使用 PDF.js 底部左侧用户坐标，不能直接混用 PyMuPDF 顶部左侧坐标。引用存在、原文精确匹配与支持某个结论是不同检查：**quoteMatched=true 不能证明任何任意结论正确**。

## 数值与统计对象

| 类别 | 原始量 | 展示与判断 |
| --- | --- | --- |
| 金额 | USD；MC 原始成本均值及每成本展示整美元有 rounding audit | 精确规则按原字段/对应原始审计定义执行，不反推 compact display |
| 数量 | units，24m 需求/固定采购；周轨迹逐周数量 | 不把 USD 当 units，不把时间数量当概率 |
| 时间 | weeks：104 周；合同 notice 是 days、renewal term 是 months | 不暗中将 days/weeks/months 互换 |
| 概率 | 原始 0–1 fraction | 展示 percent 为 fraction × 100；不是百分点差 |
| 概率差 | deltaStockoutPp / deltaServicePp，单位 percentage points | 差值 `(p_option-p_D0)*100`，不同于相对百分比变化 |
| stockoutProbability | `trials_with_at_least_one_lost_unit / monteCarloRuns` | 任一 lost unit 的试验比例 |
| serviceLevel | `fulfilled_units_all_runs / demand_units_all_runs`；总需求为零时实现定义为 1 | 是汇总单位满足比例，**不应当作 1-stockoutProbability** |
| cashOutflowP90 | 每次试验的 purchase / holding / renewalPremium / terminationFee 各组成先 whole USD half-even 舍入，再相加的现金流出 | excludedNonCashComponents 为 stockoutLoss；nearest rank `ceil(0.90*N)`；不是原始未舍入现金 P90、TCO P90、缺货损失 P90或平均现金 |
| samplePath | 某个真实模拟 trial 的 104 周路径 | 不是均值/聚合结果，不用它重新计算替代 MC 汇总 |

数字忠实率的计数单位必须是受检**声明**，不是 pytest 项数；证据有效率的计数单位是受检**引用**，必须同时验证来源与结论支持。完整流程成功率必须包含 CFO、COO、Risk、Critic、Synthesizer/Brief 全部必需阶段，不能用模拟 HTTP 200 充数。

## 当前业务规则

- D0：保持 A 基线。
- D1：保留 A 合同最低采购量，同时增加 B；不是退出 A。
- D2：退出 A，转向 B。降低对 A 的依赖不等于降低总体供应商集中度，**B-only 不叫供应商多元化**；适用退出费依当前合同与模拟结果解释，不能豁免。
- 需求下降时最低采购量使用 `locked-at-renewal` 固定 forecast：不能随新的情景需求按比例自动降低。
- notice / renewalLocked 依既有日期和通知记录条件计算；不能把原文中的条件续约条款当作无条件法律结论。
- 可行性、缺货阈值与现金上限由现有代码筛选，再按 TCO 与既有 tie-break 规则选择。无可行方案不给假推荐、不调用模型。
- AI 只能引用当前模拟/合同/来源；不执行或替代 Monte Carlo，不创设新供应商、费用减免、生产批准或人工签认。

## 证据类别

| 类别 | 可证明范围 | 不可宣称 |
| --- | --- | --- |
| 当前本地 reviewed Simulation | 当前源码安装后实际 MC + Trace + 门禁运行 | 模型、真人审批或线上新部署成功 |
| 当前离线故障注入 | 本地校验、失败处理与受测范围内拒绝行为 | 真实模型检出率、未见模型表现 |
| 主包本地真实 AI 历史响应 | 原包记载的当时一次网络工作流结果 | 本次修订代码重新真实调用或公开 AI 成功 |
| 历史 Verified Golden 回放 | 绑定历史材料的只读展示 | 新的实时模型调用/最新决策 |
| 示例 / TEST_FIXTURE_ONLY | 开发、接口测试或演示 | 真实审核、模型来源或正式 Golden |
| 正式未见评测 | 仅在独立未知输入/标签、提示配置评分冻结后真实执行并核查来源时成立 | 用看过标签的控制题/fixture 冒充未见 |

模型/提示/数据/源码/评分器版本通过评测冻结清单和全包 SHA-256 清单绑定。旧文件保留其当时状态，本次报告明确区分它们，不修改旧回答、旧评分或批准记录。
