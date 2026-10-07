# RAG Pipeline 说明

RAG 部分只依赖结构化 `EngineeringCase`，不关心 Case 是手写的，还是由 LLM 从历史对话抽取出来的。

## Chunk 设计

每个 Case 会被切成三类 Chunk：

- `task`：这个 Case 解决的任务是什么。
- `constraint`：这个任务有哪些接口、工程、验证或回滚约束。
- `solution`：出现过的问题、根因、解决方式和可复用经验。

这种切法让 chunk 和 Case schema 保持一致。查询偏任务目标时容易命中 `task`，查询接口限制时容易命中 `constraint`，查询错误症状或修复经验时容易命中 `solution`。

## 向量化内容

检索时向量化的是每个 Chunk 的 `text`，不是整个 Case 文件。每条向量仍然保存 `case_id`、`chunk_id`、`chunk_type`、`module`、`final_status` 和 `source`，所以命中 Chunk 后可以回溯到完整 Case 和原始对话。

## Index

索引使用归一化向量和内积相似度。安装 `faiss-cpu` 时使用 FAISS；没有 FAISS 时使用 NumPy 兼容文件，方便本地测试。

默认真实 embedding provider 是：

```text
bge-m3 / BAAI/bge-m3
```

内部自动化测试使用确定性向量：

```text
mock
```

## Planner 输入

Prompt Builder 会把以下内容拼成 LLM 输入：

```text
当前任务
当前仓库事实
Top-K 检索结果
Algorithm Replacement Skill
当前允许修改的文件内容与可用工具
上一轮验证失败信息（若有）
```

Planner 输出结构化 JSON 计划和 actions。ProjectAdapter 实际执行后独立验证，
失败信息进入错误查询，再次检索、规划与执行；重试耗尽则恢复 checkpoint。
默认示例使用 DeepSeek 和 BGE-M3，完整快速开始见 README。
