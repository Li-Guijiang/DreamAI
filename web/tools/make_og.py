"""Regenerate the social share card (1200×630)."""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "web" / "assets" / "img"
MARK = Path(
    r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\DreamAI"
    r"\assets\logo\DreamAI-Logo\02_纯星球符号_透明底\DreamAI-mark-1024-透明底.png"
)
FONT_BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")
FONT_REG = Path(r"C:\Windows\Fonts\msyh.ttc")
BG = (8, 9, 13)


def glow(width: int, height: int, color, center, radius, alpha):
    ys, xs = np.mgrid[0:height, 0:width]
    cx, cy = center[0] * width, center[1] * height
    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    falloff = np.clip(1 - dist / radius, 0, 1) ** 2.0
    arr = np.zeros((height, width, 4), dtype=np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = color
    arr[..., 3] = (falloff * alpha * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def gradient_text(text: str, font, size: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).text((0, 0), text, font=font, fill=255)
    width, height = size
    stops = [(0.0, (94, 234, 212)), (0.42, (124, 156, 255)), (0.76, (183, 156, 255)), (1.0, (240, 166, 200))]
    x = np.linspace(0, 1, width)[None, :]
    y = np.linspace(0, 1, height)[:, None]
    t = np.clip(x * 0.85 + y * 0.15, 0, 1)
    arr = np.zeros((height, width, 3))
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


def main() -> None:
    width, height = 1200, 630
    card = Image.new("RGBA", (width, height), BG)
    card.alpha_composite(glow(width, height, (94, 234, 212), (0.02, -0.08), 640, 0.30))
    card.alpha_composite(glow(width, height, (124, 156, 255), (1.03, 0.0), 640, 0.32))
    card.alpha_composite(glow(width, height, (183, 156, 255), (0.6, 1.2), 720, 0.22))

    draw = ImageDraw.Draw(card, "RGBA")
    rng = random.Random(11)
    for _ in range(90):
        px, py = rng.randrange(width), rng.randrange(height)
        r = rng.choice([1, 1, 2])
        draw.ellipse((px, py, px + r, py + r), fill=(200, 214, 255, rng.randrange(10, 55)))

    mark = Image.open(MARK).convert("RGBA").resize((124, 124), Image.LANCZOS)
    card.alpha_composite(mark, (86, 66))

    title_font = ImageFont.truetype(str(FONT_BOLD), 54)
    draw.text((228, 84), "Dream AI", font=title_font, fill=(244, 245, 249, 255))
    sub_font = ImageFont.truetype(str(FONT_REG), 24)
    draw.text((230, 152), "通用人工智能助手", font=sub_font, fill=(158, 166, 184, 255))

    head_font = ImageFont.truetype(str(FONT_BOLD), 74)
    card.alpha_composite(gradient_text("把想法交给 Dream，", head_font, (980, 100)), (86, 288))
    card.alpha_composite(gradient_text("让每个灵感都有回响。", head_font, (980, 100)), (86, 392))

    body_font = ImageFont.truetype(str(FONT_REG), 25)
    draw.text((90, 520), "写作 · 编程 · 推理 · 创意", font=body_font, fill=(154, 162, 180, 255))

    draw.line((90, 578, 1110, 578), fill=(255, 255, 255, 22), width=1)
    small = ImageFont.truetype(str(FONT_REG), 21)
    draw.text((90, 592), "liguijiang.com", font=small, fill=(178, 188, 208, 255))
    by = "by Dream AI 团队"
    bbox = draw.textbbox((0, 0), by, font=small)
    draw.text((1110 - (bbox[2] - bbox[0]), 592), by, font=small, fill=(128, 136, 154, 255))

    card.convert("RGB").save(IMG / "og.png", optimize=True)
    print("og.png updated")


if __name__ == "__main__":
    main()
