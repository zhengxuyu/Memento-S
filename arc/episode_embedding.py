"""Episode embedding: BM25 retrieval with TF-IDF fallback.

Replaces the original SimpleEmbedding (TF-IDF only) with BM25 for better
text-based episode retrieval. Falls back to TF-IDF if rank_bm25 is not installed.

BM25 tokenization adapted from core/skill_engine/skill_catalog.py:_tokenize_for_bm25.
"""
from __future__ import annotations

import re
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Tokenizer (adapted from Memento-S _tokenize_for_bm25)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Tokenize text for BM25 indexing."""
    raw = str(text or "").strip()
    if not raw:
        return []
    # Simple whitespace + punctuation tokenizer
    tokens = re.sub(r"[^a-z0-9\s]", " ", raw.lower()).split()
    return [t for t in tokens if len(t) > 1]


# ---------------------------------------------------------------------------
# TF-IDF fallback (from original SimpleEmbedding)
# ---------------------------------------------------------------------------

class SimpleEmbedding:
    """TF-IDF bag-of-words embedding for fast local text similarity."""

    def __init__(self, dim: int = 512):
        self.dim = dim
        self._vocab: dict[str, int] = {}
        self._doc_count: int = 0
        self._word_doc_count: dict[str, int] = {}

    def encode(self, text: str) -> np.ndarray:
        words = _tokenize(text)
        unique_words = set(words)
        self._doc_count += 1
        for w in unique_words:
            self._word_doc_count[w] = self._word_doc_count.get(w, 0) + 1
            if w not in self._vocab and len(self._vocab) < self.dim:
                self._vocab[w] = len(self._vocab)

        vec = np.zeros(self.dim, dtype=np.float32)
        word_counts: dict[str, int] = {}
        for w in words:
            word_counts[w] = word_counts.get(w, 0) + 1

        for w, cnt in word_counts.items():
            if w in self._vocab:
                tf = cnt / max(len(words), 1)
                idf = np.log((self._doc_count + 1) / (self._word_doc_count.get(w, 1) + 1)) + 1
                vec[self._vocab[w]] = tf * idf

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec


# ---------------------------------------------------------------------------
# BM25-based retrieval
# ---------------------------------------------------------------------------

class EpisodeEmbedding:
    """BM25 + TF-IDF hybrid embedding for episode retrieval.

    Primary: BM25 ranking via rank_bm25.BM25Okapi.
    Fallback: TF-IDF cosine similarity (SimpleEmbedding) if rank_bm25 is missing.
    """

    def __init__(self, dim: int = 512):
        self._tfidf = SimpleEmbedding(dim=dim)
        self._bm25 = None  # Lazy-loaded BM25Okapi
        self._bm25_docs: list[list[str]] = []
        self._bm25_available: Optional[bool] = None

    def _check_bm25(self) -> bool:
        if self._bm25_available is None:
            try:
                from rank_bm25 import BM25Okapi  # noqa: F401
                self._bm25_available = True
            except ImportError:
                self._bm25_available = False
        return self._bm25_available

    def encode(self, text: str) -> np.ndarray:
        """Encode text to TF-IDF vector (for cosine similarity fallback)."""
        return self._tfidf.encode(text)

    def add_document(self, text: str) -> None:
        """Add a document to the BM25 index."""
        tokens = _tokenize(text)
        if not tokens:
            tokens = ["_"]
        self._bm25_docs.append(tokens)
        self._bm25 = None  # Invalidate index

    def _ensure_bm25_index(self) -> bool:
        """Build/rebuild BM25 index if needed."""
        if not self._check_bm25():
            return False
        if self._bm25 is None and self._bm25_docs:
            from rank_bm25 import BM25Okapi
            self._bm25 = BM25Okapi(self._bm25_docs)
        return self._bm25 is not None

    def retrieve_bm25(
        self,
        query_text: str,
        k: int = 5,
    ) -> list[tuple[int, float]]:
        """Retrieve top-k documents by BM25 score.

        Returns list of (doc_index, score) sorted descending.
        Falls back to empty list if BM25 unavailable.
        """
        if not self._ensure_bm25_index():
            return []
        q_tokens = _tokenize(query_text)
        if not q_tokens:
            return []
        scores = self._bm25.get_scores(q_tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [(idx, float(score)) for idx, score in ranked[:k] if score > 0]

    def clear(self) -> None:
        """Reset the BM25 index."""
        self._bm25_docs.clear()
        self._bm25 = None

    @property
    def tfidf(self) -> SimpleEmbedding:
        """Access the underlying TF-IDF embedder (for checkpoint save/load)."""
        return self._tfidf
