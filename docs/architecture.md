# 架构概览

项目分为四层：

1. Case 抽取：把合成的工程师与 Agent 对话转换成结构化 `EngineeringCase`。
2. RAG：把 Case 切成 `task`、`constraint`、`solution` 三类知识 Chunk，并建立索引。
3. Planner：结合用户任务、检索结果、当前仓库事实和 Skill 生成执行计划。
4. 受控工具：只修改示例工程，并运行接口、构建、运行、算法切换和回滚验证。

系统刻意保持小规模，这样可以在一次简短展示里看完整个工作流。

