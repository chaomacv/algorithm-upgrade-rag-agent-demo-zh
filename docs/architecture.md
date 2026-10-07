# 架构概览

项目现在只保留一条通用 RAG Planning Pipeline，避免把固定示例流程和可复用能力混在一起。

```text
历史对话 / 结构化 Case
-> Case 抽取
-> Schema 对齐的 Chunk
-> Chunk Text Embedding
-> Vector Index
-> Query Retrieval
-> Prompt Builder
-> LLM Planner
-> Plan / Report
```

## 模块边界

```text
algo_rag_demo/
  case_pipeline/  历史对话、结构化 Case、Chunk
  rag/            Embedding、Index、Retrieval、Prompt
  agent/          LLM provider、Planner
  cli.py          命令入口
```

## 接口设计

LLM 接口在 `algo_rag_demo/agent/llm_provider.py`：

- `ChatProvider`：通用协议。
- `OpenAICompatibleChatProvider`：适配 DeepSeek、OpenAI-compatible 服务。
- `build_chat_provider()`：从配置创建 provider。

Embedding 接口在 `algo_rag_demo/rag/embedding.py`：

- `EmbeddingProvider`：通用协议。
- `BGEEmbeddingProvider`：真实语义向量。
- `MockEmbeddingProvider`：离线测试向量。
- `get_embedding_provider()`：从 provider 名称和模型名创建实例。

Planner 接口在 `algo_rag_demo/agent/planner.py`：

- `Planner`：通用协议。
- `LLMPlanner`：读取检索结果并调用 LLM 生成计划。
- `EvidencePlanner`：不调用外部服务的确定性备用实现。

## 数据适配方式

项目支持两种输入：

1. 用户直接提供 `EngineeringCase` JSON。
2. 用户提供历史对话 JSON，再用 LLM 抽取成 `EngineeringCase`。

后续 chunk、embedding、index、retrieval、prompt 和 planner 都只依赖 `EngineeringCase` schema，因此换数据后不需要改后续代码。

## 为什么不内置执行器

真实工程执行依赖具体仓库的文件结构、测试命令、patch 策略、权限边界和回滚机制。这个项目的通用部分停在 RAG-backed plan 和可审计报告，避免把一个示例执行器伪装成通用执行能力。
