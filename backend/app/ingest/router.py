"""MIME-based routing.

Routing on the sniffed MIME type rather than the file extension means a
mislabelled upload is still sent to the correct parser; the extension is only
used as a fallback when sniffing is inconclusive.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

from ..config import AUDIO_EXT, DOCX_EXT, IMAGE_EXT, PDF_EXT, TEXT_EXT
from ..models import Modality


def detect_modality(path: Path) -> tuple[Modality, str]:
    """Return (modality, loader_kind) for a file on disk."""
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or ""
    suffix = path.suffix.lower()

    if mime == "application/pdf" or suffix in PDF_EXT:
        return "text", "pdf"
    if "wordprocessingml" in mime or mime == "application/msword" or suffix in DOCX_EXT:
        return "text", "docx"
    if mime.startswith("image/") or suffix in IMAGE_EXT:
        return "image", "image"
    if mime.startswith("audio/") or mime.startswith("video/") or suffix in AUDIO_EXT:
        return "audio", "audio"
    if mime.startswith("text/") or suffix in TEXT_EXT:
        return "text", "plain"
    raise ValueError(f"unsupported file type: {path.name} ({mime or 'unknown mime'})")


def load_file(path: Path):
    """Dispatch to the modality-specific loader. Returns a raw payload dict."""
    modality, kind = detect_modality(path)

    if kind == "pdf":
        from .pdf_loader import load_pdf

        pages, images = load_pdf(path)
        return {"kind": kind, "modality": modality, "pages": pages, "images": images}

    if kind == "docx":
        from .docx_loader import load_docx

        return {"kind": kind, "modality": modality, "text": load_docx(path)}

    if kind == "plain":
        return {"kind": kind, "modality": modality, "text": path.read_text(errors="ignore")}

    if kind == "image":
        from .image_loader import ocr_image

        return {"kind": kind, "modality": modality, "ocr": ocr_image(path), "image_path": path}

    if kind == "audio":
        from .audio_loader import transcribe

        return {"kind": kind, "modality": modality, "segments": transcribe(path)}

    raise ValueError(f"no loader for kind: {kind}")
