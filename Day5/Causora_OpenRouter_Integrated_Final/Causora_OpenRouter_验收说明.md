# Causora 公开 OpenRouter 接入与验收说明

网站完整链接：https://causora-one.vercel.app/
后端：https://causora-api.onrender.com
源码提交：3f8e0ce8326fd25a586c171fc9743368be596a43
验收日期：2026-10-10（北京时间）

## 已完成的接入

老师提供的 OpenRouter 密钥已经配置在 Render 后台环境变量中。浏览器通过 Causora 后端调用模型，前端源码、公开文件和本交付包不包含密钥。Vercel 最新部署 Ready，Render 最新提交 Live。

真实流程为：证据与场景输入 → 代码执行 1,000 次 Monte Carlo / 104 周模拟 → CFO、COO、Risk 三个模型视角 → Critic 质询 → Synthesizer 简报 → 人工选择。数值由模拟代码计算，模型生成定性评审，再经过数字与证据约束校验。系统有预设结构和约束，并非无约束聊天；本次已核实真实模型请求、返回内容及计费凭据，不能据此声称看到了模型内部思考过程。

## 两轮公开网站真实调用

| 项目 | Baseline | Demand −15% |
|---|---|---|
| Simulation request | req-54e9b2e0aa9146b28d05506eb006126b | req-9c1c0a56a2314f2fad760f92585a98c4 |
| Boardroom request | causora-br-7f850a6e-3a85-4125-b351-671d0f40e677 | causora-br-90bdd085-7ada-4b13-9564-efed1e75a0bd |
| Provider mode | primary，五阶段完整 | primary，五阶段完整 |
| 数字校验 | passed，0 rejected claims | passed，0 rejected claims |
| D1 TCO / P90 | $348,040 / $348,723 | $358,161 / $358,829 |

两轮共 10 次真实模型调用，核实费用 USD 0.02684325。模型包括 openai/gpt-5-mini 和 google/gemini-3.1-pro-preview。每次调用的返回模型、生成 ID、token 用量、成本及输出摘要哈希保存在 provider-receipts.json。两轮评审内容随场景变化：基准场景讨论混合采购与保留承诺，需求下降场景质询固定最低采购导致的库存及持有成本风险。

本轮授权上限为 30 次模型调用 / USD 1，目前剩余 20 次模型调用，通常可完成约 4 轮五阶段评审。这是本网站授权预算，不是老师账户的实际总余额。预算保存在 PostgreSQL，最新重新部署后依然保留 10 条记录；并发预留和超额阻止已做隔离测试，未额外调用模型。

## 按钮与跳转验收范围

浏览器测试记录共 50 条（含重复场景与复测），保存在 button-checks.json。一个早期指标标签检查在页面切换时返回 false，等待新内容显示后的复测确认正确；原始检查记录保留。

- 五步导航、返回输入、下一步、比较预设值、修改假设、重置。
- 三种场景切换、风险/现金输入、九个矩阵单元及选项展示。
- 真实 Run simulation、Run Boardroom、匹配简报、Approve/Reject。
- 五条证据入口、PDF 第 4 页、公式追踪、104 周展开与周详情、关闭弹窗与 Escape。
- 财务/运营/合同评审卡片展开收起、质询证据、证据栈入口。
- 示例状态 loading / empty / error / no feasible 与恢复；保存示例的审批禁用。
- 校验缓存加载、只读矩阵和 Boardroom、匹配简报、JSON 导出、退出到场景及重置。
- 六个公开数据/PDF/Golden 文件链接均 HTTP 200。

已修复并上线：只读缓存的 Run simulation 按钮明确禁用；质询中的 2,340 单位标签改为“A floor above rolling benchmark”，避免误解为超过总需求的库存量。

本次浏览器验收为桌面主要流程。失败后才出现的 Retry 按钮没有通过刻意制造线上故障逐个触发；相应取消、超时、错误与请求绑定行为由自动化检查覆盖。不能将本验收解释为所有设备、全部输入组合和未来服务状态的无限保证。

## 代码检查

Wang Day5 包审计：后端/AI/评估 207 passed + 37 subtests；前端 62 tests、类型检查和 lint 通过。公开持久预算新增单元检查及数据库并发隔离测试通过。最新两个 UI 修正后再次通过前端 62 tests、类型检查和 lint。本包 MANIFEST.sha256 所列 267 个文件逐项匹配。

Approve/Reject 的浏览器操作是按钮验收，不是实际业务决策或供应商操作；保存缓存中的测试选择也明确标注 automated test artifact。

## 录屏顺序与使用限制

1. 打开网站，等待“Simulation service reachable”。免费 Render 闲置后启动可能需要 50 秒或更久。
2. 进入 Scenario Lab，选 Baseline，进入 Decision Matrix，点击 Run simulation。
3. 打开 live Boardroom，点击 Run Boardroom，等待三视角、Critic、数字校验和匹配简报。
4. 展示证据 PDF、公式追踪，再展示人工决策按钮。真实业务选择由团队自行决定。
5. 如展示不同场景，修改假设后重新模拟和评审，不能把旧评审当成新场景回答。

录屏要展示 LIVE / primary 与本次请求信息；“Open saved example”和“Verified cache”是明确标注的示例/只读回放，不会新增 AI 调用。

免费 PostgreSQL 到期日为 2026-11-09；当前足够本次比赛。到期或预算用尽后真实 AI 会被阻止，不能把失败伪装成成功。更换电脑或解压源码不会自动带入服务器环境变量，公开网站已配置完成。

## 交付包内容

Causora/：与公开部署提交一致的项目源码和原始 manifest。
Evidence/：本次真实 AI 截图、页面文字、10 次调用收据、按钮检查和公开链接检查。
本说明：事实、复现步骤及使用限制。未附带私密数据库 URL、API 密钥、虚拟环境或 node_modules。
