"""Central configuration. Every value can be overridden through the environment
or a .env file placed at the repository root."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except Exception:  # python-dotenv is optional
    pass


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    # ---- storage -------------------------------------------------------
    data_dir: Path = field(default_factory=lambda: Path(_env("OMRAG_DATA_DIR", str(ROOT / "data"))))
    upload_dir: Path = field(init=False)
    sqlite_path: Path = field(init=False)

    # ---- qdrant --------------------------------------------------------
    qdrant_url: str = field(default_factory=lambda: _env("QDRANT_URL", "http://localhost:6333"))
    collection: str = field(default_factory=lambda: _env("QDRANT_COLLECTION", "multimodal_rag"))
    text_vector: str = "text"
    image_vector: str = "image"
    text_dim: int = 384
    image_dim: int = 512

    # ---- models --------------------------------------------------------
    text_model: str = field(default_factory=lambda: _env("TEXT_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    image_model: str = field(default_factory=lambda: _env("IMAGE_MODEL", "ViT-B-32"))
    image_pretrained: str = field(default_factory=lambda: _env("IMAGE_PRETRAINED", "laion2b_s34b_b79k"))
    reranker_model: str = field(default_factory=lambda: _env("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"))
    whisper_model: str = field(default_factory=lambda: _env("WHISPER_MODEL", "large-v3"))
    whisper_compute: str = field(default_factory=lambda: _env("WHISPER_COMPUTE", "int8"))

    # ---- ollama --------------------------------------------------------
    ollama_url: str = field(default_factory=lambda: _env("OLLAMA_URL", "http://localhost:11434"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "llama3.1"))
    vision_model: str = field(default_factory=lambda: _env("VISION_MODEL", "llava"))
    llm_temperature: float = field(default_factory=lambda: _env_float("LLM_TEMPERATURE", 0.1))
    llm_top_p: float = field(default_factory=lambda: _env_float("LLM_TOP_P", 0.9))
    max_context_tokens: int = field(default_factory=lambda: _env_int("MAX_CONTEXT_TOKENS", 6000))

    # ---- pipeline ------------------------------------------------------
    chunk_tokens: int = field(default_factory=lambda: _env_int("CHUNK_TOKENS", 512))
    chunk_overlap: int = field(default_factory=lambda: _env_int("CHUNK_OVERLAP", 50))
    audio_chunk_words: int = field(default_factory=lambda: _env_int("AUDIO_CHUNK_WORDS", 80))
    audio_chunk_max_gap: float = field(default_factory=lambda: _env_float("AUDIO_CHUNK_MAX_GAP", 2.0))
    candidate_k: int = field(default_factory=lambda: _env_int("CANDIDATE_K", 20))
    final_k: int = field(default_factory=lambda: _env_int("FINAL_K", 5))
    w_dense: float = field(default_factory=lambda: _env_float("W_DENSE", 0.4))
    w_rerank: float = field(default_factory=lambda: _env_float("W_RERANK", 0.5))
    w_diversity: float = field(default_factory=lambda: _env_float("W_DIVERSITY", 0.1))
    mmr_lambda: float = field(default_factory=lambda: _env_float("MMR_LAMBDA", 0.7))
    enable_rerank: bool = field(default_factory=lambda: _env("ENABLE_RERANK", "1") == "1")
    enable_vision_describe: bool = field(default_factory=lambda: _env("ENABLE_VISION_DESCRIBE", "1") == "1")

    # ---- misc ----------------------------------------------------------
    max_upload_mb: int = field(default_factory=lambda: _env_int("MAX_UPLOAD_MB", 200))
    cors_origins: tuple = ("http://localhost:5173", "http://127.0.0.1:5173")

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        self.upload_dir = self.data_dir / "uploads"
        self.sqlite_path = self.data_dir / "registry.db"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()

TEXT_EXT = {".txt", ".md"}
PDF_EXT = {".pdf"}
DOCX_EXT = {".docx", ".doc"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac"}
SUPPORTED_EXT = TEXT_EXT | PDF_EXT | DOCX_EXT | IMAGE_EXT | AUDIO_EXT
