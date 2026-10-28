"""Generate the PNG brand assets (favicon, app icons, social card).

Run with a Python that has Pillow + numpy installed:

    python tools/make_assets.py

Sources: the official Dream AI mark shipped in the repository
(assets/logo/DreamAI-Logo/02_纯星球符号_透明底/DreamAI-mark-1024-透明底.png).
"""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "web" / "assets" / "img"
REPO_MARK = Path(
    r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\DreamAI"
    r"\assets\logo\DreamAI-Logo\02_纯星球符号_透明底\DreamAI-mark-1024-透明底.png"
)
FONT_BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")
FONT_REG = Path(r"C:\Windows\Fonts\msyh.ttc")

BG = (7, 8, 12)


def rounded_icon(size: int, pad_ratio: float = 0.16) -> Image.Image:
    scale = 4
    canvas = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    radius = int(size * scale * 0.24)
    draw.rounded_rectangle(
        (0, 0, size * scale - 1, size * scale - 1), radius=radius, fill=(11, 13, 19, 255)
    )
    mark = Image.open(REPO_MARK).convert("RGBA")
    inner = int(size * scale * (1 - pad_ratio * 2))
    mark = mark.resize((inner, inner), Image.LANCZOS)
    offset = (size * scale - inner) // 2
    canvas.alpha_composite(mark, (offset, offset))
    return canvas.resize((size, size), Image.LANCZOS)


def radial_layer(size: tuple[int, int], color: tuple[int, int, int], center: tuple[float, float], radius: float, alpha: float) -> Image.Image:
    width, height = size
    ys, xs = np.mgrid[0:height, 0:width]
    cx = center[0] * width
    cy = center[1] * height
    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    falloff = np.clip(1 - dist / radius, 0, 1) ** 2.2
    layer = np.zeros((height, width, 4), dtype=np.uint8)
    layer[..., 0] = color[0]
    layer[..., 1] = color[1]
    layer[..., 2] = color[2]
    layer[..., 3] = (falloff * alpha * 255).astype(np.uint8)
    return Image.fromarray(layer, "RGBA")


def gradient_text(text: str, font: ImageFont.FreeTypeFont, size: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.text((0, 0), text, font=font, fill=255)

    width, height = size
    stops = [
        (0.0, (94, 234, 212)),
        (0.38, (127, 166, 255)),
        (0.72, (183, 156, 255)),
        (1.0, (240, 166, 200)),
    ]
    x = np.linspace(0, 1, width)[None, :]
    y = np.linspace(0, 1, height)[:, None]
    t = np.clip(x * 0.82 + y * 0.18, 0, 1)
    arr = np.zeros((height, width, 3), dtype=np.float64)
    for i in range(len(stops) - 1):
        a, ca = stops[i]
        b, cb = stops[i + 1]
        sel = (t >= a) & (t <= b)
        local = (t[sel] - a) / (b - a)
        for c in range(3):
            arr[..., c][sel] = ca[c] + (cb[c] - ca[c]) * local
    grad = Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")
    grad.putalpha(mask)
    return grad


def build_og() -> None:
    width, height = 1200, 630
    card = Image.new("RGB", (width, height), BG)
    card = card.convert("RGBA")

    card.alpha_composite(radial_layer((width, height), (94, 234, 212), (0.06, -0.05), 620, 0.30))
    card.alpha_composite(radial_layer((width, height), (127, 166, 255), (1.02, 0.02), 600, 0.30))
    card.alpha_composite(radial_layer((width, height), (183, 156, 255), (0.55, 1.15), 700, 0.22))

    draw = ImageDraw.Draw(card, "RGBA")
    for x in range(0, width, 64):
        draw.line((x, 0, x, height), fill=(255, 255, 255, 9))
    for y in range(0, height, 64):
        draw.line((0, y, width, y), fill=(255, 255, 255, 9))

    rng = random.Random(7)
    for _ in range(140):
        px, py = rng.randrange(width), rng.randrange(height)
        r = rng.choice([1, 1, 1, 2])
        draw.ellipse((px, py, px + r, py + r), fill=(200, 214, 255, rng.randrange(18, 90)))

    mark = Image.open(REPO_MARK).convert("RGBA").resize((132, 132), Image.LANCZOS)
    card.alpha_composite(mark, (92, 74))

    title_font = ImageFont.truetype(str(FONT_BOLD), 52)
    draw.text((242, 92), "Dream AI", font=title_font, fill=(240, 242, 248, 255))
    sub_font = ImageFont.truetype(str(FONT_REG), 26)
    draw.text((244, 158), "梦 想 智 能", font=sub_font, fill=(160, 168, 185, 255))

    head_font = ImageFont.truetype(str(FONT_BOLD), 82)
    head = gradient_text("让每一个想法", head_font, (760, 110))
    card.alpha_composite(head, (92, 268))
    head2 = gradient_text("都被认真对待", head_font, (760, 110))
    card.alpha_composite(head2, (92, 382))

    body_font = ImageFont.truetype(str(FONT_REG), 26)
    draw.text(
        (96, 512),
        "会思考、能协作的通用智能体 · 写作 / 编程 / 推理 / 创意",
        font=body_font,
        fill=(150, 158, 176, 255),
    )

    line = Image.new("RGBA", (width, 1), (255, 255, 255, 20))
    card.alpha_composite(line, (92, 566))

    small = ImageFont.truetype(str(FONT_REG), 22)
    draw.text((96, 584), "liguijiang.com", font=small, fill=(180, 190, 210, 255))
    by = "by Dream AI 团队"
    bbox = draw.textbbox((0, 0), by, font=small)
    draw.text((width - 96 - (bbox[2] - bbox[0]), 584), by, font=small, fill=(130, 138, 156, 255))

    card.convert("RGB").save(IMG / "og.png", optimize=True)


def main() -> None:
    IMG.mkdir(parents=True, exist_ok=True)

    icon = rounded_icon(512)
    icon.save(IMG / "icon-512.png", optimize=True)
    rounded_icon(192).save(IMG / "icon-192.png", optimize=True)

    touch = rounded_icon(180, pad_ratio=0.2)
    touch.save(IMG / "apple-touch-icon.png", optimize=True)

    fav = rounded_icon(64, pad_ratio=0.1).convert("RGBA")
    fav.save(IMG / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])

    build_og()
    print("assets written to", IMG)


if __name__ == "__main__":
    main()
