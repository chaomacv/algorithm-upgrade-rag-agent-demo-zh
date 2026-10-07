# 命令手册

这份文档只保留当前可用的通用命令。所有命令都围绕同一条链路：

```text
历史对话 / 结构化 Case -> Chunk -> Embedding -> Index -> Retrieval -> Planner -> Report
```

## 安装依赖

离线 smoke test 只需要轻量依赖：

```bash
pip install -r requirements-lite.txt
```

真实 DeepSeek + BGE-M3 需要完整依赖：

```bash
pip install -r requirements.txt
```

## 一键运行内置数据

不调用 LLM，不下载 embedding 模型，用于确认代码链路能跑通：

```bash
bash scripts/run_pipeline_offline.sh
```

真实模式：

```bash
source ./load_deepseek_env.sh
bash scripts/run_pipeline_deepseek_bge.sh
```

## 使用结构化 Case 运行

```bash
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json run \
  --case-dir examples/custom_data/cases \
  --task-file examples/custom_data/task.txt \
  --repository-facts examples/custom_data/repository_facts.txt
```

离线验证时加上：

```bash
--embedding-provider mock --offline
```

## 从历史对话抽取 Case

原始对话放到 `raw/`：

```text
my_data/
  raw/
    conversation_001.json
  task.txt
  repository_facts.txt
```

抽取：

```bash
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json extract-cases \
  --raw-dir my_data/raw \
  --case-dir my_data/cases
```

然后运行完整链路：

```bash
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json run \
  --case-dir my_data/cases \
  --task-file my_data/task.txt \
  --repository-facts my_data/repository_facts.txt
```

也可以让 `run` 先抽取再检索规划：

```bash
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json run \
  --raw-dir my_data/raw \
  --task-file my_data/task.txt \
  --repository-facts my_data/repository_facts.txt
```

## 单独构建索引

```bash
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json build-index \
  --case-dir examples/custom_data/cases
```

## 单独检索

```bash
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json search \
  --task "new scorer changed metadata schema and downstream validation fails" \
  --case-dir examples/custom_data/cases \
  --top-k 5
```

## 单独生成计划

```bash
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json plan \
  --task-file examples/custom_data/task.txt \
  --case-dir examples/custom_data/cases \
  --repository-facts examples/custom_data/repository_facts.txt
```

## 切换模型

LLM 和 embedding 都来自配置文件，也可以用命令行覆盖 embedding：

```bash
python -m algo_rag_demo.cli --config configs/openai_compatible_example.json run \
  --case-dir examples/custom_data/cases \
  --task-file examples/custom_data/task.txt \
  --repository-facts examples/custom_data/repository_facts.txt \
  --embedding-provider bge-m3 \
  --embedding-model BAAI/bge-m3
```

## 运行测试

```bash
python -m pytest -q
```
