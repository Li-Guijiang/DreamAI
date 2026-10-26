from PIL import Image
from pathlib import Path
src = Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\dreamai-web\tools\qa\shots\80-desktop-app.png")
dst = Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\dreamai-web\web\assets\img\desktop-preview.png")
img = Image.open(src).convert("RGB")
img.save(dst, "PNG", optimize=True)
print(dst.stat().st_size, img.size)