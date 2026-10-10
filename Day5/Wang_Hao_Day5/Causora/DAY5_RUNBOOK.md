# Causora Day5 安装、启动、测试与复核

本交付以 Deng Day5 `Causora` 为唯一主工程。本次源码修订**未重新部署公开网站**。默认启动只提供 reviewed Simulation + Evidence 或历史只读回放，公开实时 AI 没有启用。

## 1. 环境

- Python **3.12**：本次实际 Python 3.12.3。当前 NumPy 固定 2.5.3，沿用模拟数值基线。
- Node.js **22+**：实际 Node 22.13.0、npm 10.9.2。
- 当前依赖精确版本：`requirements-day5-tested.txt`；前端：`frontend/package-lock.json`。
- ZIP 不含 `.venv`、`node_modules`、`.next`、真实 `.env`、密钥或其他运行缓存。
- `frontend/builds/live` / `static` 是本次源码构建产品，可直接用于预览；修改源码后必须重建。

## 2. Linux/macOS 安装

在解压后的 **Causora 根目录**执行：

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-day5-tested.txt
cd frontend
npm ci
npm run build:previews
cd ..
```

如果使用原工程宽范围依赖，则 `pip install -r backend/backend/requirements.txt` 也可用，但版本漂移应重新验证，不能宣称与本次测试环境相同。

## 3. Windows 安装

先安装 Python 3.12、Node.js 22，并确认 `python`、`node`、`npm.cmd` 在 PATH。双击 `SETUP_WINDOWS.cmd`，或：

```powershell
powershell -NoProfile -File scripts/setup-windows.ps1
```

脚本在根目录创建 `.venv`，安装 Python 与前端依赖，构建当前源码。**本次实际验收在 Linux，未执行原生 Windows；不把跨平台设计或 spawn 测试写成 Windows 实测。**

## 4. 本地启动（推荐，默认禁止模型调用）

```bash
# .venv 已激活
python scripts/start_day5.py --mode live
# 访问 http://127.0.0.1:3000/
```

Windows：`START_LIVE.cmd`；历史只读回放：`START_STATIC.cmd` 或：

```bash
python scripts/start_day5.py --mode static
```

可用 `--backend-port 8001 --frontend-port 3001` 指定两个不同端口。端口被占用时拒绝启动，不会杀掉其他应用。Ctrl+C 只停止本启动器创建的子进程。

本地启动器不继承模型密钥和付费授权，不创建、重置、切换或删除预算台账。`live` 在这里指**实时模拟**，不是实时模型。AI 按钮若发起请求，会得到明确的未配置失败，不能绕过校验获取简报。

## 5. 分别启动 reviewed 模拟后端与前端

```bash
# 根目录，默认生产入口强制 openrouter，不使用 Manus 代理
HOST=0.0.0.0 PORT=8000 python deployment/render_start.py
```

另一个终端：

```bash
cd frontend
CAUSORA_BACKEND_URL=http://127.0.0.1:8000 HOST=127.0.0.1 PORT=3000 npm run start:live
```

已有 release 和审核材料随包保留，启动时验证其原绑定；任何审核/政策门禁失败均应修正来源或重新获得有效审批，**不要编辑状态与哈希来制造通过**。

## 6. 一键测试

```bash
python scripts/test_day5.py --build --local-http
```

默认写入系统临时目录并打印位置，不覆盖 ZIP 内原始证据；也可以 `--output /一个全新空目录`。所有测试进程移除模型密钥与付费授权。本地 HTTP 测试启动并停止自己创建的服务，检查 Simulation、六个原文证据、未配置 AI 的 503 和 Matrix/Trace 确定性。

分项命令：

```bash
cd backend/backend
python -m pytest tests simulation_day1/tests simulation_day2/tests simulation_day3/tests -q -p no:cacheprovider
cd ../..
python deployment/render_start.py --validate-only
cd agents/wanghao-day3
python -m pytest tests_day5 -q -p no:cacheprovider
cd ../..
python -m pytest evaluation/day5/tests -q -p no:cacheprovider
cd frontend
npm test
npm run typecheck
npm run lint
npm run build:previews
npm run test:production
cd ..
python scripts/verify_day5_local.py --output /一个新的本地HTTP日志目录
```

选择性恢复的历史 AI 回归在 `agents/wanghao-day3/tests` 时也可运行 `python -m pytest tests -q -p no:cacheprovider`；复现具体范围以 `DAY5_WANG_REPORT.md` 和日志为准。pytest 通过数量不是真实模型检出率。

## 7. 评测与公平比较

先阅读 `evaluation/day5/README.md` 与 `evaluation/day5/WORK_SUMMARY.md`。新评测工具冻结输入、标签、提示、模型配置、评分和源码哈希，生成只含输入的 dispatch，导入真实捕获后严格逐条评分；它**不会偷偷调用任何模型**。

- 已看过/调试过/不能证明未见的历史集，不可再声称公平未见。
- 不向模型发送标签、期望答案或陷阱答案；统一答案结构和陷阱 ID 词表属于公开评分接口，预期哪些 ID 被命中属于隐藏标签。
- 本次真实新模型调用为零，因此当前真实 Critic 指标没有新分母，写 **N/A**；逐样本离线结果仅证明本地拒绝/失败处理。
- 旧三方案原始回答和对象匹配评分仍在 `verification/day5-current`，未修饰成新正式分数。

## 8. 完整性与重打包

```bash
python scripts/verify_package.py
python scripts/package_day5.py --output ../Wang_Hao_Day5_Final.zip
```

`MANIFEST.sha256` 列全部交付文件（不列自身）；`PACKAGE_FILE_LIST.csv` 列 payload 大小和哈希（不列自身与 MANIFEST），避免递归哈希。打包器检查密钥形式、ZIP CRC 和每个文件字节一致性，生成包外 `.integrity.json` 与 `.sha256` 收据。

重新运行测试会产生日志/缓存；若需更新交付，应先重新冻结并测试，再重新生成完整性清单。交付清单哈希更新不是批准记录重签。

## 9. 需要单独完成的外部事项

真实新模型评测必须先确定独立未见输入/标签、最大调用数、费用上限及新授权；既往授权已经用完，历史文件里写着授权不构成本次授权。公开 AI 还需可持久保存、跨进程一致且不可重置的预算台账和服务端密钥。另需真实参与者测试与本人团队签认；不在本次技术交付中伪造这些记录。
