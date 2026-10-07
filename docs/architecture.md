# 架构概览

默认提供完整算法升级案例，通用闭环与具体项目通过接口连接。

```text
Conversation -> LLMCaseExtractor -> EngineeringCase -> chunk_cases
-> EmbeddingProvider -> Index -> Retriever.search
-> build_prompt -> LLMPlanner -> ProjectAdapter.execute
-> ProjectAdapter.validate
   Pass: Final Report
   Fail: Error Analysis -> error query -> Retrieval -> repair plan
   Attempts exhausted: ProjectAdapter.rollback -> Final Report
```

| 位置 | 职责 |
| --- | --- |
| case_pipeline/parser.py | 历史对话抽取与 Schema 校验 |
| case_pipeline/chunker.py | 按任务、约束、解决方案创建 Chunk |
| rag/embedding.py | EmbeddingProvider，文档与查询使用同一向量空间 |
| rag/index_builder.py | 索引与向量行到 Chunk 元数据映射 |
| rag/retriever.py | 检索并返回可溯源的 RetrievalResult |
| rag/prompt_builder.py | 合并任务、经验、Skill、事实和错误上下文 |
| agent/llm_provider.py | 可替换 OpenAI-compatible 模型服务 |
| agent/planner.py | LLMPlanner 返回计划与结构化 actions |
| agent/executor.py | ProjectAdapter 协议、白名单编辑与固定验证命令 |
| agent/workflow.py | 检索、执行、验证、错误反馈、重试和回滚 |
| cli.py | 抽取、建索引、检索、规划和完整 run 命令 |

FileProjectAdapter 在运行目录复制项目，读取实际文件作为仓库事实。
LLM 的 write_file 动作只能编辑白名单文件；验证命令来自配置而非模型。
实际运行 Python 代码仍具有当前用户权限，该执行器不等同沙箱。

自己的数据映射到 EngineeringCase 后，Chunk 到规划步骤自动适配。
项目工具和验证通过 [ProjectAdapter 接口](execution_validation.md) 适配。
run_agent 接收 retriever、planner、adapter，不绑定示例算法或 DeepSeek。
