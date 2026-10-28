# Assets

Logos, banners, icons, and other visual materials for Dream AI.

## Directory Structure

```
assets/
├── brand/                 # 为网页与文档准备的成品图（可直接引用）
│   ├── hero.gif           # README 首屏：动效标志（GitHub 上唯一会播放的格式）
│   └── hero.svg           # 同一首屏的矢量源文件（透明底，供编辑与二次使用）
└── logo/                  # DreamAI brand logo assets
    ├── 00_原始母版/        # Master design files (visual baseline)
    ├── 01_软件图标_圆角底板/  # App icons (rounded square, iOS style)
    ├── 02_纯星球符号_透明底/  # Planet mark (transparent background)
    ├── 03_组合标_含字标/     # Lockup (planet + "DreamAI" wordmark)
    ├── 04_矢量源_SVG/       # SVG vector source files
    ├── 05_PSD分层源文件/     # Photoshop layered source files
    ├── 06_favicon/         # Website favicon and icons
    ├── 07_版权与说明/       # Copyright and usage guidelines
    └── README-文件清单与使用指南.md  # Full file inventory and usage guide
```

## Quick Reference

| Use Case | File Location |
|----------|--------------|
| README 首屏（会播放） | `brand/hero.gif` |
| 首屏矢量源（可编辑） | `brand/hero.svg` |
| App / software icon | `logo/01_软件图标_圆角底板/` |
| Transparent planet mark | `logo/02_纯星球符号_透明底/` |
| Brand lockup (with text) | `logo/03_组合标_含字标/` |
| SVG vector source | `logo/04_矢量源_SVG/` |
| Favicon | `logo/06_favicon/` |
| Full documentation | `logo/README-文件清单与使用指南.md` |

## `brand/hero.gif` 与 `brand/hero.svg`

README 顶部的首屏由同一次设计导出两种格式，用途不同：

| 文件 | 角色 | 说明 |
|---|---|---|
| `hero.gif` | README 实际引用 | 400×214，24 帧 / 8 秒循环，527 KB。**唯一在 GitHub README 里会播放的形式** |
| `hero.svg` | 源文件 | 560×300 矢量，透明底，动画用 CSS + SMIL 声明；GitHub 会把它当静态图渲染，适合直接打开或二次编辑 |

### 为什么不能只用 SVG

实测结论（2026-10，GitHub 网页端）：

1. 仓库内的 `.svg` 能被正确服务（`image/svg+xml`，`<style>` 与 `@keyframes` 都在），
   但页面上不播放——同一会话间隔 4 秒的两张截图逐像素一致。
2. 仓库内相对路径的 `.webp` 完全不显示（`naturalWidth` 为 0，元素高度为 0）。
3. `.gif` 通过仓库相对路径引用同样不显示；改用
   `raw.githubusercontent.com` 的绝对地址后正常显示，并且确认在播放
   （两帧之间首屏区域有 7.7 万像素变化，标题与正文区域完全不变）。

因此 README 里的 `hero.gif` 用的是绝对地址。副作用是：仓库改名、默认分支改名或
fork 之后需要同步改这一行 URL。

### 动效构成

所有周期都整除 8 秒，循环无缝：

| 层 | 效果 | 周期 |
|---|---|---|
| 光晕 | 紫色径向渐变呼吸缩放 | 8 s |
| 外层轨道 | 虚线沿轨道流动，另有光点绕行 | 8 s |
| 内层轨道 | 更淡的虚线反向流动 | 8 s |
| 主体 | 整体上下浮动 7 px | 8 s |
| 星点 | 四角星交错闪烁 | 2 s / 4 s |

### 已知取舍

GIF 把 GitHub 深色主题的背景色 `#0d1117` 烤进了画面，因此在浅色主题下首屏是一块深色
横幅，而不是与页面融合。透明 GIF 只能用 1 位透明度，光晕与轨道虚线会出现硬边，
两种主题下都更差，所以选择了前者。

### 重新生成

1. 用 Pillow 把 `logo/02_纯星球符号_透明底/DreamAI-mark-1024-透明底.png` 按 alpha
   边界裁切、留 10 px 边距、缩放到 480 px 宽。
2. 以 base64 替换 `hero.svg` 中 `<image>` 的 `xlink:href`，其余动画参数不用改。
3. 用无头浏览器把 `<g class="float">` 之外的动画逐帧导出（暂停动画后按时间步进），
   合成 400×214、8 秒、24 帧的 GIF；背景填 `#0d1117`。

## Notes

- All logo assets are based on the approved master design in `00_原始母版/`.
- PSD files are large design source files; they are kept here for brand asset management.
- Copyright © 2026 Li Guijiang. All rights reserved. See `logo/07_版权与说明/` for full license.
