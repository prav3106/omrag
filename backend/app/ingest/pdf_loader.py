"""PDF extraction with PyMuPDF.

Text is extracted page by page so that citations can carry a page number, and
embedded raster images are extracted separately so a chart inside a report
becomes an independently retrievable chunk rather than being lost.
"""
from __future__ import annotations

from pathlib import Path

from ..config import settings


def load_pdf(path: Path) -> tuple[list[tuple[int, str]], list[tuple[int, Path]]]:
    """Return (page_texts, extracted_images) for a PDF file."""
    import fitz  # PyMuPDF

    pages: list[tuple[int, str]] = []
    images: list[tuple[int, Path]] = []
    out_dir = settings.data_dir / "extracted" / path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    with fitz.open(path) as doc:
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            text = page.get_text("text")
            if text and text.strip():
                pages.append((page_index + 1, text))

            for img_index, info in enumerate(page.get_images(full=True)):
                xref = info[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n - pix.alpha >= 4:  # CMYK -> RGB
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    if pix.width < 64 or pix.height < 64:
                        continue  # skip icons, bullets, rules
                    dest = out_dir / f"p{page_index + 1}_i{img_index}.png"
                    pix.save(dest)
                    images.append((page_index + 1, dest))
                except Exception:
                    continue
    return pages, images
