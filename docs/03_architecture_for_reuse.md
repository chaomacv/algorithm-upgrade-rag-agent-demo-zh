# 自定义实战入口

这一页替代原来的“复用架构”说明，重点回答一个问题：

```text
别人能不能把自己的数据放进来，然后直接跑通一条完整链路？
```

现在可以。入口是：

```bash
bash scripts/run_custom_demo.sh
```

或者直接使用 CLI：

```bash
python -m algo_rag_demo.cli run-custom \
  --case-dir examples/custom_data/cases \
  --task-file examples/custom_data/task.txt \
  --repository-facts examples/custom_data/repository_facts.txt \
  --provider mock \
  --planner evidence \
  --top-k 3
```

## 它会跑哪些步骤

`run-custom` 跑的是通用实战链路：

```text
用户 Case
-> Schema 对齐的 Chunk
-> Chunk Text Embedding
-> Run-local Vector Index
-> Query Retrieval
-> Prompt Builder
-> Evidence Planner
-> Prompt / Plan / Report
```

它默认是 `custom_dry_run`，也就是只生成检索证据、提示词、计划和报告，不直接修改用户项目。

这个设计是刻意的：不同真实项目的文件结构、测试命令、patch 策略都不一样。如果直接复用 DRE 教学 Demo 的 Executor，反而容易误导读者，以为通用入口会安全地修改任意工程。

## 最小数据结构

你可以参考：

```text
examples/custom_data/
  README.md
  task.txt
  repository_facts.txt
  cases/
    CASE_CUSTOM_001.json
```

其中最关键的是：

- `task.txt`：当前要解决的问题。
- `repository_facts.txt`：当前项目的事实说明，可选但推荐。
- `cases/CASE_*.json`：历史经验 Case。

## Case 文件格式

每个 `CASE_*.json` 都应该符合 `EngineeringCase`：

```json
{
  "case_id": "CASE_CUSTOM_001",
  "module": "Ranking",
  "task": "Replace legacy ranking module with a new scoring module",
  "old_algorithm": "LegacyRanker",
  "new_algorithm": "NeuralScorer",
  "constraints": {
    "interface": ["Keep downstream metadata schema stable"],
    "engineering": ["Keep rollback path available"]
  },
  "steps": ["Inspect interface", "Patch adapter", "Run validation"],
  "problems": [
    {
      "stage": "first replacement",
      "symptom": "metadata.reason is missing",
      "root_cause": "The new scorer returned a different metadata shape"
    }
  ],
  "solutions": [
    {
      "problem": "metadata schema mismatch",
      "solution": "Add an adapter that preserves the metadata contract"
    }
  ],
  "validation": {
    "interface": "passed",
    "runtime": "passed",
    "rollback": "passed"
  },
  "final_status": "success",
  "reusable_experience": [
    "Treat metadata schema compatibility as part of the public interface"
  ],
  "source_conversation_id": "CONV_CUSTOM_001"
}
```

## 运行结果在哪里

每次运行都会生成一个目录：

```text
outputs/runs/<timestamp>-custom/
```

里面包含：

```text
task.json
retrieval.json
plan.json
prompt.md
final_report.json
knowledge/chunks.json
index/cases.index
index/metadata.json
```

其中：

- `retrieval.json`：本次任务命中的历史 Chunk。
- `prompt.md`：拼给 Planner 的完整提示词。
- `plan.json`：Planner 生成的计划。
- `final_report.json`：本次运行摘要。
- `knowledge/chunks.json`：从用户 Case 生成的 Chunk。
- `index/`：本次运行独立生成的向量索引。

## 使用自己的数据

最简单的方式：

1. 复制 `examples/custom_data/`。
2. 替换 `cases/CASE_CUSTOM_001.json`。
3. 修改 `task.txt`。
4. 修改 `repository_facts.txt`。
5. 运行 `run-custom`。

示例：

```bash
python -m algo_rag_demo.cli run-custom \
  --case-dir my_data/cases \
  --task-file my_data/task.txt \
  --repository-facts my_data/repository_facts.txt
```

如果你已经有原始对话，也可以让 DeepSeek 先抽取 Case：

```bash
source ./load_deepseek_env.sh
python -m algo_rag_demo.cli run-custom \
  --raw-dir my_data/raw \
  --extractor deepseek \
  --task-file my_data/task.txt \
  --planner deepseek
```

抽取出来的 Case 会写到本次 run 目录下，不会覆盖你的原始数据。

## 什么时候需要自己改代码

`run-custom` 解决的是：

```text
我的历史数据能不能进入 RAG
我的任务能不能检索到相关经验
Planner 能不能生成可读计划
产物能不能被审计和展示
```

如果你想让 Agent 真的修改自己的工程，还需要实现项目专属执行器：

- 修改或新增 `ToolRegistry`。
- 定义允许读写的目录。
- 定义安全 patch 模板。
- 定义真实测试命令。
- 定义 rollback 策略。

教学 Demo 的执行器在：

```text
algo_rag_demo/agent/executor.py
algo_rag_demo/agent/tool_registry.py
```

它可以作为参考，但不要直接假设它适用于任意项目。
