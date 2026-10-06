# Teaching Demo：低门槛讲解版

这是项目中最容易跑通的一条路径。它用来讲清楚完整的 RAG + Planner + Executor 闭环，不需要 API key、网络或模型下载。

## 运行方式

```bash
cd algorithm-upgrade-rag-agent-demo-zh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-lite.txt
bash scripts/run_teaching_demo.sh
```

脚本会使用：

- `MockEmbeddingProvider`
- `MockPlanner`
- `PlanExecutor`

所以结果是确定的，适合课堂、汇报或面试讲解。

## 它展示什么

```text
历史 Case
-> Schema 对齐的 Chunk
-> Mock 向量索引
-> 基于任务的第一次检索
-> 第一次执行失败
-> 基于错误信息的第二次检索
-> 修复计划
-> 受控 Executor 执行
-> Validation 验证
-> Final Report
```

教学场景是固定的。模拟用户任务是：

```text
Replace OldDRE with NewLLF while keeping downstream interface compatible
```

第一次执行会故意做“直接替换”，因此失败。原因是 `NewLLF` 没有返回 `residual_map`，但下游模块仍然需要这个字段。

第二次检索使用具体错误：

```text
DRE interface validation failed 'residual_map' residual_map NewLLF
```

这样会命中历史案例中关于“需要兼容适配层”的经验。

## 相关代码位置

- `scripts/run_teaching_demo.sh`：一键运行入口。
- `algo_rag_demo/demo_scenarios/dre_failure_recovery.py`：固定教学剧情。
- `algo_rag_demo/agent/executor.py`：可复用的受控执行器。
- `algo_rag_demo/agent/tool_registry.py`：安全工具、验证、checkpoint、rollback。
- `algo_rag_demo/rag/retriever.py`：Chunk 检索。

## 运行后看哪些文件

运行完成后，打开最新的 `outputs/runs/` 子目录：

- `initial_retrieval.json`：基于任务文本的第一次检索。
- `initial_execution.json`：第一次执行失败，缺少 `residual_map`。
- `retrieval.json`：基于失败错误的第二次检索。
- `plan.json`：修复计划。
- `repair_execution.json`：修复执行步骤和工具调用。
- `final_report.json`：最终成功或失败摘要。

这条路径最适合第一次理解项目，因为它避开了 DeepSeek、BGE-M3、网络和依赖环境问题。
