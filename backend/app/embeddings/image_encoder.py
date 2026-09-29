"""512-dimensional image embeddings via open_clip (ViT-B/32).

The CLIP text tower is kept available so that a text query can also be matched
directly against the image vector space; document-length text still goes
through sentence-transformers, which handles long passages far better than
CLIP's caption-trained text encoder.
"""
from __future__ import annotations

import threading
from pathlib import Path

from ..config import settings

_state: dict = {}
_lock = threading.Lock()


def _get():
    if "model" not in _state:
        with _lock:
            if "model" not in _state:
                import open_clip
                import torch

                model, _, preprocess = open_clip.create_model_and_transforms(
                    settings.image_model, pretrained=settings.image_pretrained
                )
                model.eval()
                _state.update(
                    model=model,
                    preprocess=preprocess,
                    tokenizer=open_clip.get_tokenizer(settings.image_model),
                    torch=torch,
                )
    return _state


def encode_images(paths: list[Path], batch_size: int = 16) -> list[list[float]]:
    if not paths:
        return []
    from PIL import Image

    s = _get()
    torch = s["torch"]
    out: list[list[float]] = []

    for start in range(0, len(paths), batch_size):
        batch = paths[start : start + batch_size]
        tensors = []
        for p in batch:
            with Image.open(p) as img:
                tensors.append(s["preprocess"](img.convert("RGB")))
        stack = torch.stack(tensors)
        with torch.no_grad():
            feats = s["model"].encode_image(stack)
            feats = feats / feats.norm(dim=-1, keepdim=True)
        out.extend(feats.cpu().numpy().tolist())
    return out


def encode_text_for_images(text: str) -> list[float]:
    """Project a text query into CLIP's shared space for text-to-image search."""
    s = _get()
    torch = s["torch"]
    tokens = s["tokenizer"]([text])
    with torch.no_grad():
        feats = s["model"].encode_text(tokens)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats.cpu().numpy()[0].tolist()


def image_encoder_ready() -> tuple[bool, str]:
    try:
        _get()
        return True, f"{settings.image_model} / {settings.image_pretrained} ({settings.image_dim}-d)"
    except Exception as exc:  # pragma: no cover
        return False, str(exc)
