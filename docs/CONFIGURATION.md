# 服务端配置说明

本文列出 Web 服务读取的全部 `DREAMAI_*` 环境变量。它们由
`web/app/config.py` 的 `load_settings()` 解析，启动即固定，修改后须重启服务。
命令行版本的配置见 [SETUP.md](./SETUP.md)，其中 `DREAMAI_API_KEY`、
`DREAMAI_MODEL` 等变量属于本地客户端，与本文的 Web 服务端变量不是同一套。

未设置时均使用表中默认值。数值经过上下限裁剪，超限不会报错而是取边界值。
启动时的建议项显示在 `/api/health.configChecks` 与启动日志中。

`web/tools/check_env_docs.py` 检查本文是否覆盖代码里的每一个配置项，
避免新增配置后文档漏写。

## 1. 核心模型与输出

| 变量 | 默认值 | 作用 | 约束 |
|---|---|---|---|
| `DREAMAI_TEMPERATURE` | `0.7` | 默认采样温度；仅温度不高于 0.3 的请求会查答案缓存 | 裁剪到 0～2；请求可覆盖 |
| `DREAMAI_MAX_TOKENS` | `4096` | 单次生成的上限 | 最小 256 |
| `DREAMAI_TOP_P` | 未设置 | 核采样参数；设置后参与缓存键 | 合法浮点数，未设置时不发送该参数 |
| `DREAMAI_PRESENCE_PENALTY` | 未设置 | 重复内容惩罚；设置后参与缓存键 | 合法浮点数，未设置时不发送该参数 |
| `DREAMAI_SYSTEM_PROMPT` | 内置人格文本 | 追加到所有请求前的系统提示 | 不写入日志与公开配置 |
| `DREAMAI_STREAM_USAGE` | `true` | 是否请求上游在流末返回 token 用量 | 关闭后 token 与成本统计不可用 |
| `DREAMAI_PROMPT_CACHE` | `true` | 是否向上游发送提示词缓存标记 | 供应商不支持时会自动忽略 |
