# Contributing

欢迎基于这个项目补充新的 Case、文档、模型 provider 或检索能力。这个仓库的目标是保持“数据接口清楚、模型可替换、运行链路可复现”。

## 贡献方向

推荐从这些方向开始：

- 新增历史对话样例：放到 `examples/custom_data/raw/`。
- 新增结构化 Case：放到 `examples/custom_data/cases/`。
- 改进 Chunk 设计：修改 `algo_rag_demo/case_pipeline/chunker.py`。
- 增加检索或排序测试：放到 `tests/`。
- 增加 LLM provider：关注 `algo_rag_demo/agent/llm_provider.py`。
- 增加 embedding provider：关注 `algo_rag_demo/rag/embedding.py`。

## 本地验证

提交前建议运行：

```bash
python -m pytest -q
bash scripts/run_pipeline_offline.sh
```

如果改动了 BGE-M3 或 DeepSeek 集成，再运行：

```bash
bash scripts/run_pipeline_deepseek_bge.sh
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
