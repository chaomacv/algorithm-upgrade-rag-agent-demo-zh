# Security Policy

这个仓库是可配置 RAG Planning Pipeline，需要清楚处理密钥、数据和执行边界。

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

## 执行安全边界

项目默认只生成 RAG-backed plan 和可审计报告，不直接执行任意 LLM 生成代码。

如果你在自己的工程里继续接入自动执行器，请优先明确：

- 允许修改的目录和文件类型。
- 允许运行的命令白名单。
- 测试、验证和回滚规则。
- LLM 输出如何转成受控操作，而不是直接执行。

## 报告问题

如果你发现密钥泄露、危险执行路径或文档中的安全误导，请优先通过私有渠道联系仓库维护者，不要在公开 issue 中贴出敏感内容。
