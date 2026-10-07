# 执行与验证接口

完整案例默认运行示例排名项目；替换自己的数据后，还要配置对应的项目执行与验证。
数据、LLM 和 Embedding 的现有接口继续使用。

## 配置接入文件编辑项目

复制默认配置为 configs/my_project.json，保留模型配置，修改以下片段：

```json
{
  "paths": {
    "case_dir": "my_data/cases",
    "task_file": "my_data/task.txt",
    "repository_facts": "my_data/repository_facts.txt"
  },
  "execution": {
    "factory": "algo_rag_demo.agent.executor:FileProjectAdapter",
    "template_dir": "my_project",
    "allowed_files": ["src/adapter.py", "config.json"],
    "validation_commands": [["{python}", "-m", "pytest", "tests", "-q"]],
    "skill_file": "my_data/skill.md",
    "max_attempts": 3,
    "timeout": 120
  }
}
```

原始历史对话输入使用 paths.raw_dir 或 --raw-dir。移除示例的 demo_only 标记。
template_dir 是待复制的项目根目录，建议提供最小目标项目，不包含虚拟环境、缓存或秘密。
执行修改 outputs/runs 下的副本。依赖提前安装在运行 CLI 的 Python 环境中。

allowed_files 是可编辑的相对路径；验证脚本应放在白名单外。
validation_commands 使用 argv 数组，不使用 shell 字符串；{python} 替换为当前解释器。
退出码 0 表示通过，其他退出码或超时表示失败。

Skill 写项目约束、动作格式、接口规则和回退要求；repository_facts 写当前事实。
执行器还会将实际文件内容与验证命令提供给 Planner。

## 自定义 ProjectAdapter

在可导入模块中实现下列方法，将 execution.factory 改为 my_package.adapter:create_adapter。
工厂接收 (execution_config, run_dir)，返回适配器对象。

| 方法 | 输入 / 返回 | 用途 |
| --- | --- | --- |
| facts() | 返回 str | 当前代码、允许动作、验证条件 |
| checkpoint() | 无返回要求 | 捕获执行前状态 |
| execute(plan) | 返回 dict | 用自己的受限工具应用 plan.actions |
| validate() | {"passed": bool, "checks": [...]} | 实际测试或业务验证 |
| rollback() | {"restored": bool, ...} | 恢复状态并核实 |

例如使用 apply_patch、服务配置工具或容器工具，只需修改 Adapter 与 facts 中的
动作 Schema。闭环 run_agent 不需要改动。validate.passed 必须是真正的布尔值；
LLM 的 validation_plan 是计划，不能当作已验证结果。

## 默认案例验证

examples/algorithm_upgrade/validate.py 独立检查：

1. interface：id、score、metadata.confidence、metadata.reason 的字段和类型。
2. runtime：实际启用 NeuralScorer。
3. regression：准确分数与排序、空输入。
4. rollback：显式选择 LegacyRanker 仍得到旧结果。

失败轮次保存 error_analysis.json；真实错误和当前代码进入下一轮提示词，
错误查询经过同一 Embedding 与索引重新检索。最多 max_attempts 轮；
全部失败则恢复可编辑文件的原始字节并核实，报告 rolled_back。
旧算法回退验证与最终文件回滚是两个不同检查。

文件编辑和测试运行具有当前用户权限，文件白名单不是操作系统沙箱；
需要隔离时通过 Adapter 接入容器。验证命令来自配置，模型不能通过 actions 新增命令。
