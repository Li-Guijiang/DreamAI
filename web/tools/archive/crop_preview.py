from PIL import Image
from pathlib import Path
src = Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\dreamai-web\tools\qa\shots\98-packaged-doc.png")
dst = Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\dreamai-web\web\assets\img\desktop-preview.png")
img = Image.open(src).convert("RGB")
w, h = img.size
cropped = img.crop((0, 70, w, h - 100))
cropped.save(dst, "PNG", optimize=True)
print(img.size, "->", cropped.size, dst.stat().st_size)