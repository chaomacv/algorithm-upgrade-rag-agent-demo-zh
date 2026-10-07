# Custom Data Template

这个目录演示如何把自己的历史工程经验接入通用 RAG Planning Pipeline。

最小可运行结构：

```text
examples/custom_data/
  cases/
    CASE_CUSTOM_001.json
  task.txt
  repository_facts.txt
```

离线运行：

```bash
bash scripts/run_pipeline_offline.sh
```

真实 DeepSeek + BGE-M3 运行：

```bash
source ./load_deepseek_env.sh
bash scripts/run_pipeline_deepseek_bge.sh
```

替换成自己的结构化数据时，保持 `CASE_*.json` 文件名和 `EngineeringCase` 字段结构即可。

建议先只替换 `task.txt`，观察检索排序是否符合预期；再逐步替换 `cases/` 下的历史 Case。

如果你只有历史对话，可以参考 `raw/conversation_custom_001.json`，然后运行：

```bash
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json extract-cases \
  --raw-dir examples/custom_data/raw \
  --case-dir examples/custom_data/cases
```
