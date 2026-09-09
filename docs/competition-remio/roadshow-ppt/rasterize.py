"""用 PyMuPDF 把 PDF 逐页渲染为 PNG（150 DPI）。"""
import sys
import fitz

pdf_path, out_dir = sys.argv[1], sys.argv[2]
import os
os.makedirs(out_dir, exist_ok=True)
doc = fitz.open(pdf_path)
zoom = 150 / 72
mat = fitz.Matrix(zoom, zoom)
for i, page in enumerate(doc):
    pix = page.get_pixmap(matrix=mat)
    pix.save(os.path.join(out_dir, f"slide_{i + 1:02d}.png"))
print(f"rendered {len(doc)} pages")
