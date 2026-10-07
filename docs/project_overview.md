# 项目概览

算法升级 RAG 代理演示提供从历史对话到执行验证的完整案例。
历史对话抽取为 Case，按 Schema 生成 Chunk，用 BGE-M3 向量化、索引并检索。
Prompt Builder 合并经验、Skill、当前代码和错误上下文，LLM Planner 返回修改动作。
独立验证失败时再检索、修复，重试耗尽则回滚。

默认案例将 LegacyRanker 替换为 NeuralScorer，保持下游接口和旧算法回退。
结果来自真实代码执行和测试，不预先指定失败或成功。
LLM、Embedding、检索与项目执行均有接口；自定义数据遵循 EngineeringCase，
自定义执行与验证通过 ProjectAdapter 或配置接入。

运行后查看 attempts 下的检索、提示词、计划、执行与验证记录，
通过 Case 和 Conversation 溯源，final_report.json 记录最终状态。

见[快速开始](../README.md)、[架构](architecture.md)、[执行验证接入](execution_validation.md)。
