# Assets

Logos, banners, icons, and other visual materials for Dream AI.

## Directory Structure

```
assets/
├── brand/                 # 为网页与文档准备的成品图（可直接引用）
│   └── hero.svg           # README 首屏：透明底 + 动效标志
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
| README 首屏（含动效） | `brand/hero.svg` |
| App / software icon | `logo/01_软件图标_圆角底板/` |
| Transparent planet mark | `logo/02_纯星球符号_透明底/` |
| Brand lockup (with text) | `logo/03_组合标_含字标/` |
| SVG vector source | `logo/04_矢量源_SVG/` |
| Favicon | `logo/06_favicon/` |
| Full documentation | `logo/README-文件清单与使用指南.md` |

## `brand/hero.svg`

README 顶部的首屏图。**透明背景**，因此在 GitHub 深色与浅色主题下都不会出现白色色块
（`logo/03_组合标_含字标/` 里的组合标是白底 PNG，只适合放在白底文档中）。

动效共五层，全部为 CSS 与 SMIL 声明式动画，不依赖脚本；系统开启「减少动态效果」时
（`prefers-reduced-motion: reduce`）除星点外的位移动画会停止：

| 层 | 效果 | 周期 |
|---|---|---|
| 光晕 | 紫色径向渐变呼吸缩放 | 6 s |
| 外层轨道 | 虚线椭圆顺时针旋转，带沿轨道运行的光点 | 64 s / 13 s |
| 内层轨道 | 更淡的虚线椭圆逆时针旋转 | 96 s |
| 主体 | 整体上下轻微浮动 | 7 s |
| 星点 | 四角星交错闪烁 | 2.6–3.8 s |

组成部分与生成方式：

1. 星球主体取自 `logo/02_纯星球符号_透明底/DreamAI-mark-1024-透明底.png`，
   按 alpha 边界裁切、留 10px 边距后缩放到 480px 宽，再以 base64 内嵌进 SVG，
   因此该文件可单独复制使用，不依赖仓库内其它图片。
2. 光晕、轨道、星点均为矢量，颜色取自品牌渐变色值（`#5eead4` → `#7c9cff` → `#c0a8ff`）。

替换品牌图形后需要重新生成：用 Pillow 对新的透明底 PNG 做同样的裁切与缩放，
替换 `<image>` 的 `xlink:href` 即可，其余动画无需改动。

## Notes

- All logo assets are based on the approved master design in `00_原始母版/`.
- PSD files are large design source files; they are kept here for brand asset management.
- Copyright © 2026 Li Guijiang. All rights reserved. See `logo/07_版权与说明/` for full license.
