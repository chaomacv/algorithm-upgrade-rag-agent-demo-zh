# Custom Data Template

这个目录演示别人如何把自己的结构化 Case 放进来，然后运行通用实战入口。

最小可运行结构：

```text
examples/custom_data/
  cases/
    CASE_CUSTOM_001.json
  task.txt
  repository_facts.txt
```

运行：

```bash
bash scripts/run_custom_demo.sh
```

替换成自己的数据时，保持 `CASE_*.json` 文件名和 `EngineeringCase` 字段结构即可。
