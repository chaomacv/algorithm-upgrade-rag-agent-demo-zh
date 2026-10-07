# 可配置 RAG Planning Pipeline

这是一个轻量、可替换模型的 RAG Planning 项目。用户可以放入自己的历史对话或结构化 Case，选择 LLM Planner 和 Embedding 模型，然后自动完成：

```text
历史对话 / 结构化 Case
-> Case 抽取
-> Schema 对齐的 Chunk
-> Embedding
-> Vector Index
-> Query Retrieval
-> LLM Planner
-> Prompt / Plan / Report
```

默认推荐组合是：

```text
DeepSeek Planner + BAAI/bge-m3 Embedding
```

同时也保留接口，方便替换成其他 OpenAI-compatible LLM 或其他 embedding provider。

## 快速开始

离线 smoke test，不需要 API key，也不下载模型：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-lite.txt
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json run \
  --case-dir examples/custom_data/cases \
  --task-file examples/custom_data/task.txt \
  --repository-facts examples/custom_data/repository_facts.txt \
  --embedding-provider mock \
  --offline
```

真实 DeepSeek + BGE-M3：

```bash
pip install -r requirements.txt
source ./load_deepseek_env.sh
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json run \
  --case-dir examples/custom_data/cases \
  --task-file examples/custom_data/task.txt \
  --repository-facts examples/custom_data/repository_facts.txt
```

每次运行都会生成：

```text
outputs/runs/<timestamp>-rag-plan/
  task.json
  retrieval.json
  prompt.md
  plan.json
  final_report.json
  knowledge/chunks.json
  index/cases.index
  index/metadata.json
```

## 自定义数据

最小输入结构：

```text
my_data/
  cases/
    CASE_001.json
  task.txt
  repository_facts.txt
```

运行：

```bash
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json run \
  --case-dir my_data/cases \
  --task-file my_data/task.txt \
  --repository-facts my_data/repository_facts.txt
```

如果你有原始历史对话，可以先让 LLM 抽取结构化 Case：

```bash
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json extract-cases \
  --raw-dir my_data/raw \
  --case-dir my_data/cases
```

## 模型切换

LLM 配置在 `configs/*.json`：

```json
{
  "llm": {
    "provider": "deepseek",
    "base_url": "https://api.deepseek.com",
    "api_key_env": "DEEPSEEK_API_KEY",
    "model": "deepseek-flash"
  }
}
```

换成其他 OpenAI-compatible 服务时，只需要改：

```text
base_url
api_key_env
model
```

Embedding 配置：

```json
{
  "embedding": {
    "provider": "bge-m3",
    "model": "BAAI/bge-m3"
  }
}
```

当前内置：

- `bge-m3`：真实语义向量，默认模型 `BAAI/bge-m3`
- `mock`：离线测试用确定性向量

## 文档导航

| 文档 | 内容 |
| --- | --- |
| [自定义数据到 Case](docs/03_architecture_for_reuse.md) | 如何设计自己的历史对话和结构化 Case |
| [Case Schema](docs/case_schema.md) | `EngineeringCase` 字段含义 |
| [RAG Pipeline](docs/rag_pipeline.md) | Chunk、Embedding、Index、Retrieval |
| [命令手册](docs/commands.md) | CLI 命令和配置示例 |
| [架构概览](docs/architecture.md) | 模块边界和接口 |

## 项目目录

```text
algo_rag_demo/
  agent/          LLM provider 和 Planner
  case_pipeline/  Conversation -> Case -> Chunk
  rag/            Embedding、Index、Retrieval、Prompt
configs/          LLM 和 Embedding 配置
examples/         用户数据模板
scripts/          一键运行脚本
tests/            核心接口测试
```

## 安全说明

不要提交 API key、真实内部日志、客户数据或未脱敏对话。`password.txt`、`.env`、`outputs/`、索引产物和缓存已经被 `.gitignore` 排除。
