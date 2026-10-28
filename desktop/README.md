# Dream AI Desktop

Dream AI 的 Windows 桌面版：一个 Electron 外壳，加载官网同一套界面，并通过安全的
IPC 桥接提供**本地文件工作台**（整理、批量重命名、保存文档）。

## 开发

```bash
cd desktop
pnpm install          # 需要 ELECTRON_MIRROR 时见下方
pnpm start            # 默认加载 https://liguijiang.com

# 本地调试（配合 dreamai-web 的 uvicorn），等价于 electron . --url=http://127.0.0.1:8787
pnpm start:local
```

镜像（国内）：

```bash
ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
ELECTRON_BUILDER_BINARIES_MIRROR=https://npmmirror.com/mirrors/electron-builder-binaries/
```

## 打包

```bash
pnpm dist
# 产物：release/DreamAI-Setup-1.2.0.exe
```

打包图标固定读取 `build/icon.ico`（含 16–256 多尺寸），由品牌资产
`assets/logo/DreamAI-Logo/01_软件图标_圆角底板/DreamAI-icon-1024.png` 导出，
输出目录与资源目录由 `package.json` 的 `build.directories` 指定。替换图标时保持文件名不变。

## 测试

```bash
pnpm test            # 依次执行下面两个脚本，需先 pnpm install
pnpm test:tools      # 纯 Node，测试文件整理/重命名/路径约束
pnpm test:docs       # 文档生成（docx / xlsx / pptx），依赖 docx、exceljs、pptxgenjs
```

Electron 端到端（需要先启动本地 Web）：

```bash
# 启动后额外开放调试端口
electron --remote-debugging-port=9222 . --url=http://127.0.0.1:8787
# 另一个终端
DREAMAI_DEV_WORKSPACE=<测试文件夹> node test/e2e.js
```

调试用参数与环境变量（仅本地）：

| 参数 / 变量 | 作用 |
| --- | --- |
| `--url=<地址>` | 覆盖加载的站点地址，优先级高于 `DREAMAI_URL` |
| `DREAMAI_URL` | 覆盖加载的站点地址 |
| `DREAMAI_DEV_WORKSPACE` | 启动时预选工作文件夹，跳过系统选择框 |
| `DREAMAI_DEV_AUTO_CONFIRM=1` | 自动通过写操作确认框，仅用于自动化测试 |

## 安全模型

- `contextIsolation: true`、`nodeIntegration: false`、`sandbox: true`
- 预加载脚本只暴露固定 IPC 方法，不暴露 `fs` / `child_process`
- 只能访问用户通过系统对话框选择的文件夹，路径做包含校验
- 忽略符号链接与隐藏文件
- 每次移动 / 重命名 / 写入都先预览，再由主进程弹原生确认框
- 禁止页面导航离开官网域名，外部链接交给系统浏览器

## 本地能力（MVP）

| 能力 | 说明 |
| --- | --- |
| 按类型整理 | 图片 / 文档 / 视频 / 音频 / 压缩包 / 安装包 / 代码 / 其他 |
| 批量重命名 | 统一前缀 + 序号，保留扩展名，预览新旧对照 |
| 保存对话 | 将当前会话导出为 Markdown 到工作文件夹 |
| 文件夹概览 | 文件数、文件夹数、总大小、类型分布 |

后续可以按同样模式扩展：Word/Excel/PPT 生成、图片压缩、重复文件检测、定时整理等。
