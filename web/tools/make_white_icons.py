from PIL import Image, ImageDraw
from pathlib import Path

ROOT = Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\dreamai-web")
MARK = Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\DreamAI\assets\logo\DreamAI-Logo\02_纯星球符号_透明底\DreamAI-mark-1024-透明底.png")
IMG = ROOT / "web" / "assets" / "img"

def icon(size: int, bg="white", border=True, pad=0.14) -> Image.Image:
    scale = 4
    canvas = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    radius = int(size * scale * 0.24)
    d.rounded_rectangle((0, 0, size*scale-1, size*scale-1), radius=radius, fill=bg,
                        outline=(214, 220, 232, 255) if border else None, width=max(1, scale))
    mark = Image.open(MARK).convert("RGBA")
    inner = int(size * scale * (1 - pad * 2))
    mark = mark.resize((inner, inner), Image.LANCZOS)
    off = (size*scale - inner)//2
    canvas.alpha_composite(mark, (off, off))
    return canvas.resize((size, size), Image.LANCZOS)

icon(64).save(IMG / "favicon.ico", sizes=[(16,16),(32,32),(48,48)])
icon(180).save(IMG / "apple-touch-icon.png", optimize=True)
icon(192).save(IMG / "icon-192.png", optimize=True)
icon(512).save(IMG / "icon-512.png", optimize=True)
icon(32).save(IMG / "favicon-32.png", optimize=True)
print("icons written")