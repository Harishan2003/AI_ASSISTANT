# Module: backend.app.memory.vector_store
from __future__ import annotations

import copy
import json
import math
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.memory.embeddings import HashEmbedder, default_embedder

STORAGE_DIR = Path(r"C:\Users\Harishan\Desktop\AI_ASSISTANT\memory\embeddings")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_STORE_FILE = STORAGE_DIR / "vector_store.json"


@dataclass
class VectorDocument:
    id: str = ""
    text: str = ""
    embedding: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "score": round(self.score, 4),
            "metadata": self.metadata,
        }


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = 0.0
    na = 0.0
    nb = 0.0
    for i in range(n):
        dot += a[i] * b[i]
        na += a[i] * a[i]
        nb += b[i] * b[i]

    if na == 0.0 or nb == 0.0:
        return 0.0
    score = dot / (math.sqrt(na) * math.sqrt(nb))
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def metadata_matches(metadata: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
    if not filters:
        return True
    for key, expected in filters.items():
        actual = metadata.get(key)
        if actual is None:
            return False
        if str(actual) != str(expected):
            return False
    return True


class MemoryVectorStore:
    """
    Thread-safe in-memory vector store with disk persistence.
    Supports cosine vector search, exact keyword boost, and metadata filtering.
    """

    def __init__(
        self,
        embedder: Optional[HashEmbedder] = None,
        persist_path: Optional[Path] = None,
        auto_persist: bool = True,
    ):
        self._lock = threading.RLock()
        self._embedder = embedder or default_embedder
        self._persist_path = persist_path or DEFAULT_STORE_FILE
        self._auto_persist = auto_persist
        self._next_id = 1
        self._records: Dict[str, VectorDocument] = {}
        self.load_from_disk()

    def add(self, docs: List[VectorDocument]) -> List[str]:
        with self._lock:
            ids = []
            for doc in docs:
                if not doc.id:
                    doc.id = f"vec-{self._next_id}"
                    self._next_id += 1
                if not doc.embedding and doc.text:
                    doc.embedding = self._embedder.embed(doc.text)
                doc.metadata = copy.deepcopy(doc.metadata)
                self._records[doc.id] = doc
                ids.append(doc.id)

            if self._auto_persist:
                self.save_to_disk()
            return ids

    def update(self, doc_id: str, doc: VectorDocument) -> bool:
        with self._lock:
            if doc_id not in self._records:
                return False
            doc.id = doc_id
            if not doc.embedding and doc.text:
                doc.embedding = self._embedder.embed(doc.text)
            doc.metadata = copy.deepcopy(doc.metadata)
            self._records[doc_id] = doc
            if self._auto_persist:
                self.save_to_disk()
            return True

    def delete(self, ids: List[str]) -> bool:
        with self._lock:
            removed = False
            for doc_id in ids:
                if doc_id in self._records:
                    del self._records[doc_id]
                    removed = True
            if removed and self._auto_persist:
                self.save_to_disk()
            return removed

    def get(self, doc_id: str) -> Optional[VectorDocument]:
        with self._lock:
            return self._records.get(doc_id)

    def search_by_text(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        if not query.strip():
            return []
        query_vec = self._embedder.embed(query)
        q_lower = query.lower().strip()

        with self._lock:
            results: List[SearchResult] = []
            for doc_id, doc in self._records.items():
                if not metadata_matches(doc.metadata, filters):
                    continue
                score = cosine_similarity(query_vec, doc.embedding)
                # Boost if exact substring or tokens exist
                if q_lower in doc.text.lower():
                    score = max(score, 0.85) + 0.15
                    score = min(1.0, score)

                results.append(
                    SearchResult(
                        id=doc_id,
                        content=doc.text,
                        score=score,
                        metadata=copy.deepcopy(doc.metadata),
                    )
                )

            results.sort(key=lambda r: r.score, reverse=True)
            if top_k > 0:
                results = results[:top_k]
            return results

    def search_by_metadata(
        self,
        filters: Dict[str, Any],
        top_k: int = 5,
    ) -> List[SearchResult]:
        with self._lock:
            results: List[SearchResult] = []
            for doc_id, doc in self._records.items():
                if not metadata_matches(doc.metadata, filters):
                    continue
                results.append(
                    SearchResult(
                        id=doc_id,
                        content=doc.text,
                        score=1.0,
                        metadata=copy.deepcopy(doc.metadata),
                    )
                )
            if top_k > 0:
                results = results[:top_k]
            return results

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._next_id = 1
            if self._auto_persist:
                self.save_to_disk()

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def save_to_disk(self, path: Optional[Path] = None) -> None:
        target_path = path or self._persist_path
        with self._lock:
            data = {
                "next_id": self._next_id,
                "records": [
                    {
                        "id": doc.id,
                        "text": doc.text,
                        "embedding": doc.embedding,
                        "metadata": doc.metadata,
                    }
                    for doc in self._records.values()
                ],
            }
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"[VectorStore Error] Failed to persist vector store: {e}", flush=True)

    def load_from_disk(self, path: Optional[Path] = None) -> None:
        target_path = path or self._persist_path
        if not target_path.exists():
            return
        with self._lock:
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._next_id = data.get("next_id", 1)
                    self._records = {}
                    for item in data.get("records", []):
                        doc = VectorDocument(
                            id=item["id"],
                            text=item["text"],
                            embedding=item.get("embedding", []),
                            metadata=item.get("metadata", {}),
                        )
                        self._records[doc.id] = doc
            except Exception as e:
                print(f"[VectorStore Notice] Failed to load vector store from disk: {e}", flush=True)


memory_vector_store = MemoryVectorStore()
