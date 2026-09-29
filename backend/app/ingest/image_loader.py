"""Image preprocessing and OCR.

Greyscale conversion, denoising and adaptive thresholding materially improve
pytesseract's output on screenshots and scans compared with feeding the raw
image straight in.
"""
from __future__ import annotations

from pathlib import Path


def preprocess(path: Path):
    import cv2

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"could not decode image: {path}")
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    grey = cv2.fastNlMeansDenoising(grey, h=10)
    return cv2.adaptiveThreshold(
        grey, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
    )


def ocr_image(path: Path) -> str:
    """Best-effort OCR. Returns an empty string if the image carries no text."""
    try:
        import pytesseract

        processed = preprocess(path)
        return (pytesseract.image_to_string(processed) or "").strip()
    except Exception:
        return ""
