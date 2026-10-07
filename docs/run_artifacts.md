# 运行产物说明

每次 demo 会在 `outputs/runs/<timestamp>/` 下写入结果。

## 主要文件

```text
task.json
initial_retrieval.json
initial_plan.json
initial_execution.json
retrieval.json
plan.json
repair_execution.json
validation.json
final_report.json
```

## 怎么看

- `task.json`：本次模拟用户任务。
- `initial_retrieval.json`：第一次基于任务本身的 RAG 检索。
- `initial_plan.json`：第一次计划。
- `initial_execution.json`：第一次执行结果，教学版会故意失败。
- `retrieval.json`：基于具体错误信息的二次检索。
- `plan.json`：修复计划。
- `repair_execution.json`：修复执行步骤和工具调用。
- `validation.json`：接口、构建、运行、算法切换、回滚验证。
- `final_report.json`：最终成功或失败摘要。

## 5 分钟展示路线

1. 打开 `examples/data/raw/conversation_dre_upgrade.json`，说明历史对话不是直接拿来检索。
2. 打开 `examples/data/cases/CASE_DRE_001.json`，说明对话会变成结构化 Case。
3. 打开 `examples/data/knowledge/chunks.json`，说明 Chunk 与 Case Schema 对齐。
4. 运行 `python -m algo_rag_demo.cli search "Replace DRE while keeping downstream interface compatible"`。
5. 运行 `python -m algo_rag_demo.cli demo-failure`。
6. 打开最新的 `outputs/runs/.../final_report.json`，展示接口、构建、运行、算法切换和回滚验证。
