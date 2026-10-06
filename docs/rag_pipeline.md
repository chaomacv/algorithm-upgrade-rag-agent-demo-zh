# RAG Pipeline 说明

Case 会被切成三类 Chunk：

- task
- constraint
- solution

每个 Chunk 都会保留 `chunk_id`、`case_id`、`chunk_type`、`module`、`final_status` 和 `source`，方便检索后回溯到原始 Case 和历史对话。

索引使用归一化向量和内积相似度。安装了 `faiss-cpu` 时使用 FAISS；否则 Demo 会使用 NumPy 兼容的 `cases.index` 文件，这样离线教学版仍然能跑通。

