# Wang Hao Day5 接续材料

Deng 的最终源代码与模拟部署已交接，先从 DAY5_FINAL_STATUS.md 了解当前事实，无需重做部署或改写数值。

网站：https://causora-one.vercel.app/
后端：https://causora-api.onrender.com
部署源版本：4da7c5f8ed4939390b230e8de02bd513b11d96a8。

## Wang 的工作范围

1. 对现有 CFO、COO、Risk → Critic → Brief 流程做未见样本及负例评估。覆盖数字篡改、错误 evidence ID、缺失 Critic、超时、格式错误、场景或 simulation ID 不匹配；记录是否拒绝及原因。不得用本包冻结控制题冒充 held-out。
2. 记录 Critic 检出率 TP/(TP+FN)、误报率 FP/(FP+TN)、数字忠实率、证据有效率及完整流程成功率，保留每条样本标签与输出。先跑本地离线测试，新的真实模型调用需要单独预算；此前授权轮次已执行，不自行追加。
3. 复核三方案报告。旧提示未统一答案字段与陷阱标识符，因此旧严格匹配分数不能证明模型数学准确率。先冻结统一输出结构和新的未见题，再做后续公平测量；不要修饰旧捕获答案。
4. 如团队要求公开实时 AI，先确定现有预算台账如何持久保存，再配置服务端密钥与批准开关。当前免费公开服务只启用模拟，老师密钥不在本包，也不要放前端或 Git。
5. 保存真实评测结果与团队确认；未完成的 2–3 人用户测试、十次公开完整 AI 流程及人工审核保留真实状态，不替签。

## 现成证据

verification/day5-current/local-reviewed-boardroom-response.json 是本地真实正式 AI 的成功响应；AI-测试结果.md 解释调用和验证。WangHao-最终确认的测试记录.md 是本人提交的最终确认。benchmark_actual_comparison.json、两种 capture 与 comparison-model-generated-calculation.py / comparison-code-execution.log 可复核实际比较。

## 本地入口

先按 README.md 安装依赖。后端目录 backend/backend：

```text
python -m pytest tests simulation_day1/tests simulation_day2/tests simulation_day3/tests -q -p no:cacheprovider
```

当前交付包该组通过 91 项测试与 37 项子测试。独立 oracle 与 benchmark 的说明在 evaluation 对应 README；AI 管线源代码在 agents/wanghao-day3/agent_day4，接口在 backend/backend/app/boardroom_adapter.py。不要降低数值守卫或审核门禁来换取成功。
