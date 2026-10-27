# Dream AI Desktop

Dream AI 的 Windows 桌面版：Electron 外壳加载官网同一套界面，并通过安全的 IPC 桥接提供
**本地文件工作台**与**文档生成**。

## 能做什么

| 能力 | 说明 |
| --- | --- |
| 文档生成 | 一句话生成 Word（.docx）、Excel（.xlsx）、PPT（.pptx）、PDF、Markdown，保存到工作文件夹 |
| 按类型整理 | 图片 / 文档 / 视频 / 音频 / 压缩包 / 安装包 / 代码 / 其他 |
| 批量重命名 | 统一前缀 + 序号，保留扩展名，预览新旧对照 |
| 保存对话 | 将当前会话导出为 Markdown |
| 文件夹概览 | 文件数、文件夹数、总大小、类型分布 |

文档全部用纯 JS 生成，**不需要本机安装 Office**。PDF 由 Electron `printToPDF` 渲染，
中文使用系统字体。

## 开发

```bash
cd desktop
pnpm install
pnpm start            # 默认加载 https://liguijiang.com

# 本地调试（配合 dreamai-web 的 uvicorn）
DREAMAI_URL=http://127.0.0.1:8787 pnpm start
```

镜像：

```bash
ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
ELECTRON_BUILDER_BINARIES_MIRROR=https://npmmirror.com/mirrors/electron-builder-binaries/
```

## 打包

```bash
pnpm dist
# 产物：release/DreamAI-Setup-1.1.0.exe
```

## 测试

```bash
node test/local-tools.test.js   # 文件整理 / 重命名 / 路径约束
node test/documents.test.js     # DOCX / XLSX / PPTX / Markdown 生成
```

Electron 端到端（需先启动本地 Web）：

```bash
electron --remote-debugging-port=9227 .
DREAMAI_DEV_WORKSPACE=<测试文件夹> node test/doc-e2e.js
```

调试环境变量：

| 变量 | 作用 |
| --- | --- |
| `DREAMAI_URL` | 覆盖加载的站点地址 |
| `DREAMAI_DEV_WORKSPACE` | 启动时预选工作文件夹 |
| `DREAMAI_DEV_AUTO_CONFIRM=1` | 自动通过写操作确认框，仅自动化测试 |

## 安全模型

- `contextIsolation: true`、`nodeIntegration: false`、`sandbox: true`
- 预加载脚本只暴露固定 IPC 方法，不暴露 `fs` / `child_process`
- 只能访问用户通过系统对话框选择的文件夹，路径做包含校验
- 文档只能写入 `<工作文件夹>/Dream AI 文档`
- 每次移动 / 重命名 / 写入都先预览，再由主进程弹原生确认框
- 禁止页面导航离开官网域名，外部链接交给系统浏览器
