# 复用架构说明

这个项目面向两类读者：

1. 想快速理解 RAG + Agent 闭环的人。
2. 想把代码改造成自己工程模板的人。

因此项目把“教学剧情”和“可复用组件”分开。

## 分层流程

```text
examples/data/raw
-> case_pipeline
-> examples/data/cases
-> chunker
-> examples/data/knowledge/chunks.json
-> embedding
-> index
-> retriever
-> planner
-> executor
-> tool registry
-> runs
```

## 教学专属层

`algo_rag_demo/demo_scenarios/dre_failure_recovery.py` 负责固定剧情：

- 模拟用户任务。
- 第一次故意做不安全的直接替换。
- 生成错误检索 query。
- 记录两阶段运行产物。
- 生成最终报告。

这个文件适合讲解和演示，不是读者复用时最先复制的部分。

## 可复用组件

`algo_rag_demo/case_pipeline/`

负责把原始对话转换成结构化 `EngineeringCase`，再切成和 Schema 对齐的 Chunk。

`algo_rag_demo/rag/`

负责 embedding、向量索引构建、Top-K 检索。

`algo_rag_demo/agent/planner.py`

定义规划器：

- `MockPlanner`：离线、确定性规划器。
- `LLMPlanner`：可接入 DeepSeek 的 LLM 规划器。

Planner 输出既包含可读计划，也包含 `executable_plan.steps`。

`algo_rag_demo/agent/executor.py`

定义 `PlanExecutor`，负责通过安全工具执行结构化步骤。支持：

- `inspect`
- `search`
- `patch`
- `backup` / `checkpoint`
- `validate`

Executor 不允许 LLM 任意写文件。Patch 步骤会被当成意图，再映射到已知的安全修改模板。

`algo_rag_demo/agent/tool_registry.py`

提供受控工具：

- 在示例工程内读写文件。
- 代码搜索。
- 构建检查。
- 接口检查。
- 运行时检查。
- 算法切换检查。
- checkpoint。
- rollback。

这是 LLM 规划和真实系统修改之间最重要的边界。

## 如何改造成自己的项目

可以按下面顺序改：

1. 用你的目标项目替换 `examples/demo_project/`。
2. 修改 `ToolRegistry` 里的验证方法，让它执行你的测试命令。
3. 修改 `PlanExecutor._apply_safe_patch()`，把 patch 意图映射到你的安全编辑操作。
4. 把自己的历史对话放到 `examples/data/raw/`。
5. 抽取结构化 Case 到 `examples/data/cases/`。
6. 重新构建索引。

建议保持 scenario 层独立。新的演示剧情可以放到：

```text
algo_rag_demo/demo_scenarios/
```

如果要做更接近生产的使用方式，可以直接调用 `case_pipeline`、`rag`、`planner`、`executor`，不依赖固定的 DRE 教学剧情。

## 为什么要这样拆

教学 Demo 需要叙事：

```text
第一次失败
-> 根据错误再次检索
-> 修复成功
```

可复用代码需要边界：

```text
planner 产生步骤
executor 解释步骤
tool registry 限制能力
validation 决定成功与否
```

把这两件事分开，项目就更容易讲，也更容易改。
