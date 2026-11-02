"""Render a PDF's pages to PNG for visual layout checks: python render_pages.py in.pdf outdir [dpi]"""
import sys, os
import fitz
pdf, out = sys.argv[1], sys.argv[2]
dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 60
os.makedirs(out, exist_ok=True)
doc = fitz.open(pdf)
for i, page in enumerate(doc, 1):
    page.get_pixmap(dpi=dpi).save(os.path.join(out, f"p{i:02d}.png"))
print(len(doc), "pages")
