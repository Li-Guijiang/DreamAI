"""Generate the animated page banners used across the documentation.

Usage (repository root):

    python assets/brand/build_banners.py            # all variants
    python assets/brand/build_banners.py docs web   # selected variants

Each banner is a wide, thin strip placed directly under the page title. Frames are
synthesised with numpy and Pillow — no browser, no external assets — so the output
is deterministic and can be rebuilt anywhere.

Everything is periodic over LOOP seconds, so the GIF loops without a visible seam.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent
W, H = 760, 132
LOOP = 8.0          # seconds per loop
FPS = 4             # frames per second (GIF timing)
COLORS = 64         # palette size; keeps the files small

VARIANTS = {
    # name: (accent, second accent, motion mode)
    "docs":    ((139, 124, 255), (94, 234, 212), "aurora"),
    "web":     ((91, 140, 255), (120, 220, 255), "orbit"),
    "desktop": ((94, 234, 212), (124, 156, 255), "grid"),
    "assets":  ((240, 180, 41), (240, 166, 200), "aurora"),
}

rng = np.random.default_rng(7)


def _background(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> np.ndarray:
    """Vertical gradient, returned as float RGB in [0, 1] with shape (H, W, 3)."""
    t = np.linspace(0.0, 1.0, H)[:, None, None]
    column = (np.array(top) / 255.0) * (1 - t) + (np.array(bottom) / 255.0) * t
    return np.repeat(column, W, axis=1)


def _stars(count: int = 110) -> list[tuple[float, float, float, float]]:
    """Fixed star positions: x, y, radius, phase."""
    stars = []
    for _ in range(count):
        x = rng.uniform(0, W)
        y = rng.uniform(4, H - 6)
        r = float(rng.choice([0.6, 0.8, 1.0, 1.3]))
        stars.append((x, y, r, rng.uniform(0, 1)))
    return stars


STARS = _stars()


def _aurora_frame(accent: tuple[int, int, int], accent2: tuple[int, int, int], phase: float) -> Image.Image:
    base = _background((10, 12, 20), (16, 20, 34))
    yy = np.arange(H)[:, None]
    xx = np.arange(W)[None, :]
    overlay = np.zeros((H, W, 3))
    weight = np.zeros((H, W))

    for i, (color, amp, length, speed, y0) in enumerate(
        [
            (accent, 38, 560, 1.0, 0.44),
            (accent2, 26, 380, -1.5, 0.64),
            (accent, 18, 260, 2.2, 0.22),
        ]
    ):
        wave = y0 * H + amp * np.sin(2 * np.pi * (xx / length + phase * speed + i * 0.31))
        band = np.exp(-((yy - wave) ** 2) / (2 * (13 + 6 * i) ** 2))
        overlay += band[..., None] * (np.array(color) / 255.0) * (0.55 - 0.12 * i)
        weight += band

    weight = np.clip(weight, 0, 1)[..., None]
    img = base * (1 - weight * 0.85) + overlay * 0.85
    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")
    draw = ImageDraw.Draw(out, "RGBA")

    for x, y, r, ph in STARS:
        tw = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(2 * math.pi * (phase + ph)))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(220, 232, 255, int(200 * tw)))

    _comet(draw, phase)
    _hairline(out, accent, phase)
    return out.convert("RGB")


def _orbit_frame(accent: tuple[int, int, int], accent2: tuple[int, int, int], phase: float) -> Image.Image:
    base = _background((9, 12, 22), (14, 20, 38))
    img = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    cx, cy = W * 0.5, H * 0.68
    rings = [
        (300, 42, -7, 1.0, accent, 70),
        (232, 32, 5, -1.25, accent2, 52),
        (164, 23, -3, 1.7, accent, 38),
    ]

    def point(rx, ry, rot, angle):
        ex, ey = rx * math.cos(angle), ry * math.sin(angle)
        r = math.radians(rot)
        return (cx + ex * math.cos(r) - ey * math.sin(r), cy + ex * math.sin(r) + ey * math.cos(r))

    for rx, ry, rot, speed, color, alpha in rings:
        # smooth full ring
        poly = [point(rx, ry, rot, 2 * math.pi * i / 180) for i in range(181)]
        draw.line(poly, fill=(*color, alpha), width=1, joint="curve")

        # two rotating highlight arcs, drawn as dense polylines so they stay smooth
        for k in range(2):
            a0 = 2 * math.pi * ((phase * speed + 0.5 * k) % 1.0)
            span = math.radians(40)
            arc = [point(rx, ry, rot, a0 + span * j / 24) for j in range(25)]
            draw.line(arc, fill=(*color, min(255, alpha + 120)), width=2, joint="curve")

        # travelling light point
        p_ang = 2 * math.pi * ((phase * speed) % 1.0)
        px, py = point(rx, ry, rot, p_ang)
        for rad, a in ((7, 34), (4, 96), (2, 220)):
            draw.ellipse((px - rad, py - rad, px + rad, py + rad), fill=(*color, a))

    for x, y, rad, ph in STARS:
        tw = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(2 * math.pi * (phase + ph)))
        draw.ellipse((x - rad, y - rad, x + rad, y + rad), fill=(226, 236, 255, int(190 * tw)))

    _comet(draw, phase)
    _hairline(img, accent, phase)
    return img.convert("RGB")


def _grid_frame(accent: tuple[int, int, int], accent2: tuple[int, int, int], phase: float) -> Image.Image:
    base = _background((8, 12, 18), (12, 20, 30))
    img = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    step = 26
    for row, y in enumerate(range(10, H, step)):
        for col, x in enumerate(range(14, W, step)):
            d = math.hypot((x - W / 2) / (W / 2), (y - H / 2) / (H / 2))
            pulse = 0.5 + 0.5 * math.sin(2 * math.pi * (phase * 1.6 - d * 0.8))
            alpha = int(20 + 150 * pulse * (1 - d * 0.55))
            if alpha <= 6:
                continue
            rad = 1.0 + 1.6 * pulse
            color = accent if (row + col) % 3 else accent2
            draw.ellipse((x - rad, y - rad, x + rad, y + rad), fill=(*color, alpha))

    # sweeping scan line
    sx = (phase * 1.35 % 1.0) * (W + 120) - 60
    for off, width, alpha in ((0, 4, 12), (4, 2, 26), (9, 1, 55)):
        draw.line([(sx - off, 0), (sx - off - 14, H)], fill=(*accent2, alpha), width=width)

    _hairline(img, accent, phase)
    return img.convert("RGB")


def _comet(draw: ImageDraw.ImageDraw, phase: float) -> None:
    """A streak crossing the strip once per loop, visible for the middle third."""
    span = 0.62
    if not (0.12 <= phase <= 0.12 + span):
        return
    t = (phase - 0.12) / span
    x = -80 + t * (W + 160)
    y = H * 0.30 - t * 26
    for i in range(26, 0, -1):
        alpha = int(150 * (i / 26) ** 2)
        draw.line([(x - i * 5, y + i * 1.6), (x - i * 5 + 4, y + i * 1.6 + 1.2)],
                  fill=(200, 214, 255, alpha), width=1)
    draw.ellipse((x - 2.2, y - 2.2, x + 2.2, y + 2.2), fill=(255, 255, 255, 235))


def _hairline(img: Image.Image, accent: tuple[int, int, int], phase: float) -> None:
    """A gradient bar along the bottom edge that sweeps with the loop."""
    draw = ImageDraw.Draw(img, "RGBA")
    for x in range(W):
        wave = 0.5 + 0.5 * math.sin(2 * math.pi * (x / W - phase))
        alpha = int(30 + 120 * wave ** 3)
        draw.point((x, H - 2), fill=(*accent, alpha))
        draw.point((x, H - 1), fill=(*accent, max(0, alpha - 40)))


# --- Extra motion assets -----------------------------------------------------

DIV_W, DIV_H = 640, 34
FOOT_W, FOOT_H = 760, 92
FLOW_W, FLOW_H = 760, 210


def divider_frame(accent, accent2, phase):
    """A thin stream of particles with a bright pulse running left to right."""
    img = Image.new("RGBA", (DIV_W, DIV_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    mid = DIV_H / 2
    draw.line([(0, mid), (DIV_W, mid)], fill=(*accent, 34), width=1)

    for i in range(46):
        x = (i / 46 + phase * 0.9) % 1.0 * DIV_W
        wave = math.sin(2 * math.pi * (i / 46 + phase)) * 6
        fade = math.sin(math.pi * x / DIV_W)
        r = 1.2 + 1.6 * abs(math.sin(2 * math.pi * (phase + i * 0.13)))
        draw.ellipse((x - r, mid + wave - r, x + r, mid + wave + r),
                     fill=(*accent2, int(150 * fade)))

    px = phase * (DIV_W + 120) - 60
    for off, alpha, width in ((0, 210, 3), (10, 90, 6), (24, 40, 12)):
        draw.line([(px, mid), (px - off, mid)], fill=(255, 255, 255, alpha), width=width)
    return img


def footer_frame(accent, accent2, phase):
    """A calm closing strip: three breathing arcs and a slow comet."""
    base = _background((7, 9, 16), (11, 14, 24))
    img = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    for i, (color, rad) in enumerate(((accent, 180), (accent2, 128), (accent, 84))):
        cy = FOOT_H + 26
        breathe = 0.5 + 0.5 * math.sin(2 * math.pi * (phase + i * 0.22))
        for k in range(3):
            rr = rad - k * 8
            alpha = int((16 + 44 * breathe) * (1 - k * 0.25))
            draw.arc((FOOT_W / 2 - rr, cy - rr, FOOT_W / 2 + rr, cy + rr),
                     start=200, end=340, fill=(*color, alpha), width=1 + k)

    for x, y, r, ph in STARS[:60]:
        if y > FOOT_H - 4:
            continue
        tw = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(2 * math.pi * (phase + ph)))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(220, 232, 255, int(150 * tw)))

    _hairline(img, accent, phase)
    return img.convert("RGB")


def flow_frame(accent, accent2, phase):
    """Animated data flow: CLI -> Agent -> Provider / Memory / Tools."""
    base = _background((8, 10, 18), (12, 16, 28))
    img = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    nodes = {
        "cli": (86, FLOW_H / 2),
        "agent": (340, FLOW_H / 2),
        "prov": (600, 54),
        "mem": (600, FLOW_H / 2),
        "tools": (600, FLOW_H - 54),
    }
    edges = [("cli", "agent", accent), ("agent", "prov", accent2), ("agent", "mem", accent2), ("agent", "tools", accent2)]

    for a, b, color in edges:
        ax, ay = nodes[a]
        bx, by = nodes[b]
        draw.line([(ax, ay), (bx, by)], fill=(*color, 46), width=1)

        # packet travelling along the edge
        for k in range(2):
            tpar = (phase + 0.5 * k) % 1.0
            px = ax + (bx - ax) * tpar
            py = ay + (by - ay) * tpar
            fade = math.sin(math.pi * tpar)
            for rad, alpha in ((5, int(40 * fade)), (2.4, int(210 * fade))):
                draw.ellipse((px - rad, py - rad, px + rad, py + rad), fill=(*color, alpha))

    for key, (x, y) in nodes.items():
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * (phase + (0.15 if key == "agent" else 0.0)))
        radius = 13 + 2.5 * pulse
        color = accent if key in ("cli", "agent") else accent2
        draw.ellipse((x - radius - 6, y - radius - 6, x + radius + 6, y + radius + 6), fill=(*color, 18))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=(*color, 190), width=1)
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(*color, 230))

    for x, y, r, ph in STARS[:70]:
        tw = 0.2 + 0.8 * (0.5 + 0.5 * math.sin(2 * math.pi * (phase + ph)))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(220, 232, 255, int(120 * tw)))

    return img.convert("RGB")


def build_asset(name: str, render, frames: int, colours: int, duration: int) -> Path:
    out_frames = []
    for i in range(frames):
        out_frames.append(render(i / frames).convert("P", palette=Image.ADAPTIVE, colors=colours))
    out = OUT_DIR / name
    out_frames[0].save(out, save_all=True, append_images=out_frames[1:], duration=duration,
                       loop=0, optimize=True, disposal=2)
    return out


def build(name: str, accent, accent2, mode: str) -> Path:
    frames = []
    total = int(round(LOOP * FPS))
    render = {"aurora": _aurora_frame, "orbit": _orbit_frame, "grid": _grid_frame}[mode]
    for i in range(total):
        phase = i / total
        frames.append(render(accent, accent2, phase).convert("P", palette=Image.ADAPTIVE, colors=COLORS))

    out = OUT_DIR / f"banner-{name}.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / FPS),
        loop=0,
        optimize=True,
        disposal=2,
    )
    return out


if __name__ == "__main__":
    wanted = sys.argv[1:] or list(VARIANTS)
    for key in wanted:
        accent, accent2, mode = VARIANTS[key]
        path = build(key, accent, accent2, mode)
        print(f"{path.name}: {path.stat().st_size / 1024:.0f} KB ({mode})")

    if not sys.argv[1:]:
        accent, accent2 = VARIANTS["docs"][0], VARIANTS["docs"][1]
        for name, render, frames, colours, dur in (
            ("divider.gif", lambda p: divider_frame(accent, accent2, p), 24, 32, 250),
            ("footer.gif", lambda p: footer_frame(accent, accent2, p), 20, 48, 400),
            ("flow.gif", lambda p: flow_frame(accent, accent2, p), 24, 48, 333),
        ):
            path = build_asset(name, render, frames, colours, dur)
            print(f"{path.name}: {path.stat().st_size / 1024:.0f} KB")
