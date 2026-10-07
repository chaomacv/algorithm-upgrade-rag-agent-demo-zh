# 命令手册

在仓库根目录执行。默认使用配置中的 DeepSeek 和 BGE-M3。

## 完整算法升级演示

```bash
pip install -r requirements.txt
source ./load_deepseek_env.sh
bash scripts/run_demo.sh
```

对应命令：

```bash
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json run \
  --case-dir examples/custom_data/cases \
  --task-file examples/custom_data/task.txt \
  --repository-facts examples/custom_data/repository_facts.txt
```

默认配置包含 raw_dir，会重新抽取 Case 到运行目录，再建索引、规划、执行和验证。
直接运行 run 也会使用配置中的任务。只使用已有 Case 时移除配置的 paths.raw_dir。

## 自定义数据完整运行

根据[执行与验证接口](execution_validation.md)创建 configs/my_project.json：

```bash
python -m algo_rag_demo.cli --config configs/my_project.json run \
  --case-dir my_data/cases --task-file my_data/task.txt \
  --repository-facts my_data/repository_facts.txt
```

从历史对话开始可加 --raw-dir my_data/raw。自定义 Case 必须配置对应执行器，
默认示例配置不会将任意数据拿到排名示例中执行。只规划可加 --plan-only。

## 单步命令

```bash
python -m algo_rag_demo.cli extract-cases --raw-dir my_data/raw --case-dir my_data/cases
python -m algo_rag_demo.cli build-index --case-dir my_data/cases
python -m algo_rag_demo.cli search --case-dir my_data/cases --task "metadata schema mismatch" --top-k 5
python -m algo_rag_demo.cli plan --case-dir my_data/cases --task-file my_data/task.txt \
  --repository-facts my_data/repository_facts.txt
```

build-index/search/plan 默认使用 outputs/index，可指定 --index-dir。
run 的索引和记录始终放在本次运行目录。

## 模型切换与测试

通过 --config configs/openai_compatible_example.json 切换 LLM；
完整执行前也需加入 execution。Embedding 可用
--embedding-provider bge-m3 --embedding-model /path/to/local/model 覆盖。

```bash
python -m pytest -q
```

测试使用受控模型响应与测试向量验证真实执行、失败再检索和回滚，
不等于在线 DeepSeek + BGE-M3 验证。
