"""Generate the README hero, assets/brand/hero.svg.

Usage (from the repository root):

    python assets/brand/build_hero.py

The output is a self-contained SVG: the brand planet is embedded as base64, while
the starfield, nebulae, orbits, companion planet, and comet are vectors. Every
animation period divides 8 seconds, so the loop is seamless, and
`prefers-reduced-motion` stops the movement.

Edit the layout constants below and re-run this script instead of hand-editing
hero.svg.
"""

from __future__ import annotations

import base64
import io
import random
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MARK_SRC = ROOT / "assets/logo/DreamAI-Logo/02_纯星球符号_透明底/DreamAI-mark-1024-透明底.png"
OUT = Path(__file__).resolve().parent / "hero.svg"

# --- Layout -----------------------------------------------------------------
W, H = 1000, 340
MARK_W = 330                      # main planet width
MARK_X, MARK_Y = 150, 58          # main planet, top-left corner
PLANET2 = (790, 104, 44)          # companion planet: cx, cy, radius
MOON = (636, 258, 12)             # moon
ORBITS = [                        # orbits around the main planet: rx, ry, rotation, opacity, dash
    (368, 108, -14, 0.40, "5 12"),
    (312, 92, 9, 0.26, "3 14"),
    (262, 76, -3, 0.16, "2 16"),
]
STAR_COUNT = 165
LOOP = 8                          # seconds; every animation period must divide it

random.seed(20261028)


def _mark_base64(width: int) -> str:
    """Crop the transparent brand mark, scale it, and encode it as base64."""
    src = Image.open(MARK_SRC).convert("RGBA")
    bbox = src.getchannel("A").getbbox()
    pad = 10
    box = (
        max(0, bbox[0] - pad),
        max(0, bbox[1] - pad),
        min(src.width, bbox[2] + pad),
        min(src.height, bbox[3] + pad),
    )
    cropped = src.crop(box)
    height = round(cropped.height * width / cropped.width)
    cropped = cropped.resize((width, height), Image.LANCZOS)
    buffer = io.BytesIO()
    cropped.save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode(), height


def _stars(layer: str = "all") -> str:
    """Draw the starfield: four colours, about 60% twinkling on staggered delays.

    ``layer`` splits the field into two parallax groups so the near stars drift
    further than the far ones, which reads as depth while the loop runs.
    """
    palette = [
        ("#ffffff", 0.9),
        ("#cfe0ff", 0.72),
        ("#a5f3fc", 0.62),
        ("#c4b5fd", 0.62),
    ]
    p2x, p2y, p2r = PLANET2
    out: list[str] = []
    for i in range(STAR_COUNT):
        x = round(random.uniform(10, W - 10), 1)
        y = round(random.uniform(8, H - 8), 1)
        if MARK_X - 16 < x < MARK_X + MARK_W + 40 and MARK_Y - 16 < y < MARK_Y + 230:
            continue
        if abs(x - p2x) < p2r + 26 and abs(y - p2y) < p2r + 26:
            continue
        r = round(random.choice([0.5, 0.7, 0.8, 1.0, 1.2, 1.5, 1.9]), 1)
        color, alpha = random.choice(palette)
        alpha = round(min(0.95, alpha * random.uniform(0.4, 1.0)), 2)
        if layer == "far" and i % 3 == 0:
            continue
        if layer == "near" and i % 3 != 0:
            continue
        if i % 5 < 3:
            dur = random.choice([2, 4])
            delay = round(-random.uniform(0, dur), 2)
            out.append(
                f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" opacity="{alpha}" '
                f'class="twinkle" style="animation-duration:{dur}s;animation-delay:{delay}s"/>'
            )
        else:
            out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" opacity="{alpha}"/>')
    return "\n    ".join(out)


