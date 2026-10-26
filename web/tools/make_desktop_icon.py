from PIL import Image
from pathlib import Path
ROOT = Path(r"D:\Users\HI MATEBOOK 14\Documents\deepseek-harness\default-workspace\dreamai-web")
src = Image.open(ROOT / "web" / "assets" / "img" / "icon-512.png").convert("RGBA")
out = ROOT / "desktop" / "build" / "icon.ico"
src.save(out, sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print("icon.ico", out.stat().st_size)