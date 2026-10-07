# 可配置 RAG Planning Pipeline

这是一个轻量、可替换模型的 RAG Planning 项目。用户可以放入自己的历史对话或结构化 Case，
选择 LLM Planner 和 Embedding 模型，然后自动完成：

```text
历史对话 / 结构化 Case
-> Case 抽取（已有结构化 Case 时跳过）
-> Schema 对齐的 Chunk
-> Embedding
-> Vector Index
-> Query Retrieval
-> Prompt Builder（历史经验 + Skill + 当前仓库事实）
-> LLM Planner
-> Restricted Tools 执行
-> Validation
   -> 通过：Final Report
   -> 失败：Error Analysis
      -> 错误再检索 -> 修复计划 -> 再执行与验证
      -> 重试耗尽：Rollback -> Final Report
```

## 快速开始

[演示demo任务介绍](docs/demo_task.md)

在仓库根目录运行，默认使用 DeepSeek + BGE-M3，并包含历史对话抽取：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 首次填写自己的 API key；password.txt 已被 Git 忽略
cp .env.example password.txt
# 编辑 password.txt 中的 DEEPSEEK_API_KEY 后加载
source ./load_deepseek_env.sh
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json run \
  --case-dir examples/custom_data/cases \
  --task-file examples/custom_data/task.txt \
  --repository-facts examples/custom_data/repository_facts.txt
```

也可以运行 `bash scripts/run_demo.sh`。首次需要下载 BGE-M3；
已有本地模型时可以通过 embedding 配置指向本地目录。

## 自定义数据与模型

历史对话和 Case 的设计方式、模型切换接口继续沿用。
自定义数据接入完整闭环时，还需配置自己的目标项目、可编辑文件与验证命令，
或实现 ProjectAdapter；见[执行与验证接口](docs/execution_validation.md)。
只检查数据检索与规划时可使用 `--plan-only`，仍调用配置中的 LLM 和 Embedding。

| 文档 | 内容 |
| --- | --- |
| [自定义数据到 Case](docs/03_architecture_for_reuse.md) | 历史对话、Schema、自动适配 |
| [执行与验证接口](docs/execution_validation.md) | 自定义工具、验证、重试和回滚 |
| [Case Schema](docs/case_schema.md) | EngineeringCase 字段 |
| [RAG Pipeline](docs/rag_pipeline.md) | Chunk、Embedding、索引与检索 |
| [命令手册](docs/commands.md) | 完整运行与单步命令 |
| [架构概览](docs/architecture.md) | 模块边界与替换接口 |

## 模型切换

LLM 配置在 configs/*.json，更换 OpenAI-compatible 服务只需修改
base_url、api_key_env 和 model：

```json
{"llm": {"provider": "deepseek", "base_url": "https://api.deepseek.com",
         "api_key_env": "DEEPSEEK_API_KEY", "model": "deepseek-flash"}}
```

Embedding 配置：

```json
{"embedding": {"provider": "bge-m3", "model": "BAAI/bge-m3"}}
```

自定义 Embedding 实现 EmbeddingProvider.encode_documents/encode_query，
在 get_embedding_provider() 注册。检索实现遵循 Retriever.search() 返回结构；
替换检索器后仍可复用 run_agent()。Mock 向量仅保留用于内部自动化测试。

## 项目目录

```text
algo_rag_demo/
  case_pipeline/  Conversation -> Case -> Chunk
  rag/            Embedding、Index、Retrieval、Prompt
  agent/          LLM、Planner、ProjectAdapter、闭环 Workflow
configs/          模型与执行配置
examples/
  custom_data/    历史对话、Case、任务与仓库事实
  algorithm_upgrade/  示例算法项目、独立验证与 Skill
docs/             接入文档
scripts/          一键运行入口
tests/            自动化测试
```

文件白名单约束代理的编辑入口，验证命令来自用户配置；这个执行器不是操作系统沙箱。
不可信代码可通过自己的 Adapter 在容器中执行。API key、password.txt、.env、
outputs 和缓存不提交到 GitHub。
