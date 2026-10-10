# Causora Day5 实际测试结果

公开网站：https://causora-one.vercel.app/

公开模拟服务：https://causora-api.onrender.com/

2026-10-10，本地使用正式 reviewed release 配置，经实际 OpenRouter 网络调用完成 Baseline AI Boardroom。没有使用模拟模型或放宽校验。

- 模拟接口：HTTP 200。
- AI Boardroom 接口：HTTP 200。
- 三角色评审、Critic、最终简报：完整返回，共五次模型调用。
- OpenRouter 返回的实际总费用：0.014141 美元。
- 数值校验：passed=true，rejectedClaims=[]。
- 最终推荐：D1，保留供应商 A 的最低采购承诺，同时引入供应商 B。
- 新一轮授权上限：六次调用、一美元。使用五次后停止。

公开网站的模拟与公式追溯已经验证。AI 成功结果来自本地测试，公开 Render 服务未配置密钥，也未接通公开 AI。此前 Mac 上的失败本轮没有复现，不能据此断言其原始原因已经找到。尚未完成真实用户测试或比赛最终验收。

完整 AI 响应保存在同一工作区的 private-day5-ai-round2/response.json；费用记录保存在 private-day5-ai-round2/budget.json。密钥没有写入这些交付说明或公开代码。
