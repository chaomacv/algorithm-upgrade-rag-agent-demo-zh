# Contributing

欢迎基于这个项目补充新的 Case、Demo 场景、文档或执行器能力。这个仓库的目标是保持“能讲清楚、能跑通、能复用”。

## 贡献方向

推荐从这些方向开始：

- 新增历史对话样例：放到 `examples/data/raw/`。
- 新增结构化 Case：放到 `examples/data/cases/`。
- 改进 Chunk 设计：修改 `algo_rag_demo/case_pipeline/chunker.py`。
- 增加检索或排序测试：放到 `tests/`。
- 增加新的教学场景：放到 `algo_rag_demo/demo_scenarios/`。
- 改进执行和验证逻辑：关注 `algo_rag_demo/agent/executor.py` 和 `algo_rag_demo/agent/tool_registry.py`。

## 本地验证

提交前建议运行：

```bash
python -m pytest -q
bash scripts/run_teaching_demo.sh
```

如果改动了 BGE-M3 或 DeepSeek 集成，再运行：

```bash
bash scripts/run_live_demo.sh
```

## 数据要求

请只提交合成数据或已经脱敏的数据。不要提交：

- API key
- 密码
- 公司内部日志
- 客户数据
- 未脱敏的真实工程对话
- 模型缓存和向量索引产物

`password.txt`、`outputs/`、`.venv/` 和索引产物已经在 `.gitignore` 中排除。

## 文档风格

中文说明优先保持清晰、短句、可操作。README 只放入口和导航，详细解释放到 `docs/`。
