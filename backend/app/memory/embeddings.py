# Module: backend.app.memory.embeddings
from __future__ import annotations

import hashlib
import math
import re
from typing import List, Optional


class HashEmbedder:
    """
    Deterministic text embedder based on SHA-256 token hashing.
    Provides fast, sub-millisecond embeddings without external GPU/model dependencies.
    """

    def __init__(self, dimension: int = 64):
        self.dimension = max(16, dimension)

    def embed(self, text: str) -> List[float]:
        """Convert input text to a normalized float vector."""
        if not text:
            return [0.0] * self.dimension

        vec = [0.0] * self.dimension
        words = re.findall(r"\b\w+\b", text.lower())
        if not words:
            words = [text.strip().lower()]

        for word in words:
            digest = hashlib.sha256(word.encode("utf-8")).digest()
            # Extract 8 bytes as big-endian integer
            val = int.from_bytes(digest[:8], byteorder="big")
            idx = val % self.dimension
            vec[idx] += 1.0

        # Also hash character n-grams (tri-grams) for robust sub-word matching
        clean_text = text.lower().strip()
        if len(clean_text) >= 3:
            for i in range(len(clean_text) - 2):
                ngram = clean_text[i:i+3]
                digest = hashlib.sha256(ngram.encode("utf-8")).digest()
                val = int.from_bytes(digest[:8], byteorder="big")
                idx = val % self.dimension
                vec[idx] += 0.5

        self._normalize(vec)
        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts in batch."""
        return [self.embed(t) for t in texts]

    @staticmethod
    def _normalize(vec: List[float]) -> None:
        sum_sq = sum(v * v for v in vec)
        if sum_sq == 0.0:
            return
        norm = math.sqrt(sum_sq)
        for i in range(len(vec)):
            vec[i] = round(vec[i] / norm, 6)


default_embedder = HashEmbedder(dimension=64)
