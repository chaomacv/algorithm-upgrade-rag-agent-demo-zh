# 算法升级 RAG Agent Demo

这是一个中文教学版工程示例，用来展示如何把历史工程对话沉淀为结构化 Case，再通过 RAG 检索、Planner 规划、Executor 执行和验证闭环，辅助完成复杂算法模块替换任务。

项目中的代码、数据、日志和配置均为合成示例，不包含真实业务数据或公司内部信息。

## 一句话理解

这个项目演示的是：

```text
历史对话
-> 结构化 Case
-> Schema 对齐的 Chunk
-> 向量索引
-> RAG 检索
-> Planner 生成计划
-> Executor 受控执行
-> Validation 验证
-> 失败后再次检索并修复
```

示例场景是“复杂算法模块系统中的单模块算法替换”：把旧的 `OldDRE` 替换成新的 `NewLLF`，同时保持下游接口兼容。

## 快速开始

低门槛教学版不需要 DeepSeek、不需要 BGE-M3、不需要网络：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-lite.txt
bash scripts/run_teaching_demo.sh
```

运行成功后会看到完整闭环：

```text
历史 Case -> RAG 检索 -> Planner -> Executor
-> 验证失败 -> 错误再检索 -> 修复计划 -> 再执行 -> SUCCESS
```

如果你想用自己的结构化 Case 跑通“检索 + 规划 + 报告”链路：

```bash
python -m algo_rag_demo.cli run-custom \
  --case-dir examples/custom_data/cases \
  --task-file examples/custom_data/task.txt \
  --repository-facts examples/custom_data/repository_facts.txt
```

## 文档导航

| 模块 | 适合读者 | 内容 |
| --- | --- | --- |
| [项目背景与问题](docs/project_overview.md) | 第一次了解项目的人 | 为什么算法替换会失败，示例场景是什么 |
| [Teaching Demo](docs/01_teaching_demo.md) | 想快速跑通的人 | 无 API、无网络的一键演示 |
| [DeepSeek + BGE-M3](docs/02_live_deepseek_bge.md) | 想接真实模型的人 | DeepSeek Planner 和 BGE-M3 Embedding |
| [自定义实战入口](docs/03_architecture_for_reuse.md) | 想放入自己数据直接跑的人 | 自定义 Case、任务、检索、计划和报告 |
| [Case 与 Chunk](docs/case_schema.md) | 关注知识结构的人 | Case Schema 和 Chunk 设计 |
| [RAG Pipeline](docs/rag_pipeline.md) | 关注检索链路的人 | 从 chunk 到 index 再到 retrieval |
| [命令手册](docs/commands.md) | 需要实际操作的人 | 构建索引、搜索、运行 demo、DeepSeek 抽取 |
| [运行产物](docs/run_artifacts.md) | 需要展示结果的人 | `outputs/runs/` 下每个文件怎么看 |

## 项目目录

```text
algo_rag_demo/      核心代码：Case pipeline、RAG、Agent、CLI
examples/           示例数据、示例工程、示例 Skill
docs/               详细说明文档
scripts/            一键运行脚本
tests/              单元测试和流程测试
outputs/            生成的索引和运行日志，不提交到 GitHub
```

## 两条使用路线

教学讲解优先看：

```text
README
-> docs/project_overview.md
-> docs/01_teaching_demo.md
-> docs/run_artifacts.md
```

工程复用优先看：

```text
README
-> docs/03_architecture_for_reuse.md
-> examples/custom_data/
-> docs/case_schema.md
-> docs/rag_pipeline.md
-> CONTRIBUTING.md
```

## GitHub 模块

- [Contributing](CONTRIBUTING.md)：如何贡献 case、文档、执行器和测试。
- [Code of Conduct](CODE_OF_CONDUCT.md)：协作规范。
- [Security](SECURITY.md)：密钥、数据和安全边界说明。
- [MIT License](LICENSE)：开源许可证。
