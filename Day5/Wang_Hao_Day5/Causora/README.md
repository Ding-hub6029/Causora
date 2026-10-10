# Causora — Wang Hao Day5 完整技术交付

## 当前入口

- [本次实际完成与验证报告](DAY5_WANG_REPORT.md)
- [团队状态：Deng / Ding / Wang 分开记录](TEAM_DAY5_STATUS.md)
- [安装、启动、测试、复核](DAY5_RUNBOOK.md)
- [接口身份、单位、业务定义与证据范围](DAY5_DATA_AND_BUSINESS_CONTRACT.md)
- [唯一主工程的 Deng 原交接状态](DAY5_FINAL_STATUS.md)
- [Wang 原任务说明](WANG_HAO_DAY5_HANDOFF.md)

## 工程与线上版本

唯一主工程为 `Deng_Jinzhu_Day5.zip/Causora`。部署基线由该包交接记载为 `4da7c5f8ed4939390b230e8de02bd513b11d96a8`。Ding Day5 包与 Hackathon 历史包只作比较和选择性恢复测试的参考，不整目录覆盖当前程序。

现有公开网站：[causora-one.vercel.app](https://causora-one.vercel.app/)；现有模拟后端：[causora-api.onrender.com](https://causora-api.onrender.com)。本次没有重新部署这些服务。本次只读主页/health 检查与已有公开模拟记录不是公开完整 AI 流程测试。

公开实时 AI 未启用。主工程中已有的本地真实 AI 和三方案网络捕获保留为历史原始证据；**本次无新增模型请求、无密钥使用、无服务器购买**。离线 fixture 检验只证明本地防护和故障行为，不是真实模型检出率。

## 快速安装与启动

要求 Python 3.12、Node.js 22+：

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-day5-tested.txt
cd frontend && npm ci && npm run build:previews && cd ..
python scripts/start_day5.py --mode live
```

`http://127.0.0.1:3000/` 提供实时 reviewed 模拟与来源证据；此便捷启动器**禁用模型调用、不创建/切换预算台账**。历史回放用 `--mode static`。Windows 先运行 `SETUP_WINDOWS.cmd`，再运行 `START_LIVE.cmd` 或 `START_STATIC.cmd`。Windows 脚本本次未在原生 Windows 实机验证。

## 快速验证

```bash
python scripts/verify_package.py
python scripts/test_day5.py --build --local-http
```

测试结果写入新的系统临时目录，避免覆盖原始证据。详细分项命令见 [Runbook](DAY5_RUNBOOK.md)。评测工具在 `evaluation/day5`；逐样本离线记录、冻结哈希、原始失败与复测日志在 `verification/wang-day5`。

## 安全和发布边界

不改 Simulation v2、Boardroom v1 或 Formula Trace 的批准字段；不改 release/人工审核记录及原绑定哈希。AI 只解释当次 MC 结果；失败后 Matrix/Trace 保留。D1 保留 A 最低采购并增加 B；D2 退出 A 转向 B，不称多元化；需求下降不降低合同固定最低量。

后续真实未见评测需要单独授权与可信未知样本；公开 AI 需要持久预算和服务端密钥；真实参与者测试与团队本人签认未由本次代办。请勿把这些未完成项与已完成的技术回归混为一谈。

## 文件完整性

ZIP 含完整源码、源数据、既有批准文件、当前测试、验证材料、前端本次构建及安装说明；不含依赖目录、缓存、密钥、真实 `.env`。`MANIFEST.sha256` 与 `PACKAGE_FILE_LIST.csv` 是交付完整性清单，非批准记录。可用 `scripts/package_day5.py` 生成并校验 ZIP，详情见 Runbook。