def _milkyway() -> str:
    """Diagonal milky-way band: one soft wash plus dense dust stars."""
    dust: list[str] = []
    for _ in range(120):
        x = random.uniform(0, W)
        y = 168 + (x - W / 2) * 0.22 + random.gauss(0, 22)
        if not (0 < y < H):
            continue
        r = round(random.uniform(0.35, 1.0), 2)
        alpha = round(random.uniform(0.10, 0.5), 2)
        dust.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#dbeafe" opacity="{alpha}"/>'
        )
    dust_svg = "".join(dust)
    return (
        '<g class="drift-b">'
        f'<ellipse cx="{W // 2}" cy="170" rx="{W // 2 + 40}" ry="62" '
        'transform="rotate(-7 500 170)" fill="url(#milkyway)" filter="url(#soften)"/>'
        f"{dust_svg}</g>"
    )


def _sparkles() -> str:
    """Three four-point sparkles as visual anchors."""
    spots = [(268, 46, 9), (884, 40, 7), (60, 250, 6)]
    out = []
    for x, y, s in spots:
        out.append(
            f'<g transform="translate({x} {y})">'
            f'<path class="twinkle" style="animation-duration:4s;animation-delay:-1.2s" '
            f'd="M0,{-s} L{s * 0.22},{-s * 0.22} L{s},0 L{s * 0.22},{s * 0.22} '
            f'L0,{s} L{-s * 0.22},{s * 0.22} L{-s},0 L{-s * 0.22},{-s * 0.22} Z" '
            f'fill="#e8f0ff"/></g>'
        )
    return "".join(out)


def _constellation() -> str:
    """A few bright stars joined by thin lines, like a constellation chart."""
    points = [(46, 58), (128, 34), (196, 96), (92, 132), (28, 168)]
    lines = "".join(
        f'<line x1="{points[i][0]}" y1="{points[i][1]}" x2="{points[i + 1][0]}" y2="{points[i + 1][1]}"/>'
        for i in range(len(points) - 1)
    )
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="1.6"/>' for x, y in points)
    return f'<g class="constellation" stroke="#93c5fd" fill="#dbeafe">{lines}{dots}</g>'


