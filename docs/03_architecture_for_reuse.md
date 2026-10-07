# 自定义数据到 Case

这个项目的核心不是固定示例，而是一条可复用链路：

```text
你的历史对话
-> 结构化 EngineeringCase
-> Schema 对齐的 Chunk
-> Embedding
-> Vector Index
-> Retrieval
-> LLM Planner
-> ProjectAdapter 执行
-> Validation
-> 成功报告 / 错误再检索与重试 / 回滚
```

## 方式一：直接写结构化 Case

最稳定的方式是直接准备 `CASE_*.json`：

```text
my_data/
  cases/
    CASE_001.json
  task.txt
  repository_facts.txt
```

最小 Case 示例：

```json
{
  "case_id": "CASE_001",
  "module": "Ranking",
  "task": "Replace old ranking algorithm with a new scorer",
  "old_algorithm": "OldRanker",
  "new_algorithm": "NewScorer",
  "constraints": {
    "interface": ["Keep downstream metadata schema stable"],
    "engineering": ["Keep rollback path available"]
  },
  "steps": ["Inspect interface", "Patch adapter", "Run validation"],
  "problems": [
    {
      "stage": "first replacement",
      "symptom": "metadata.reason is missing",
      "root_cause": "new scorer changed output schema"
    }
  ],
  "solutions": [
    {
      "problem": "metadata schema mismatch",
      "solution": "add adapter preserving required metadata"
    }
  ],
  "validation": {
    "interface": "passed",
    "runtime": "passed",
    "rollback": "passed"
  },
  "final_status": "success",
  "reusable_experience": [
    "Treat output metadata as public interface",
    "Verify runtime evidence before declaring replacement complete"
  ],
  "source_conversation_id": "CONV_001"
}
```

运行：

```bash
python -m algo_rag_demo.cli --config configs/my_project.json run \
  --case-dir my_data/cases \
  --task-file my_data/task.txt \
  --repository-facts my_data/repository_facts.txt
```

## 方式二：从历史对话自动抽取 Case

如果你有历史对话，先整理成：

```json
{
  "conversation_id": "CONV_001",
  "task": "Replace old ranking algorithm with a new scorer",
  "messages": [
    {"role": "engineer", "content": "We need to replace OldRanker with NewScorer."},
    {"role": "agent", "content": "I will inspect the output schema first."},
    {"role": "tool", "name": "test", "content": "FAIL: metadata.reason is missing."},
    {"role": "agent", "content": "The new scorer changed the metadata schema, so we need an adapter."}
  ]
}
```

然后运行：

```bash
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json extract-cases \
  --raw-dir my_data/raw \
  --case-dir my_data/cases
```

抽取使用配置文件里的 LLM provider。默认配置是 DeepSeek，但只要服务兼容 OpenAI Chat Completions，就可以通过 `configs/*.json` 替换。

## repository_facts 怎么写

`repository_facts.txt` 用来告诉 Planner 当前项目事实，例如：

```text
- Ranking module path: src/ranking/
- Config path: config/pipeline.json
- Normal test command: pytest tests/ranking -q
- Runtime evidence should include metadata.algorithm == "new_scorer"
- Rollback can switch config back to old_ranker
```

它不是历史经验，而是当前仓库事实。Planner 会同时参考：

```text
当前任务 + 当前仓库事实 + 检索到的历史 Case
```

## 运行后如何看结果

每次运行会生成：

```text
outputs/runs/<timestamp>-algorithm-upgrade-<id>/
  task.json
  attempts/01/
    retrieval.json
    prompt.md
    plan.json
    execution.json
    validation.json
  final_report.json
  knowledge/chunks.json
  index/
```

重点看：

- `attempts/01/retrieval.json`：检索排序是否正确。
- `attempts/01/prompt.md`：最终给 Planner 的上下文。
- `attempts/01/plan.json`：LLM 生成的工程计划。
- `knowledge/chunks.json`：Case 被切成了哪些检索单元。

## 自动适配的边界

项目会自动适配：

- 用户自己的 `CASE_*.json`
- 用户自己的 `task.txt`
- 用户自己的 `repository_facts.txt`
- LLM provider
- embedding provider
- index 输出目录
- run artifact 输出目录

默认演示执行并验证示例项目副本。自己的数据要同步接入对应的项目执行与验证：
创建 configs/my_project.json，设置 template_dir、allowed_files、validation_commands 和
skill_file，或实现 ProjectAdapter。详见[执行与验证接口](execution_validation.md)。
自定义数据不会自动套用默认排名项目的验证。仅检查数据检索和计划时可使用 --plan-only。
