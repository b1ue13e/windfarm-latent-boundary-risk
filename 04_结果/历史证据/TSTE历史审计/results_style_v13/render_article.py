"""Render every article page and make complete contact sheets for visual review."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import shutil
import fitz
from PIL import Image, ImageDraw, ImageFont

Q = Path(__file__).resolve().parent
B = Q.parents[1]
PAGES = Q / "pages"
PAGES.mkdir(exist_ok=True)
doc = fitz.open(B / "manuscript.pdf")
shutil.copy2(B / "manuscript.pdf", B / "manuscript_results_style_v13.pdf")
images = []
for i, page in enumerate(doc):
    pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
    path = PAGES / f"page_{i+1}.png"
    pix.save(path)
    im = Image.open(path).convert("RGB")
    im.thumbnail((540, 720), Image.Resampling.LANCZOS)
    images.append(im)
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
for start, stop, stem in [(0, 4, "layout_pages_1_4"), (4, len(images), "layout_pages_5_7")]:
    sheet = Image.new("RGB", (1140, 1510), "#e9edf0")
    draw = ImageDraw.Draw(sheet)
    for j, im in enumerate(images[start:stop]):
        x, y = 20 + 570 * (j % 2), 16 + 750 * (j // 2)
        draw.text((x, y), f"Page {start+j+1}", font=font, fill="#263d4b")
        sheet.paste(im, (x, y+26))
    sheet.save(B / ("manuscript_" + stem + "_v13.png"))
print(f"Rendered all {len(doc)} pages; two complete contact sheets exported.")
