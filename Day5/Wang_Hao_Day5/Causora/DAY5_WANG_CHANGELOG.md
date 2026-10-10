# Wang Day5 逐项变更记录

## 唯一基线

Deng Day5 `Causora` 为唯一主工程；参考比较入口 `verification/wang-day5/version_comparison.json`（235 相同/16 不同/71 main-only/446 reference-only 是准备阶段文件范围，非最终包大小）。每个公共路径差异先保留主版本，未用 Ding/Hackathon 旧目录覆盖当前运行代码。

## 生产修复

| 路径 | 原因与修复 | 不改动的含义 |
| --- | --- | --- |
| `agent_day4/numeric.py` | 百分点独立识别，拒绝概率误标；integer/units 后缀单位与 registry 对齐 | 不降低数值守卫；不重算 MC；不改变公开字段 |
| `agent_day4/pipeline.py` | 不向 Synthesizer 转发自由 option label/description；共同文本校验调用目标 evidence support guard | 保持三角色独立→Critic→Brief 必需流程 |
| `agent_day4/evidence_support.py`（新增） | 拒绝当前来源不支持的供货保证和退出费豁免表达；只承诺已测英文限定模式 | 不是通用蕴含、法律意见或独立人工批准 |
| `agent_day4/eval_interface.py` | 替换缺失的旧 `agent_day3.evals.scoring` loader 依赖 | 不把旧开发/heldout 标签升为批准 |
| `backend/backend/app/boardroom_adapter.py` | no-feasible 在 provider import/factory 前零调用 typed 分支；约束列表 `_thaw` | 原 simulation/review/Trace 验证和注册先完成；不设假推荐 |
| `frontend/lib/boardroom-api.ts` | pre-aborted signal 零 fetch；成功 header/outbound/envelope identity 绑定 | 保留 active run 的 Matrix/Trace；不接受迟到结果 |
| `frontend/lib/evidence-api.ts` | pre-aborted signal 零 fetch；成功 header/envelope 均与本次 outbound 对齐 | EV ID 是否存在仍由 server 404 决定；不造新 DTO |
| `frontend/package.json` | 默认 npm test 纳入 Wang 新前端运行时回归 | 不遗漏原有57项 |
| `frontend/tests/day4-api.test.mjs` | 成功夹具按当前请求回显 ID，匹配加强后的正确关联 | 不放宽测试预期，不伪造实际网络 |

## 新增验证与工程可运行性

- `agents/wanghao-day3/tests_day5/`：离线完整流程、所有用户指定故障范围及金额/单位/时间/概率声明测试；明确 fixture 来源。
- 后端 Wang 生命周期/launcher safety tests，前端 Wang 迟到/取消/关联 tests。
- `scripts/start_day5.py` 与 Windows wrappers：原 `.cmd` 缺失 target script 复现为 false，补齐当前脚本；默认移除模型凭据和付费授权，不创建/重置/改换预算。
- `requirements-day5-tested.txt` 保存本次准确 Python 依赖；`test_day5.py` 一键复核；`verify_day5_local.py` 真实本地 HTTP；`package_day5.py` 完整 ZIP/hash/CRC/secret-pattern 检查；`verify_package.py` 当前清单复核。
- `evaluation/day5/`：统一答案 schema、输入/标签隔离、来源 registry、freeze、只含输入 dispatch、物理收据/输出封存、N/A 与失败保留。
- 前端 static/live build 从当前修订源码真实生成；包含可用构建产品而不打包依赖或 `.next` 缓存。

## 选择性历史恢复（非整目录合并）

1. Ding 原 `test_day4_budget_portability.py` → 新 `tests_day5/test_day5_budget_portability.py`，本地多进程锁与额度回归；未改预算 runtime。
2. Ding 原 `test_day4_openrouter.py` → 新 `tests_day5/test_day5_openrouter.py`，fake transport，无真实请求；仅适配当前 fixture 导入。
3. Ding 旧 dev/heldout input/labels/生成器/SHA 清单逐文件归档到 `evaluation/day5/historical/`，用于数量、重复、标签与暴露审计；不进入正式运行、未当新 heldout。
4. 原 Windows 参考脚本存在选择端口专属新预算路径的逻辑；**没有原样恢复**，当前重写为模拟专用启动器。

## 保留原字节

- 所有 `release/*`、`API_CONTRACT_V2.md`、Simulation v2 schema/Pydantic/TypeScript/validator 及其 dependency 文件。
- 已审核合成源数据、人工记录、政策记录及批准哈希。
- `verification/day5-current/` 29 个本地真实 AI/旧比较原始材料；没有改答案或改原评分。

## 失败与复测

原生缺脚本、注入转发、百分点、前端取消/关联以及 evidence false acceptance 的原始红灯都保留；新增测试 fixture 的 dataclass 构造错误也如实单列。最终数量和命令以 `DAY5_WANG_REPORT.md`、最终一键日志与包 SHA 清单为准，中间子报告不替代最终验收。
