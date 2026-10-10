# Deng Jinzhu Day5 最终技术交付

日期：2026-10-10。公开部署源版本：4da7c5f8ed4939390b230e8de02bd513b11d96a8。本包在该版本上补齐数值测试、独立校验、性能测试及交接材料，未重新部署测试目录。

网站：https://causora-one.vercel.app/
模拟 API：https://causora-api.onrender.com

## 已完成并可复核

- 免费 Vercel 前端与 Render 模拟后端上线。真实 Matrix、Formula Trace、三场景模拟通过；公开模拟重复请求 10/10 HTTP 200。
- 修复免费后端冷启动时过早禁用模拟按钮的问题。Wang Hao 已最终确认修复版 Baseline 与 Demand -15% 的实时模拟复测成功。
- 正式 reviewed 配置的本地 AI Boardroom 实际完成：5 次模型调用，HTTP 200，数值守卫通过，推荐 D1；费用 0.014141 美元。
- 普通 LLM、LLM 加代码两方案实际执行完成，代码实际运行；费用 0.0244975 美元。比较报告披露旧评分器字段结构偏差，不能将对象匹配 0/6 当作数学准确率。
- 独立算术控制题 6/6 通过。最终包后端 91 项测试、37 项子测试通过，包含数值、来源、确定性、接口、篡改拒绝及部署检查。
- 前端修复版本此前验证：57 项测试通过，类型与静态检查通过；线上构建及浏览器真实模拟成功。
- 本机引擎性能实测：1,000 次 0.108269 秒，10,000 次 0.489898 秒。这是未审核合成引擎性能测试，不包含网络、AI、公开服务延迟；Windows 内存峰值不可用，不填造数值。
- 交付源代码、冻结控制题、评分器、原始模型捕获、实际代码输出、部署证据、真实用户确认记录及文件哈希清单。

## 边界与团队后续

Deng 的本次技术交付可交接给 Wang。团队完整 G5 仍不能标为全部通过：现有真实用户只有 Wang Hao 一人；原计划 2–3 人、独立人工 oracle 审查、团队签认及十次公开完整 AI 流程未完成。公开 AI 尚未配置，免费 Render 没有现有预算台账设计要求的持久存储；网站提供真实模拟与清楚标明的历史只读 Golden 回放。本地 AI 成功不能冒充公开 AI 成功。

Wang 的 held-out/negative Critic 验证与公平评测后续见 WANG_HAO_DAY5_HANDOFF.md。未新增模型调用、未购买服务器、未生成他人签名。

## 复核入口

- verification/day5-final-backend-tests.txt：当前测试原始日志。
- verification/day5-performance-1000.json 与 day5-performance-10000.json：当前性能与输入、源码哈希。
- verification/day5-current/：公开 API、截图、本地正式 AI 响应、三方案比较与 Wang 最终确认。
- evaluation/oracle 与 evaluation/benchmark：可重复离线校验工具。
- deployment/render_start.py --validate-only：正式发布门禁检查。
- scripts/verify_package.py：逐文件哈希完整性检查。

历史 G4/G5 工具输出留作历史证据，当前事实以本页及 day5-current 材料为准。
