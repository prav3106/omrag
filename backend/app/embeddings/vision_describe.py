"""LLaVA image descriptions through the local Ollama daemon.

Placing a natural-language description of every image into the text vector
space is what lets a plain text query reach an image without going through
CLIP's text tower.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

import httpx
from PIL import Image

from ..config import settings

MAX_DIMENSION = 1024

PROMPT = (
    "Describe this image factually and in detail for a search index. "
    "Include any visible text, numbers, chart values, labels and the overall subject. "
    "If the image shows a person, describe their appearance, always including: "
    "hair colour, and whether they have a beard, moustache, or are clean-shaven "
    "(state this explicitly even if the answer is 'clean-shaven' or 'no facial hair'), "
    "clothing, and any other notable features. "
    "Do not speculate. Respond with description text only."
)

FALLBACK = "image"


def _downscaled_b64(path: Path) -> str:
    """Cap the longest edge at MAX_DIMENSION before sending to the vision model.

    Vision-language models with dynamic-resolution encoders (e.g. Qwen2.5-VL)
    tokenise proportionally to pixel count, so full-resolution page scans cost
    several times more prompt-eval time than a downscaled copy for barely any
    caption-quality loss - the model is describing content, not reading fine
    print (OCR already covers that separately).
    """
    with Image.open(path) as im:
        im = im.convert("RGB")
        if max(im.size) > MAX_DIMENSION:
            im.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode()


def describe_image(path: Path, timeout: float = 240.0) -> str:
    """Ask LLaVA to describe the image. Retries once on failure.
    Always returns at least a generic fallback so the chunk gets a text vector.
    """
    if not settings.enable_vision_describe:
        return FALLBACK
    payload = {
        "model": settings.vision_model,
        "prompt": PROMPT,
        "images": [_downscaled_b64(path)],
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 120},
    }
    for attempt in range(2):
        try:
            r = httpx.post(
                f"{settings.ollama_url}/api/generate", json=payload, timeout=timeout
            )
            r.raise_for_status()
            result = (r.json().get("response") or "").strip()
            if result:
                return result
        except Exception:
            if attempt == 0:
                continue  # retry once
    return FALLBACK
