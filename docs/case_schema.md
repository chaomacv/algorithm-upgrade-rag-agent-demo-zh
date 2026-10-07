# Case Schema 说明

`EngineeringCase` 是后续 Chunk、Embedding、Index、Retrieval 和 Planner 的统一输入。只要用户自己的数据能对齐这个 schema，后面步骤就能自动适配。

## 字段

- `case_id`：案例唯一 ID。
- `module`：案例所属模块或业务域。
- `task`：当时要解决的工程任务。
- `old_algorithm`：可选，旧实现、旧策略或旧模块名称。
- `new_algorithm`：可选，新实现、新策略或新模块名称。
- `constraints`：约束集合，建议按 `interface`、`engineering`、`validation`、`rollback` 等类别组织。
- `steps`：当时采取过的关键步骤。
- `problems`：执行中遇到的问题，建议包含 `stage`、`symptom`、`root_cause`。
- `solutions`：对应问题的解决方式。
- `validation`：验证结果，例如接口、运行时、配置、回滚。
- `final_status`：最终状态，例如 `success`、`partial`、`failed`。
- `reusable_experience`：可以复用到新任务里的经验。
- `source_conversation_id`：来源历史对话 ID。

## 原始对话格式

如果不想手写 Case，可以先提供 `Conversation`：

```json
{
  "conversation_id": "CONV_001",
  "task": "Replace legacy ranking module with a new scoring module",
  "messages": [
    {"role": "user", "content": "We need to replace LegacyRanker."},
    {"role": "assistant", "content": "I will compare output contracts first."},
    {"role": "tool", "name": "pytest", "content": "FAIL: metadata.reason is missing."}
  ]
}
```

`extract-cases` 会调用配置里的 LLM，把它抽取成 `EngineeringCase`。

## 设计建议

Case 不是聊天记录存档，而是经验卡片。建议保留稳定结论、约束、错误症状、根因、解决方案和验证结果，减少重复寒暄、临时猜测和无效试错。

