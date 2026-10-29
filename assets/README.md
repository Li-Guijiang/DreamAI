# Assets

<p align="center"><img src="https://github.com/user-attachments/assets/de9a940f-8d02-4cce-9da8-2b1cecd8d1d7" alt="Animated Dream AI brand banner" width="720"></p>

Logos, banners, icons, and other visual materials for Dream AI.

> **README images live elsewhere.** GitHub's repository-relative image CDN
> (`raw.githubusercontent.com`) is unreachable on some networks, so Markdown
> illustrations use GitHub user attachments. The source-of-truth mapping and
> regeneration notes live in [`readme/`](readme/README.md). Local originals
> still live under `brand/` and `logo/`.

## Directory Structure

```
assets/
├── brand/                 # Deliverables ready to be referenced directly
│   ├── build_hero.py      # Generator for the README hero (run it, do not hand-edit)
│   ├── hero.svg           # README hero: transparent vector mark with animation
│   ├── hero.gif           # Same hero as raster frames, for sites / slides
│   ├── banner-*.gif       # Animated page banners (docs / web / desktop / assets)
│   └── build_banners.py   # Generator for the banners
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
| README hero (renders on any network) | `brand/hero.svg` |
| Animated raster version (site / slides) | `brand/hero.gif` |
| App / software icon | `logo/01_软件图标_圆角底板/` |
| Transparent planet mark | `logo/02_纯星球符号_透明底/` |
| Brand lockup (with text) | `logo/03_组合标_含字标/` |
| SVG vector source | `logo/04_矢量源_SVG/` |
| Favicon | `logo/06_favicon/` |
| Full documentation | `logo/README-文件清单与使用指南.md` |

## `brand/hero.svg` and `brand/hero.gif`

The README opens with **`hero.svg`**: transparent background, so it never shows a white block
on the dark theme (the lockup in `logo/03_组合标_含字标/` is a white-background PNG and only
suits light documents). It is about 112 KB and served as text by github.com, so it renders on
any network.

`hero.gif` is the same design as raster frames (400×214, 24 frames, 8-second loop, 527 KB).
The README does not reference it; it is there for the website, slides, demo packages, or for
replacing the hero once it is hosted on our own domain.

Both files come from the same artwork. The planet is
`logo/02_纯星球符号_透明底/DreamAI-mark-1024-透明底.png`; the nebulae, orbits, companion planet,
moon, comet, and starfield are vectors. Every animation period divides 8 seconds, so the loop
is seamless.

| Layer | Effect | Period |
|---|---|---|
| Nebulae | Three soft washes drifting and breathing on opposite phases | 8 s |
| Milky way | Blurred diagonal band with 120 dust stars | 8 s |
| Starfield | 165 stars in four colours, about 60% twinkling | 2 s / 4 s |
| Orbits | Three dashed ellipses flowing in alternating directions | 8 s |
| Main planet | Floats 7 px up and down | 8 s |
| Companion planet | Floats on an offset phase, with rim light and a dashed ring | 8 s |
| Comet | Sweeps along an arc with a tapered tail, then fades | 8 s |

### Why the README uses SVG rather than GIF

1. **SVG animation does not play inside a GitHub README.** Two screenshots taken four seconds
   apart in the same browser session are pixel-identical, while the same file referenced by an
   `<img>` on an ordinary page animates. The renderer does not play it; the file is fine.
2. **GIF plays, but costs twice.** Its 256-colour palette puts visible noise into the planet
   gradient, and GitHub serves binary files through `raw.githubusercontent.com`, which is often
   slow or unreachable from some networks — the hero can end up blank.
3. So the hero prioritises "always visible, always crisp". The animation lives in the SVG: open
   `brand/hero.svg` directly in a browser to see the full effect.

### Enabling motion in the README

Upload `hero.gif` to our own domain (for example `https://liguijiang.com/assets/img/hero.gif`)
and point the hero line at that URL. A self-hosted domain is fast everywhere, and the GIF will
play. Note that the GIF bakes in the GitHub dark background `#0d1117`, so on the light theme it
appears as a dark banner.

### Regenerating

1. `python assets/brand/build_hero.py` rewrites `hero.svg` from the brand mark. Layout constants
   at the top of the script control planet size and position, orbits, and star count.
2. For the GIF: pause the animations in an inlined copy of the SVG, step `currentTime` frame by
   frame through an 8-second loop, and encode 400×214 at 24 frames with `#0d1117` as the
   background.

## `brand/banner-*.gif`

Four animated strips, one per document family, placed directly under the page title:

| File | Used by | Motion |
|---|---|---|
| `banner-docs.gif` | `docs/` and every page inside it | Three glowing ribbons drifting on opposite phases, a starfield, a tapered comet |
| `banner-web.gif` | `web/README.md`, `web/tools/README.md` | Concentric orbit rings with rotating highlights and travelling light points |
| `banner-desktop.gif` | `desktop/README.md` | Pulsing dot grid with a soft light sweep |
| `banner-assets.gif` | `assets/README.md` | The same ribbons and stars in the warm brand palette |

All four are 760×132, 80 frames over an 8-second loop at 10 fps with a 96-colour palette, so the
motion reads as continuous rather than stepped. Sizes are 178–371 KB. Regenerate with:

```bash
python assets/brand/build_banners.py          # all four
python assets/brand/build_banners.py web      # just one
```

Each page loads a single banner (118–336 KB). If a lighter page matters more than motion, remove the
`<img>` line under the title and the rest of the page is unaffected.

## Notes

- All logo assets are based on the approved master design in `00_原始母版/`.
- PSD files are large design source files; they are kept here for brand asset management.
- Copyright © 2026 Li Guijiang. All rights reserved. See `logo/07_版权与说明/` for full license.
