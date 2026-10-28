# Web 维护脚本

本目录存放 Web 服务相关的**本地维护脚本**，不属于线上运行时，服务器部署也不需要它们。
脚本以仓库内的相对路径为基准，运行环境基于 `web/requirements.txt`（部分脚本额外需要
`pillow`、`numpy`、`paramiko`、`requests`）。

## 1. 保留在根目录的脚本

| 脚本 | 用途 | 何时使用 |
|---|---|---|
| `make_assets.py` | 从品牌资产生成站点图标（favicon、PWA 图标、社交分享图） | 更换品牌图形后重新生成 `web/assets/img/` |
| `make_og.py` | 单独重新生成 1200×630 社交分享卡 `web/assets/img/og.png` | 调整站点标语或分享卡版式 |
| `mock_upstream.py` | 本地模拟一个 OpenAI 兼容的流式接口 | 没有 API Key 时调试界面与流式渲染 |
| `server_exec.py` | 通用 SSH 助手（`exec` / `put` / `get` / `shell`） | 需要临时在服务器执行命令或传输文件 |

用法示例：

```bash
# 用 Mock 模型启动本地前端
.venv/bin/uvicorn mock_upstream:app --app-dir tools --port 8799

# 重新生成品牌图标
python tools/make_assets.py

# 远程执行一段脚本（密码来自环境变量，不落盘）
export DREAMAI_SSH_PASSWORD=...
python tools/server_exec.py exec ./some-script.sh
```

## 2. `archive/` 目录

`archive/` 保存**一次性运维与诊断脚本**：发布某一版本时写的一次性上传脚本、排查
nginx 与静态资源时写的 `fix_*` / `check_*` / `test_*` 脚本等。

这些脚本的共同特征：

1. 内含写死的主机地址、服务器绝对路径或本机 `D:\...` 路径，换机器即失效；
2. 面向某一个具体版本（例如 `deploy_v12.py`），版本推进后不再复用；
3. 只输出诊断信息，不参与构建、测试或部署流水线。

保留它们的原因是可追溯：需要回看某次发布做了什么改动时，脚本本身就是记录。
**它们不保证可运行，也不要在生产环境直接执行。**

新增脚本的归档约定：

1. 一次性脚本直接放进 `archive/`，命名以 `check_` / `fix_` / `push_` / `test_` 开头；
2. 需要长期复用的脚本留在本目录根下，并在上表登记；
3. 新脚本不要写入本机绝对路径，统一用
   `ROOT = Path(__file__).resolve().parent.parent` 推导；
4. 涉及密钥的脚本只从环境变量读取，不要写进源码或示例。
