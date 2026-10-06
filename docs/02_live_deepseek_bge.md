# Live DeepSeek + BGE-M3 Demo：真实集成版

这个模式保留同一个教学场景，但把 Mock 组件替换成真实集成：

- `BgeM3EmbeddingProvider`：生成真实语义向量。
- `LLMPlanner` + DeepSeek：根据 RAG 证据生成计划。

建议先跑通 Teaching Demo，再尝试这个版本。

## 依赖要求

你需要：

- 可安装 BGE-M3 依赖的 Python 环境。
- DeepSeek 环境变量。
- 能访问 DeepSeek API 的网络。
- Hugging Face 模型文件可下载或已经缓存。

本地可以创建 `password.txt` 保存 DeepSeek 环境变量。这个文件已经被 `.gitignore` 排除，不应该提交到 GitHub。`load_deepseek_env.sh` 会读取它。

## 运行方式

```bash
cd algorithm-upgrade-rag-agent-demo-zh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/run_live_demo.sh
```

脚本内部会运行：

```bash
python -m pytest -q
python -m algo_rag_demo.cli build-index --provider bge-m3
python -m algo_rag_demo.cli demo-failure --provider bge-m3 --planner deepseek
```

## 关键注意点

向量索引必须和 embedding provider 匹配。

如果 `outputs/index/cases.index` 是用 `mock` 构建的，它是 64 维；而 BGE-M3 查询向量是 1024 维。用 BGE-M3 查询 mock index 会触发 FAISS 维度错误。

所以 live 脚本每次都会重新构建 BGE-M3 索引：

```bash
python -m algo_rag_demo.cli build-index --provider bge-m3
```

## 哪些结果可能变化

这个模式更接近真实使用，但不完全确定：

- DeepSeek 生成的计划措辞可能不同。
- 第一次加载模型可能更慢。
- 网络和 API 状态会影响运行。
- BGE-M3 的检索分数和 mock 检索分数不同。

`PlanExecutor` 会把 LLM 输出当作意图，而不是直接让 LLM 任意改文件。真正执行时会映射到安全模板和受控工具。

## 预期结果

成功运行时结尾应该看到：

```text
Final Result
SUCCESS
```

最终报告大致包含：

```json
{
  "status": "success",
  "validation": {
    "build": "passed",
    "interface": "passed",
    "runtime": "passed",
    "algorithm_switch": "passed",
    "rollback": "passed"
  }
}
```

DeepSeek 可能会额外生成 `residual_map`、`tests`、`rollback_readiness` 等验证项，Executor 会把它们映射到最接近的内置验证。
