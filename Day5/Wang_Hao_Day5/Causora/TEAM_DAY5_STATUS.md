# Causora Team Day5 Status

日期：2026-10-10（UTC+8）。本文件是 Wang 技术交付状态摘要，**不是新增团队批准或任何人的代签**。现有唯一真实用户是 Wang Hao。

## 一、工程与发布

- 唯一主工程：Deng Day5 包 `Causora`；交接所记部署基线 `4da7c5f8ed4939390b230e8de02bd513b11d96a8`。
- Ding Day5 为前端和历史验收参考；Hackathon 为 Day1–3 历史参考。均未整目录覆盖主工程。
- 本次 Wang 技术修订仅交付 ZIP，**未新部署**现有 Vercel/Render。
- 当前网站与 `/health` 在本次只读检查返回 HTTP 200。当前公开 AI 未启用；这不是公开完整 AI 成功测试。

## 二、各成员完成项

| 成员 | 原 Day5 主包/参考材料记载 | 本次 Wang 实际复核或完成 | 状态边界 |
| --- | --- | --- | --- |
| Deng Jinzhu | 当前模拟后端、approved reviewed Simulation v2、MC/Matrix/Formula Trace 与部署基线 | 未改原稿副本复现后端 **91 项测试、37 项子测试通过**；当前本地真实 HTTP reviewed 模拟、六项 source Evidence 与确定性复核；保留所有 release 绑定字节 | 记录来自交接及实际复核，不表示本次由 Deng 新签认 |
| Ding Xiangfeng | 前端、历史 Golden、证据定位和当前网页/验收参考 | 原前端 **57 项测试**、typecheck/lint 复现；逐差异保留当前主工程；Wang 增加取消/响应关联回归、静态/live 构建及本地生产服务验证 | 不把 Ding 历史待部署状态当当前公开状态，也不把 Wang 修订称 Ding 新交付 |
| Wang Hao | AI reliability / Critic / Brief / eval / 版本证据负责人 | 完整离线五阶段故障注入、数值/单位/证据/提示注入/异常/错配/无可行方案测试；修复已发现漏洞；旧评测审计；冻结及逐样本工具；完整工程/日志/清单/启动说明 | 本次模型请求 **0**；离线通过不是实际模型检出率；不制作新审核签名 |

## 三、Wang 本次实际修复

1. `percentage points` / `pp` / `ppt` 独立识别，拒绝作为概率 percent/fraction 声明。
2. Synthesizer 不再接收 option 的未信任 label/description。
3. 已取消 Boardroom/Evidence 请求不 fetch；成功响应关联到当前 outbound ID，而不是只比较两个旧字段。
4. 无可行方案在 import/provider 创建前输出 typed code-only Brief，零模型调用、零假推荐；保留约束列表。
5. 有效 EV 配上“无限/不中断供货保证、退出费豁免”等结论时，新增限定英文声明拒绝规则；原误接收样本完整保留，修复后重测。
6. 评测接口不依赖主工程已缺失的旧包模块；公平评分先统一字段、精度和陷阱 ID，不重写旧回答或旧成绩。
7. 原包 Windows `.cmd` 引用缺失脚本已补齐，并增加跨平台默认禁模型启动器；不创建或改换预算账本。

## 四、剩余团队项目（单列，不掩盖技术完成）

| 剩余项 | 当前状态 | 所需实际条件 |
| --- | --- | --- |
| 新真正未见 Critic 评测 | **未执行，N/A** | 新外部独立语料、真实人工标签、正式运行前冻结、新增调用授权 |
| 当前修订版真实完整 AI | **未执行**；仅保留主包当时一次本地真实响应 | 教师服务端密钥和独立预算授权，逐阶段实际记录 |
| 新正式三方案比较 | **未执行，N/A** | 相同新题/证据/答案结构/舍入/陷阱规则，无答案泄露及独立执行记录 |
| 公开实时 AI | **未启用** | 跨重启、跨 worker 可信持久预算台账，服务端密钥，真实公开五阶段验证 |
| 新修订上线 | **未部署** | 团队选择当前修订源并按既有流程部署，保持批准绑定与真实验收 |
| 真实用户观察 | **未完成** | 真实参与者本人使用与记录；不得虚构第二人 |
| Deng/Ding/Wang 最终团队签认 | **本次未新增** | 各本人确认；当前技术代理不得代签 |
| 原生 Windows 实机验收 | **未执行** | 安装 Python3.12/Node22 后在真实 Windows 执行脚本和回归 |

更多授权用途、最大调用数与费用硬上限提案见 `DAY5_EXTERNAL_REQUIREMENTS.md`。这些提案尚未执行或获得授权。

## 五、证据导航

- 最终实际结果：`DAY5_WANG_REPORT.md`。
- 当前测试原始日志：`verification/wang-day5/final-regression/` 与最终一键复测目录。
- 原始红灯/复测：`verification/wang-day5/ai/`、`logs/`、`ai/prior-semantic-failure/`。
- 逐样本与冻结：`verification/wang-day5/ai/final-offline-evaluation/`。
- 新模型 N/A 与离线计数分离：`verification/wang-day5/OFFLINE_AND_REAL_METRICS.json`。
- 原语料审计/旧比较缺陷：`verification/wang-day5/evaluation/`。
- 版本差异与选择性引入：`version_comparison.json`、`merge-and-change-record.json`。
- 当前包清单：`PACKAGE_FILE_LIST.csv`、`MANIFEST.sha256`。
