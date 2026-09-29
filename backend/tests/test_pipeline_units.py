"""Unit tests for the pure-python parts of the pipeline.

These run without Qdrant, Ollama or any model download, so they are safe to
run in CI or on a fresh checkout.
"""
from app.ingest.chunker import normalise, sliding_window
from app.retrieval.bm25 import BM25, tokenize
from app.retrieval.mmr import mmr_select
from app.store.dedup import chunk_uuid


def test_sliding_window_respects_size_and_overlap():
    text = " ".join(f"w{i}" for i in range(1200))
    windows = sliding_window(text, size=512, overlap=50)
    assert len(windows) >= 2
    assert len(windows[0].split()) == 512
    first_tail = windows[0].split()[-50:]
    second_head = windows[1].split()[:50]
    assert first_tail == second_head


def test_short_text_is_a_single_window():
    assert sliding_window("only a few tokens here") == ["only a few tokens here"]


def test_normalise_collapses_whitespace():
    assert normalise("  a\n\tb   c ") == "a b c"


def test_bm25_ranks_the_lexically_closest_document_first():
    corpus = ["offline rag qdrant vectors", "civic issue reporting", "whisper audio transcript"]
    scores = BM25(corpus).scores("qdrant offline rag")
    assert scores[0] == max(scores) > 0


def test_tokenize_drops_stopwords():
    assert "the" not in tokenize("the offline system")


def test_mmr_suppresses_near_duplicates():
    items = [
        {"text": "alpha beta gamma delta", "s": 0.99},
        {"text": "alpha beta gamma delta", "s": 0.98},
        {"text": "entirely different content here", "s": 0.40},
    ]
    picked = mmr_select(items, k=2, lambda_=0.5, score_key="s")
    assert len({p["text"] for p in picked}) == 2


def test_mmr_with_lambda_one_ignores_diversity():
    items = [
        {"text": "alpha beta gamma delta", "s": 0.99},
        {"text": "alpha beta gamma delta", "s": 0.98},
        {"text": "entirely different content here", "s": 0.40},
    ]
    picked = mmr_select(items, k=2, lambda_=1.0, score_key="s")
    assert [p["s"] for p in picked] == [0.99, 0.98]


def test_chunk_uuid_is_deterministic_and_content_sensitive():
    assert chunk_uuid("doc", 1, "hello") == chunk_uuid("doc", 1, "hello")
    assert chunk_uuid("doc", 1, "hello") != chunk_uuid("doc", 1, "hello!")
