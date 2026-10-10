# Wang Hao Day 5 离线可靠性测试

**运行边界：全部为 `TEST_FIXTURE_ONLY`。** 本目录的 provider 是内存中的确定性响应，测试运行前应清空 `OPENAI_API_KEY`、`OPENAI_API_BASE`、`OPENAI_BASE_URL` 与 `OPENROUTER_API_KEY`。不得将结果描述为真实模型调用、真实模型检出率或人工审批。

## 参考包的逐文件比较与选择性引入

主工程在开始时没有 `agents/wanghao-day3/tests/`，而参考工程有完整 Day 4 回归包。实现模块 `pipeline.py`、`numeric.py`、`business.py`、`allocation.py`、`evidence.py`、`inputs.py`、`wire.py` 除 provider 文案外与参考工程一致；因此没有整目录覆盖。只将下列回归意图以更窄的本目录 fixture 重写：

| 参考文件 | 本目录覆盖 | 选择理由 |
| --- | --- | --- |
| `tests/day4_fixtures.py` | `day5_fixtures.py` | 仅保留构造 reviewed fixture、内存 provider、选择重算；不导入历史项目。 |
| `tests/test_day4_pipeline.py` | `test_day5_pipeline_reliability.py` | 完整五阶段 fixture 流程、缺失/超时/畸形 Critic fallback、身份与 no-feasible。 |
| `tests/test_day4_numeric.py` | `test_day5_pipeline_reliability.py` | 数字绑定、百分比与百分点单位篡改。 |
| `tests/test_day4_business.py`、`tests/test_day4_concentration.py` | `test_day5_pipeline_reliability.py` | D1 最低固定 A 的混合采购，以及 D2 B-only 不等于多元化。 |
| `tests/test_day4_inputs.py` | `test_day5_pipeline_reliability.py` | MC Matrix/Trace 不变、源证据/合同注入拒绝和模型载荷隔离。 |
| `tests/test_day4_real_failure_regressions.py` | `test_day5_pipeline_reliability.py` | JSON 缺字段/非对象和安全失败不发布简报。 |
| `tests/test_day4_budget_portability.py` | `test_day5_budget_portability.py` | 父代理要求的逐文件引入；仅本地 journal、portalocker、spawn/thread 测试，无 HTTP；没有修改预算 runtime。 |
| `tests/test_day4_openrouter.py` | `test_day5_openrouter.py` | 父代理要求的逐文件引入；`/models`、`/key`、completion 都是内存 fake，仅将窄 fixture 导入改到本目录。 |

未复制其余依赖 live/provider 配置或历史路径的测试；这符合本 Day 5 任务禁止真实模型、密钥和网络调用的约束。

## 运行

```bash
cd /home/ubuntu/causora_day5/main/Causora/agents/wanghao-day3
unset OPENAI_API_KEY OPENAI_API_BASE OPENAI_BASE_URL OPENROUTER_API_KEY
/home/ubuntu/causora_day5/.venv/bin/python -m pytest tests_day5 -q -p no:cacheprovider
```

`run_offline_ai_evaluation.py` 另产生逐样本 JSONL 与汇总；其中 `semantic_false_acceptance` 是已知、明确标记的未解决局限，而不是通过的安全检出率。
