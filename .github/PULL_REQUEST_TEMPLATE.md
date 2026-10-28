## 改动说明

<!-- 这个 PR 做了什么，为什么需要它。关联的 issue 用 "Closes #123" 自动关闭。 -->

Closes #

## 改动类型

- [ ] 新功能（feat）
- [ ] 缺陷修复（fix）
- [ ] 文档（docs）
- [ ] 重构或工程配置（refactor / chore）
- [ ] 仅格式调整（style）

## 影响范围

<!-- 勾选受影响的形态，便于 reviewer 决定验收方式 -->

- [ ] 命令行包 `dream_ai/`
- [ ] Web 服务 `web/app/`
- [ ] Web 前端 `web/web/`
- [ ] 桌面端 `desktop/`
- [ ] 文档 `docs/`
- [ ] CI / 打包 / 依赖

## 验证方式

<!-- 贴出实际执行的命令与结果，不要只写「已测试」。 -->

```bash
pytest
ruff check dream_ai tests examples web/app web/tools
ruff format --check dream_ai tests examples
```

补充说明（手动验证步骤、截图、录屏）：

## 检查清单

- [ ] 已阅读 [贡献指南](../docs/CONTRIBUTING.md)
- [ ] 新增或修改的行为有对应测试
- [ ] 面向用户的变更同步更新了文档与 `CHANGELOG.md`
- [ ] 涉及配置项时，`.env.example` 与文档中的变量名一致
- [ ] 提交内容不含 API Key、密码、服务器地址等敏感信息
- [ ] 提交历史按逻辑拆分，提交信息使用 `type: summary` 格式
