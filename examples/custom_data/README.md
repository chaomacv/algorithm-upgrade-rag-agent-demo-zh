# 示例数据与自定义模板

raw/ 是排名算法替换的历史工程对话，cases/ 是结构化数据模板，
task.txt 是新任务，repository_facts.txt 是当前示例项目事实。

在仓库根目录运行 bash scripts/run_demo.sh：
默认从 raw/ 用 LLM 抽取本次 Case，再完成 BGE-M3 检索、执行、验证与重试或回滚。
示例代码和独立验证位于 examples/algorithm_upgrade。

自己的数据继续遵循 EngineeringCase Schema；完整执行还需接入对应项目验证。
见[数据设计](../../docs/03_architecture_for_reuse.md)、
[执行与验证接口](../../docs/execution_validation.md)。
