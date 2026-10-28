# Assets

Logos, banners, icons, and other visual materials for Dream AI.

## Directory Structure

```
assets/
├── brand/                 # 为网页与文档准备的成品图（可直接引用）
│   ├── hero.svg           # README 首屏：透明底矢量标志（动效以 CSS/SMIL 声明）
│   └── hero.gif           # 同一首屏的动效栅格版，供官网 / PPT / 演示使用
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
| README 首屏（任何网络可显示） | `brand/hero.svg` |
| 动效栅格版（官网 / PPT / 演示） | `brand/hero.gif` |
| App / software icon | `logo/01_软件图标_圆角底板/` |
| Transparent planet mark | `logo/02_纯星球符号_透明底/` |
| Brand lockup (with text) | `logo/03_组合标_含字标/` |
| SVG vector source | `logo/04_矢量源_SVG/` |
| Favicon | `logo/06_favicon/` |
| Full documentation | `logo/README-文件清单与使用指南.md` |

## `brand/hero.svg` 与 `brand/hero.gif`

README 顶部使用 **`hero.svg`**：透明背景，在 GitHub 深色与浅色主题下都不会出现白色色块
（`logo/03_组合标_含字标/` 里的组合标是白底 PNG，只适合放在白底文档中）。172 KB，
由 github.com 直接返回，任何网络下都能显示。

`hero.gif` 是同一套动效的栅格版本（400×214、24 帧、8 秒循环、527 KB），README 未引用，
留给官网、PPT、演示包等会播放 GIF 的场合，或上传到自有域名后替代首屏。

两个文件基于同一份设计：星球主体取自
`logo/02_纯星球符号_透明底/DreamAI-mark-1024-透明底.png`，光晕、轨道、星点为矢量，
动画周期全部整除 8 秒，循环无缝。

| 层 | 效果 | 周期 |
|---|---|---|
| 光晕 | 紫色径向渐变呼吸缩放 | 8 s |
| 外层轨道 | 虚线沿轨道流动，另有光点绕行 | 8 s |
| 内层轨道 | 更淡的虚线反向流动 | 8 s |
| 主体 | 整体上下浮动 7 px | 8 s |
| 星点 | 四角星交错闪烁 | 2 s / 4 s |

### 为什么 README 用 SVG 而不是 GIF

1. **SVG 的动画在 GitHub README 里不播**：同一浏览器会话间隔 4 秒的两张截图逐像素一致，
   而同一文件在普通网页里以 `<img>` 引用时是会动的。渲染环境不播放，不是文件写错。
2. **GIF 能播，但代价明显**：256 色让星球渐变出现噪点；且 GitHub 对二进制文件会重定向到
   `raw.githubusercontent.com`，该域名在部分网络（含国内）经常很慢或不可达，首屏可能直接空白。
3. 因此首屏优先保证「一定显示、一定清晰」；动效放在 SVG 源文件里，直接用浏览器打开
   `assets/brand/hero.svg` 即可看到完整效果。

### 想在 README 里放动效时

把 `hero.gif` 上传到自有域名（例如 `https://liguijiang.com/assets/img/hero.gif`），
再把 README 首屏那一行改成该地址。自有域名在国内访问稳定，GIF 也会正常播放。
注意 GIF 已经把 GitHub 深色底 `#0d1117` 烘进画面，浅色主题下会是一块深色横幅。

### 重新生成

1. 用 Pillow 把 `logo/02_纯星球符号_透明底/DreamAI-mark-1024-透明底.png` 按 alpha
   边界裁切、留 10 px 边距、缩放到 480 px 宽。
2. 以 base64 替换 `hero.svg` 中 `<image>` 的 `xlink:href`，其余动画参数不用改。
3. 如需 GIF：用无头浏览器暂停动画后按时间步进逐帧导出，合成 400×214、8 秒、24 帧，
   背景填 `#0d1117`。

## Notes

- All logo assets are based on the approved master design in `00_原始母版/`.
- PSD files are large design source files; they are kept here for brand asset management.
- Copyright © 2026 Li Guijiang. All rights reserved. See `logo/07_版权与说明/` for full license.