def build() -> str:
    mark_b64, mark_h = _mark_base64(MARK_W)
    orbits = "\n    ".join(
        f'<ellipse class="{"flow" if i % 2 == 0 else "flow-rev"}" rx="{rx}" ry="{ry}" '
        f'transform="rotate({ang})" fill="none" stroke="url(#orbitGrad)" stroke-width="1" '
        f'stroke-dasharray="{dash}" stroke-linecap="round" opacity="{op}"/>'
        for i, (rx, ry, ang, op, dash) in enumerate(ORBITS)
    )
    p2x, p2y, p2r = PLANET2
    mx, my, mr = MOON

    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
  <title id="t">Dream AI</title>
  <desc id="d">Dream AI hero: a gradient planet at the centre of stacked orbits, surrounded by
  nebulae, star clusters, a companion planet, a moon, and a passing comet.</desc>

  <defs>
    <radialGradient id="nebulaViolet" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#8b7cff" stop-opacity="0.30"/>
      <stop offset="60%" stop-color="#6d5dfc" stop-opacity="0.10"/>
      <stop offset="100%" stop-color="#6d5dfc" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="nebulaTeal" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#5eead4" stop-opacity="0.22"/>
      <stop offset="70%" stop-color="#22d3ee" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="nebulaRose" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#f0a6c8" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="#f0a6c8" stop-opacity="0"/>
    </radialGradient>

    <filter id="soften" x="-25%" y="-60%" width="150%" height="220%">
      <feGaussianBlur stdDeviation="14"/>
    </filter>

    <linearGradient id="milkyway" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#6d5dfc" stop-opacity="0"/>
      <stop offset="28%" stop-color="#8b7cff" stop-opacity="0.16"/>
      <stop offset="55%" stop-color="#5eead4" stop-opacity="0.14"/>
      <stop offset="78%" stop-color="#c4b5fd" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#6d5dfc" stop-opacity="0"/>
    </linearGradient>

    <linearGradient id="orbitGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#5eead4" stop-opacity="0.9"/>
      <stop offset="50%" stop-color="#7c9cff" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#c0a8ff" stop-opacity="0.9"/>
    </linearGradient>

    <radialGradient id="planet2" cx="32%" cy="28%" r="78%">
      <stop offset="0%" stop-color="#7ee7d3"/>
      <stop offset="46%" stop-color="#5b8cff"/>
      <stop offset="100%" stop-color="#7c4ddb"/>
    </radialGradient>
    <radialGradient id="planet2Glow" cx="50%" cy="50%" r="50%">
      <stop offset="55%" stop-color="#7c9cff" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#7c9cff" stop-opacity="0"/>
    </radialGradient>

    <radialGradient id="cometGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#9fc4ff" stop-opacity="0"/>
    </radialGradient>

    <linearGradient id="cometTail" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#8b7cff" stop-opacity="0"/>
      <stop offset="70%" stop-color="#b9a7ff" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#eaf1ff" stop-opacity="0.95"/>
    </linearGradient>

    <style>
      .parallax-far  {{ animation: panFar {LOOP}s ease-in-out infinite; }}
      .parallax-near {{ animation: panNear {LOOP}s ease-in-out infinite; }}
      .breathe       {{ animation: breathe {LOOP}s ease-in-out infinite; transform-origin: 500px 170px; }}
      .drift-a {{ animation: driftA {LOOP}s ease-in-out infinite; transform-origin: 0 0; }}
      .drift-b {{ animation: driftB {LOOP}s ease-in-out infinite; transform-origin: 0 0; }}
      .float   {{ animation: float {LOOP}s ease-in-out infinite; }}
      .float-2 {{ animation: float {LOOP}s ease-in-out infinite; animation-delay: -2.6s; }}
      .flow     {{ animation: flow {LOOP}s linear infinite; }}
      .flow-rev {{ animation: flow {LOOP}s linear infinite reverse; }}
      .twinkle {{ animation: twinkle 4s ease-in-out infinite; transform-origin: 0 0; }}
      .constellation {{ opacity: 0.16; stroke-width: 0.8; fill-opacity: 0.8; }}

      @keyframes panFar {{
        0%, 100% {{ transform: translate(0, 0); }}
        50%      {{ transform: translate(-9px, 4px); }}
      }}
      @keyframes panNear {{
        0%, 100% {{ transform: translate(0, 0); }}
        50%      {{ transform: translate(15px, -7px); }}
      }}
      @keyframes breathe {{
        0%, 100% {{ transform: scale(1); }}
        50%      {{ transform: scale(1.04); }}
      }}
      @keyframes float {{
        0%, 100% {{ transform: translateY(0); }}
        50%      {{ transform: translateY(-7px); }}
      }}
      @keyframes flow {{
        from {{ stroke-dashoffset: 0; }}
        to   {{ stroke-dashoffset: -17; }}
      }}
      @keyframes driftA {{
        0%, 100% {{ transform: scale(1) translate(0, 0); opacity: 0.85; }}
        50%      {{ transform: scale(1.06) translate(6px, -4px); opacity: 1; }}
      }}
      @keyframes driftB {{
        0%, 100% {{ transform: scale(1.04) translate(0, 0); opacity: 0.9; }}
        50%      {{ transform: scale(0.97) translate(-8px, 5px); opacity: 0.7; }}
      }}
      @keyframes twinkle {{
        0%, 100% {{ opacity: 0.12; }}
        50%      {{ opacity: 0.95; }}
      }}

      @media (prefers-reduced-motion: reduce) {{
        .drift-a, .drift-b, .float, .float-2, .flow, .flow-rev, .twinkle,
        .parallax-far, .parallax-near, .breathe {{ animation: none; }}
      }}
    </style>
  </defs>

  <!-- Nebulae and milky way, slowly breathing as one backdrop -->
  <g class="breathe">
  <g transform="translate(300 168)"><ellipse class="drift-a" rx="330" ry="190" fill="url(#nebulaViolet)"/></g>
  <g transform="translate(806 250)"><ellipse class="drift-b" rx="240" ry="150" fill="url(#nebulaTeal)"/></g>
  <g transform="translate(560 40)"><ellipse class="drift-a" rx="200" ry="110" fill="url(#nebulaRose)"/></g>

  <!-- Milky way -->
  {_milkyway()}
  </g>

  <!-- Constellation -->
  {_constellation()}

  <!-- Sparkles -->
  {_sparkles()}

  <!-- Starfield, split into two parallax layers -->
  <g class="parallax-far">{_stars("far")}</g>
  <g class="parallax-near">{_stars("near")}</g>

  <!-- Orbits -->
  <g transform="translate({MARK_X + MARK_W / 2} {MARK_Y + mark_h / 2})">
    {orbits}
  </g>

  <!-- Comet: sweeps along an arc, tail tapering to nothing -->
  <g>
    <g>
      <path d="M0,0 L-86,-3.6 L-96,0 L-86,3.6 Z" fill="url(#cometTail)"/>
      <circle cx="0" cy="0" r="2.6" fill="#ffffff"/>
      <circle cx="0" cy="0" r="6" fill="url(#cometGlow)"/>
      <animateMotion dur="{LOOP}s" repeatCount="indefinite" keyPoints="0;1;1" keyTimes="0;0.66;1"
                     calcMode="linear"
                     path="M-60,110 C140,44 340,6 560,20 C760,32 900,92 1040,66"/>
      <animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite"
               values="0;0.95;0.95;0" keyTimes="0;0.08;0.58;0.66"/>
    </g>
  </g>

  <!-- Second comet, offset by half a loop, on a lower arc -->
  <g>
    <g>
      <path d="M0,0 L-64,-2.8 L-72,0 L-64,2.8 Z" fill="url(#cometTail)"/>
      <circle cx="0" cy="0" r="2" fill="#ffffff"/>
      <circle cx="0" cy="0" r="5" fill="url(#cometGlow)"/>
      <animateMotion dur="{LOOP}s" repeatCount="indefinite" begin="-4s"
                     keyPoints="0;1;1" keyTimes="0;0.6;1" calcMode="linear"
                     path="M1040,210 C840,250 640,286 440,268 C260,252 120,214 -40,236"/>
      <animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite" begin="-4s"
               values="0;0.8;0.8;0" keyTimes="0;0.1;0.54;0.6"/>
    </g>
  </g>

  <!-- Companion planet -->
  <g class="float-2">
    <circle cx="{p2x}" cy="{p2y}" r="{p2r + 16}" fill="url(#planet2Glow)"/>
    <circle cx="{p2x}" cy="{p2y}" r="{p2r}" fill="url(#planet2)"/>
    <circle cx="{p2x}" cy="{p2y}" r="{p2r - 1}" fill="none" stroke="#bcd0ff" stroke-width="1" opacity="0.35"/>
    <ellipse cx="{p2x}" cy="{p2y}" rx="{p2r + 20}" ry="{round(p2r * 0.34)}" transform="rotate(-18 {p2x} {p2y})"
             fill="none" stroke="#9db8ff" stroke-width="1" stroke-dasharray="2 7" opacity="0.55"/>
  </g>

  <!-- Moon -->
  <g class="float">
    <circle cx="{mx}" cy="{my}" r="{mr}" fill="#8fa6c9" opacity="0.85"/>
    <circle cx="{mx - 4}" cy="{my - 4}" r="{mr - 5}" fill="#c3d2e8" opacity="0.5"/>
  </g>

  <!-- Main planet -->
  <g class="float">
    <image x="{MARK_X}" y="{MARK_Y}" width="{MARK_W}" height="{mark_h}"
           xlink:href="data:image/png;base64,{mark_b64}"/>
  </g>
</svg>
"""


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
