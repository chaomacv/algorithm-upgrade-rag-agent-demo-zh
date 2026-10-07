# 项目概览

这个仓库是一个可配置的 RAG Planning Pipeline。它适合把历史工程经验整理成结构化 Case，然后在新任务到来时检索相似经验，并交给 LLM 生成可审查的工程计划。

默认推荐组合：

```text
DeepSeek Planner + BAAI/bge-m3 Embedding
```

但这两个部分都不是写死的。LLM 可以替换为其他 OpenAI-compatible 服务，embedding 也可以替换为其他 provider。

## 完整链路

```text
历史对话
-> LLM 抽取
-> 结构化 EngineeringCase
-> Schema 对齐的 Chunk
-> Chunk Text Embedding
-> Vector Index
-> Query Retrieval
-> 回溯 Case 和原始 Conversation
-> Prompt Builder
-> LLM Planner
-> Plan / Report
```

如果用户已经有结构化 Case，可以从 `EngineeringCase` 直接开始，不必经过历史对话抽取。

## 核心产物

一次运行会生成：

```text
outputs/runs/<timestamp>-rag-plan/
  task.json
  retrieval.json
  prompt.md
  plan.json
  final_report.json
  knowledge/chunks.json
  index/
```

这些文件用于回答四个问题：

- `retrieval.json`：检索到了什么，排序是否合理。
- `prompt.md`：LLM 看到了哪些上下文。
- `plan.json`：LLM 给出的计划是什么。
- `final_report.json`：本次运行使用了哪些输入、索引和知识产物。

## 自带示例的定位

仓库里的示例以“复杂算法模块系统中的单模块算法替换”为背景，只是为了提供一个具体数据样板。项目代码本身不绑定这个场景，换成调度、推荐、风控、数据治理、配置迁移等工程问题也可以沿用同一套 schema 和接口。
