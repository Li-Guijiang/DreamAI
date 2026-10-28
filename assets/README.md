# Assets

Logos, banners, icons, and other visual materials for Dream AI.

## Directory Structure

```
assets/
├── brand/                 # 为网页与文档准备的成品图（可直接引用）
│   ├── hero.gif           # README 首屏：8 秒循环的动效标志
│   └── hero.svg           # 同一首屏的矢量源文件（透明底，供编辑与二次导出）
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
| README 首屏（动效） | `brand/hero.gif` |
| 首屏矢量源（可编辑 / 高清导出） | `brand/hero.svg` |
| App / software icon | `logo/01_软件图标_圆角底板/` |
| Transparent planet mark | `logo/02_纯星球符号_透明底/` |
| Brand lockup (with text) | `logo/03_组合标_含字标/` |
| SVG vector source | `logo/04_矢量源_SVG/` |
| Favicon | `logo/06_favicon/` |
| Full documentation | `logo/README-文件清单与使用指南.md` |

## `brand/hero.gif` 与 `brand/hero.svg`

README 顶部使用 **`hero.gif`**：400×214、24 帧、8 秒循环、527 KB，仓库内相对路径引用。
GIF 是 GitHub README 里唯一能稳定播放动画的形式；矢量版 `hero.svg` 保留为源文件，
需要改颜色、改尺寸或导出高清图时用它。

两个文件都基于同一份设计：星球主体取自
`logo/02_纯星球符号_透明底/DreamAI-mark-1024-透明底.png`，光晕、轨道、星点为矢量，
动画周期全部整除 8 秒，循环无缝。

| 层 | 效果 | 周期 |
|---|---|---|
| 光晕 | 紫色径向渐变呼吸缩放 | 8 s |
| 外层轨道 | 虚线沿轨道流动，另有光点绕行 | 8 s |
| 内层轨道 | 更淡的虚线反向流动 | 8 s |
| 主体 | 整体上下浮动 7 px | 8 s |
| 星点 | 四角星交错闪烁 | 2 s / 4 s |

### 为什么动效用 GIF 而不是 SVG

1. 仓库内的 `.svg` 能正常显示，但其中声明的 CSS/SMIL 动画不会被播放：同一浏览器会话
   间隔 4 秒的两张截图逐像素一致，而同一文件在普通网页里以 `<img>` 引用时是会动的。
   也就是说，这不是 SVG 写错，而是渲染环境不播放。
2. GIF 会把底色烘进画面。这里用的是 GitHub 深色主题的 `#0d1117`，所以在浅色主题下
   首屏呈现为一块深色横幅，而不是与页面完全融合。透明 GIF 只支持 1 位透明度，
   光晕与轨道虚线会出现硬边，两种主题下都更差，因此没有采用。

### 已知限制

`assets/brand/hero.gif` 使用的是仓库相对路径。GitHub 对二进制文件会重定向到
`raw.githubusercontent.com` 取内容，该域名在部分网络（含国内）可能较慢甚至不可达；
若首屏偶发空白，通常是这个原因，与文件本身无关（本地用浏览器打开同一文件可正常显示）。

需要完全消除这一依赖时，把 GIF 上传到自有域名（例如
`https://liguijiang.com/assets/img/hero.gif`）并把 README 首屏改成该地址即可。

### 重新生成

1. 用 Pillow 把 `logo/02_纯星球符号_透明底/DreamAI-mark-1024-透明底.png` 按 alpha
   边界裁切、留 10 px 边距、缩放到 480 px 宽。
2. 以 base64 替换 `hero.svg` 中 `<image>` 的 `xlink:href`，其余动画参数不用改。
3. 用无头浏览器暂停动画、按时间步进逐帧导出，合成 400×214、8 秒、24 帧的 GIF，
   背景填 `#0d1117`。

## Notes

- All logo assets are based on the approved master design in `00_原始母版/`.
- PSD files are large design source files; they are kept here for brand asset management.
- Copyright © 2026 Li Guijiang. All rights reserved. See `logo/07_版权与说明/` for full license.
