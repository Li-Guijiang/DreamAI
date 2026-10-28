# Dream AI 文档索引

本目录集中存放项目文档。仓库同时提供三种可运行形态（命令行、Web 服务、Windows 桌面端），
本文说明每份文档解决什么问题、应当按什么顺序阅读，以及版本号与目录的对应关系。

---

## 1. 文档地图

| 文档 | 内容 | 适合谁 |
|---|---|---|
| [../README.md](../README.md) | 项目定位、能力清单、快速开始、整体目录结构 | 首次访问仓库的所有人 |
| [GUIDE.md](./GUIDE.md) | 中文上手手册：环境准备、命令逐条讲解、常见报错处理 | 第一次运行本项目的使用者 |
| [SETUP.md](./SETUP.md) | 本地安装步骤（Windows 为主，附 macOS / Linux 差异） | 需要在本地跑起来的使用者 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 分层设计、模块职责、一次对话与一次自主任务的完整数据流 | 需要读代码或扩展功能的开发者 |
| [ROADMAP.md](./ROADMAP.md) | 分阶段路线图、每阶段任务与验收标准 | 想了解进度与后续计划的人 |
| [adr/](./adr/) | 架构决策记录（ADR）：决定了什么、为什么、否决了哪些方案 | 需要理解设计取舍的开发者 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 分支约定、提交信息格式、代码风格、PR 检查清单 | 贡献者 |
| [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) | 社区行为准则 | 所有参与者 |
| [SECURITY.md](./SECURITY.md) | 漏洞报告渠道与安全边界 | 安全研究者、部署者 |
| [PRICING.md](./PRICING.md) | 未来可选托管方案的设想（当前均未提供） | 关注商业化方向的人 |
| [../CHANGELOG.md](../CHANGELOG.md) | 按版本记录的变更历史（Keep a Changelog 格式） | 升级或排查回归的人 |
| [../web/README.md](../web/README.md) | Web 版功能、接口、部署与运维 | Web 部署与维护者 |
| [../desktop/README.md](../desktop/README.md) | 桌面端开发、打包、测试与安全模型 | 桌面端开发与维护者 |
| [../assets/README.md](../assets/README.md) | 品牌资源目录与取用指引 | 设计、宣传物料制作 |

---

## 2. 三种运行形态的入口

1. **命令行（Python 包）**：`pip install -e .` 后执行 `python -m dream_ai` 或 `dream-ai`。
   配置项见根目录 [.env.example](../.env.example)，说明见 [GUIDE.md](./GUIDE.md)。
2. **Web 服务（FastAPI）**：进入 `web/` 目录，按 [web/README.md](../web/README.md) 安装依赖并启动。
   配置项见 `web/.env.example`。
3. **Windows 桌面端（Electron）**：进入 `desktop/` 目录，`pnpm install` 后 `pnpm start`。
   构建安装包见 [desktop/README.md](../desktop/README.md)。

三者共用同一套界面与后端约定，但**版本号各自独立**，见下一节。

---

## 3. 版本号对照

仓库内存在三个独立发布的产物，版本号不同属于预期行为，并非遗漏：

| 产物 | 版本来源 | 当前版本 | 说明 |
|---|---|---|---|
| 命令行包 `dream-ai` | `pyproject.toml` → `[project].version` | `0.4.0` | 与服务端包语义化版本一致，发布到 GitHub Releases |
| Web 服务 | `web/app/config.py` → `VERSION` | `1.4.0` | 站点迭代以自己的节奏推进，通过 `/api/config` 下发 |
| Windows 桌面端 | `desktop/package.json` → `version` | `1.2.0` | 安装包文件名 `DreamAI-Setup-<version>.exe` |

修改任一版本号时，请同步检查：

1. `CHANGELOG.md` 是否有对应条目；
2. `web/web/index.html` 中静态资源 `?v=` 查询串是否需要同步更新（用于刷新浏览器缓存）；
3. `web/web/downloads/latest.json` 的版本、文件名、大小与校验和是否与安装包一致。

---

## 4. 文档维护约定

1. 新增文档放入本目录，并在第 1 节的表格中登记，避免出现"仓库里有、索引里没有"的孤立文件。
2. 面向使用者的操作步骤使用有序列表，命令统一放在代码块中。
3. 涉及配置项时，同时更新对应的 `.env.example`，保证文档与代码读取的变量名一致。
4. 架构层面的取舍记录到 `adr/`，按 `0001-<topic>.md` 递增编号，不要改写已生效的旧记录。
5. 文档中的相对链接使用仓库内路径，避免指向个人站点或临时地址。
