# Security Policy

这个仓库是教学 Demo，但仍然需要清楚处理密钥、数据和执行边界。

## 不要提交的内容

不要提交：

- `password.txt`
- `.env`
- API key
- SSH key
- 真实业务日志
- 客户数据
- 公司内部代码片段
- `outputs/` 下的运行产物
- 模型缓存或向量索引文件

## DeepSeek API key

本地使用 DeepSeek 时，可以创建 `password.txt`：

```bash
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
```

然后运行：

```bash
source ./load_deepseek_env.sh
```

`password.txt` 已经被 `.gitignore` 排除。提交前仍建议执行一次敏感信息扫描。

## Executor 安全边界

项目中的 `PlanExecutor` 不直接执行任意 LLM 生成代码。LLM 输出会被当作意图，再映射到 `ToolRegistry` 中的受控工具和安全修改模板。

如果你把项目改造成真实工程工具，请优先审查：

- `algo_rag_demo/agent/executor.py`
- `algo_rag_demo/agent/tool_registry.py`
- `algo_rag_demo/demo_scenarios/`

## 报告问题

如果你发现密钥泄露、危险执行路径或文档中的安全误导，请优先通过私有渠道联系仓库维护者，不要在公开 issue 中贴出敏感内容。
