# 命令手册

## 低门槛教学版

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-lite.txt
bash scripts/run_teaching_demo.sh
```

它使用：

- `MockEmbeddingProvider`
- `MockPlanner`
- `PlanExecutor`

## 常用 CLI

构建索引：

```bash
python -m algo_rag_demo.cli build-index
```

检索历史案例：

```bash
python -m algo_rag_demo.cli search "Replace DRE while keeping downstream interface compatible"
```

运行失败恢复闭环：

```bash
python -m algo_rag_demo.cli demo-failure
```

运行测试：

```bash
python -m pytest -q
```

## DeepSeek 抽取 Case

```bash
export DEEPSEEK_API_KEY="your_api_key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-flash"
python -m algo_rag_demo.cli extract-case --extractor deepseek --raw examples/data/raw/conversation_dre_upgrade.json
```

批量处理所有合成原始对话：

```bash
python -m algo_rag_demo.cli extract-case --extractor deepseek --all
```

## DeepSeek Planner + BGE-M3

```bash
source ./load_deepseek_env.sh
python -m algo_rag_demo.cli build-index --provider bge-m3
python -m algo_rag_demo.cli demo-failure --provider bge-m3 --planner deepseek
```

## 检索排序示例

项目内置了多个相近 Case，方便观察 RAG 排序：

```bash
python -m algo_rag_demo.cli search "missing metadata algorithm runtime evidence"
python -m algo_rag_demo.cli search "pipeline json still selects old algorithm rollback"
python -m algo_rag_demo.cli search "DRE missing residual_map interface error"
```
