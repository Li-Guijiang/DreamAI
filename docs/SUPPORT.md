# 获取帮助

<sub>[返回文档索引](./README.md)</sub>

先按下面的顺序自查，多数问题在前两步就能解决。仍然解决不了，再按第 4 节选择渠道。

## 1. 先看文档

| 你的问题 | 看这里 |
|---|---|
| 怎么装、怎么跑起来 | [SETUP.md](./SETUP.md)（分步安装）、[GUIDE.md](./GUIDE.md)（中文逐步讲解） |
| 某个命令怎么用、报错怎么处理 | [GUIDE.md](./GUIDE.md) 第 5 节命令速查、第 9 节常见问题排查 |
| 配置项含义与默认值 | 根目录 [.env.example](../.env.example)、[GUIDE.md](./GUIDE.md) 第 6 节 |
| 想看代码怎么分层 | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| 某个功能什么时候做 | [ROADMAP.md](./ROADMAP.md) |
| Web 部署、nginx、systemd | [web/README.md](../web/README.md)、[web/deploy/](../web/deploy) |
| 桌面端打包、图标、签名 | [desktop/README.md](../desktop/README.md) |

## 2. 确认是不是环境问题

```bash
python --version          # 需要 3.11+
pip show dream-ai         # 确认安装的是哪个版本
python -m dream_ai        # 看到欢迎横幅说明启动正常
```

没有 API Key 时进入的是**离线演示模式**，回复由占位实现生成。这不是故障，配置 `DREAMAI_API_KEY` 后重启即可接入真实模型。

## 3. 自己先排查一遍

1. 复制报错信息里的关键字，在本仓库 issue 中搜索（含已关闭的 issue）。
2. 用 `DREAMAI_AUTONOMY_VERBOSE=true` 重跑一次，观察失败发生在哪个阶段。
3. 涉及工具调用时，先用 `/tools` 确认工具已注册，再用 `/tool <name> <json>` 单独复现。

## 4. 选择渠道

| 情况 | 渠道 | 响应预期 |
|---|---|---|
| 可复现的缺陷 | [提交缺陷报告](https://github.com/Li-Guijiang/DreamAI/issues/new?template=bug_report.yml) | 按 issue 模板填写，缺失步骤会退回补充 |
| 新功能建议 | [提交功能建议](https://github.com/Li-Guijiang/DreamAI/issues/new?template=feature_request.yml) | 先对照路线图，避免与已计划内容重复 |
| 安全漏洞 | [SECURITY.md](./SECURITY.md) 中的私下渠道 | 请勿公开提交 |
| 只想试用 | <https://liguijiang.com> | 无需安装，免费模型直接可用 |

## 5. 提问时请附上

1. 操作系统与 Python / Node 版本；
2. 你执行的确切命令；
3. 完整报错信息（不要截断堆栈）；
4. 已尝试过的排查步骤。

**请勿粘贴 API Key、服务器地址、密码。** 需要展示配置时，把值替换成 `***`。
