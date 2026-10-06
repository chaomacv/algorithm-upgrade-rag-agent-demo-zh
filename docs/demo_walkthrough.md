# Demo 讲解流程

运行：

```bash
python -m algo_rag_demo.cli build-index
python -m algo_rag_demo.cli demo-failure
```

失败恢复 Demo 会做这些事：

1. 先执行一次直接替换。
2. 因为缺少 `residual_map`，接口验证失败。
3. 使用具体失败信息再次检索历史 Case。
4. 命中 `CASE_DRE_001_solution`。
5. 增加兼容适配层。
6. 把配置切换到 `new_llf`。
7. 验证接口、构建、运行、算法切换和回滚。

