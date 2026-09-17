# Module: backend.app.memory.long_term_memory
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.memory.vector_store import SearchResult, VectorDocument, memory_vector_store

logger = logging.getLogger("friday.memory.long_term")

LONG_TERM_STORAGE = Path(r"C:\Users\Harishan\Desktop\AI_ASSISTANT\memory\cache\long_term_facts.json")
LONG_TERM_STORAGE.parent.mkdir(parents=True, exist_ok=True)


class LongTermMemory:
    """
    Persistent semantic memory for user preferences, entity facts, and learned behaviors.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or LONG_TERM_STORAGE
        self._lock = threading.RLock()
        self._facts: Dict[str, Dict[str, Any]] = {}
        self.load_facts()

    def remember_fact(
        self,
        fact: str,
        category: str = "general",
        user_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        clean_fact = fact.strip()
        if not clean_fact:
            return ""

        with self._lock:
            fact_id = f"fact_{uuid.uuid4().hex[:8]}"
            now = time.time()
            meta = {
                **(metadata or {}),
                "fact_id": fact_id,
                "category": category,
                "user_id": user_id,
                "domain": "fact",
                "created_at": now,
            }

            self._facts[fact_id] = {
                "fact_id": fact_id,
                "fact": clean_fact,
                "category": category,
                "user_id": user_id,
                "created_at": now,
                "metadata": meta,
            }

            # Index into memory vector store for semantic search
            doc = VectorDocument(
                id=fact_id,
                text=clean_fact,
                metadata=meta,
            )
            memory_vector_store.add([doc])
            self.save_facts()
            logger.info(f"[LongTermMemory] Remembered fact [{fact_id}]: {clean_fact[:60]}")
            return fact_id

    def recall_facts(
        self,
        query: str,
        user_id: str = "default",
        top_k: int = 5,
        category: Optional[str] = None,
    ) -> List[SearchResult]:
        filters: Dict[str, Any] = {"domain": "fact"}
        if user_id and user_id != "all":
            filters["user_id"] = user_id
        if category:
            filters["category"] = category

        return memory_vector_store.search_by_text(query=query, top_k=top_k, filters=filters)

    def forget_fact(self, fact_id: str) -> bool:
        with self._lock:
            if fact_id in self._facts:
                del self._facts[fact_id]
                memory_vector_store.delete([fact_id])
                self.save_facts()
                return True
            return False

    def list_facts(self, user_id: str = "default", category: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            results = []
            for item in self._facts.values():
                if user_id and user_id != "all" and item.get("user_id") != user_id:
                    continue
                if category and item.get("category") != category:
                    continue
                results.append(copy_fact := dict(item))
            results.sort(key=lambda x: x.get("created_at", 0), reverse=True)
            return results

    def clear(self, user_id: Optional[str] = None) -> int:
        with self._lock:
            to_delete = []
            for fact_id, item in self._facts.items():
                if user_id is None or item.get("user_id") == user_id:
                    to_delete.append(fact_id)
            for f_id in to_delete:
                del self._facts[f_id]
            memory_vector_store.delete(to_delete)
            self.save_facts()
            return len(to_delete)

    def save_facts(self) -> None:
        with self._lock:
            try:
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.storage_path, "w", encoding="utf-8") as f:
                    json.dump({"facts": list(self._facts.values())}, f, indent=2)
            except Exception as e:
                logger.error(f"[LongTermMemory] Failed saving facts: {e}", exc_info=True)

    def load_facts(self) -> None:
        if not self.storage_path.exists():
            return
        with self._lock:
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._facts = {}
                    for item in data.get("facts", []):
                        f_id = item.get("fact_id")
                        if f_id:
                            self._facts[f_id] = item
                            # Re-index if not present in vector store
                            if not memory_vector_store.get(f_id):
                                memory_vector_store.add([
                                    VectorDocument(
                                        id=f_id,
                                        text=item.get("fact", ""),
                                        metadata=item.get("metadata", {}),
                                    )
                                ])
            except Exception as e:
                logger.warning(f"[LongTermMemory] Load facts error: {e}")


long_term_memory = LongTermMemory()
