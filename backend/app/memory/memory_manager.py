# Module: backend.app.memory.memory_manager
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.memory.conversation_memory import (
    MemoryJob,
    MemoryJobStore,
    memory_job_store,
    stable_hash,
)
from app.memory.long_term_memory import LongTermMemory, long_term_memory
from app.memory.profile_memory import ProfileMemory, profile_memory
from app.memory.session_memory import SessionMemory, session_memory
from app.memory.vector_store import (
    MemoryVectorStore,
    SearchResult,
    VectorDocument,
    memory_vector_store,
)

logger = logging.getLogger("friday.memory.manager")


class FridayMemoryManager:
    """
    Unified memory orchestrator for Friday AI Assistant.
    Coordinates short-term session memory, persistent long-term facts,
    profile memory, deterministic vector retrieval, and durable background ingestion.
    """

    def __init__(
        self,
        vector_store: Optional[MemoryVectorStore] = None,
        job_store: Optional[MemoryJobStore] = None,
        long_term: Optional[LongTermMemory] = None,
        profile: Optional[ProfileMemory] = None,
        session: Optional[SessionMemory] = None,
    ):
        self.vector_store = vector_store or memory_vector_store
        self.job_store = job_store or memory_job_store
        self.long_term = long_term or long_term_memory
        self.profile = profile or profile_memory
        self.session = session or session_memory

    async def fetch_memory_context(
        self,
        query: str,
        user_id: str = "default",
        top_k: int = 5,
        min_score: float = 0.35,
    ) -> Dict[str, Any]:
        """
        Retrieve user-scoped relevant memory context (facts + past conversations).
        Returns structured sources and a formatted string ready for LLM prompt augmentation.
        """
        if not query.strip():
            return {"context_text": "", "sources": []}

        try:
            results = await asyncio.to_thread(
                self.vector_store.search_by_text,
                query=query,
                top_k=top_k * 2,
            )

            filtered_sources = []
            for r in results:
                # User scoping: allow if matching user or global
                item_user = r.metadata.get("user_id", "default")
                if user_id != "all" and item_user not in [user_id, "default", "system"]:
                    continue
                if r.score >= min_score:
                    filtered_sources.append({
                        "id": r.id,
                        "content": r.content,
                        "score": round(r.score, 4),
                        "domain": r.metadata.get("domain", "conversation"),
                        "metadata": r.metadata,
                    })

            filtered_sources = filtered_sources[:top_k]

            context_lines = []
            for s in filtered_sources:
                domain_tag = s["domain"].upper()
                context_lines.append(f"[{domain_tag} | Relevance: {int(s['score'] * 100)}%] {s['content']}")

            context_text = "\n".join(context_lines)
            return {
                "context_text": context_text,
                "sources": filtered_sources,
                "count": len(filtered_sources),
            }
        except Exception as e:
            logger.warning(f"[FridayMemoryManager] Memory retrieval failed: {e}", exc_info=True)
            return {"context_text": "", "sources": [], "error": str(e)}

    def ingest_turn_sync(
        self,
        user_query: str,
        agent_response: str,
        user_id: str = "default",
        session_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Synchronously index a conversation turn into the memory vector store."""
        clean_q = user_query.strip()
        clean_a = agent_response.strip()
        if not clean_q and not clean_a:
            return ""

        turn_id = f"turn_{uuid.uuid4().hex[:10]}"
        now = time.time()
        combined_text = f"User: {clean_q}\nFriday: {clean_a}" if clean_a else f"User: {clean_q}"

        meta = {
            **(metadata or {}),
            "turn_id": turn_id,
            "user_id": user_id,
            "session_id": session_id,
            "domain": "conversation",
            "created_at": now,
        }

        doc = VectorDocument(
            id=turn_id,
            text=combined_text,
            metadata=meta,
        )
        self.vector_store.add([doc])
        logger.info(f"[FridayMemoryManager] Ingested turn [{turn_id}] into memory vector store.")
        return turn_id

    async def ingest_turn_async(
        self,
        user_query: str,
        agent_response: str,
        user_id: str = "default",
        session_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[MemoryJob, bool]:
        """
        Asynchronously queue a durable memory ingest job with idempotency deduplication.
        """
        payload = {
            "user_query": user_query,
            "agent_response": agent_response,
            "user_id": user_id,
            "session_id": session_id,
            "metadata": metadata or {},
        }
        idempotency_fields = {
            "user_id": user_id,
            "content_hash": stable_hash({
                "q": user_query.strip(),
                "a": agent_response.strip(),
                "session": session_id,
            }),
        }

        job, created = self.job_store.enqueue(
            job_type="memory_ingest",
            payload=payload,
            idempotency_fields=idempotency_fields,
            user_id=user_id,
            timeout_seconds=60.0,
            max_attempts=3,
        )

        if created:
            async def _worker():
                return await asyncio.to_thread(
                    self.ingest_turn_sync,
                    user_query=user_query,
                    agent_response=agent_response,
                    user_id=user_id,
                    session_id=session_id,
                    metadata=metadata,
                )

            self.job_store.schedule_job(job, _worker)

        return job, created

    async def batch_ingest_async(
        self,
        items: List[Dict[str, Any]],
        user_id: str = "default",
    ) -> Tuple[MemoryJob, bool]:
        """
        Batch asynchronous ingest for multiple conversation turns.
        """
        payload = {"items": items, "user_id": user_id}
        idempotency_fields = {
            "user_id": user_id,
            "content_hash": stable_hash(items),
        }

        job, created = self.job_store.enqueue(
            job_type="memory_batch_ingest",
            payload=payload,
            idempotency_fields=idempotency_fields,
            user_id=user_id,
            timeout_seconds=max(60.0, float(len(items) * 30.0)),
            max_attempts=3,
        )

        if created:
            async def _batch_worker():
                results = []
                for item in items:
                    q = item.get("user_query") or item.get("query") or item.get("message") or ""
                    a = item.get("agent_response") or item.get("response") or item.get("answer") or ""
                    s_id = item.get("session_id", "default")
                    u_id = item.get("user_id", user_id)
                    t_id = await asyncio.to_thread(
                        self.ingest_turn_sync,
                        user_query=q,
                        agent_response=a,
                        user_id=u_id,
                        session_id=s_id,
                    )
                    results.append({"turn_id": t_id, "success": bool(t_id)})
                return {"ingested_count": len(results), "results": results}

            self.job_store.schedule_job(job, _batch_worker)

        return job, created

    def search_memory(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        return self.vector_store.search_by_text(query=query, top_k=top_k, filters=filters)

    def clear_all_memory(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Clear vector store, long term facts, and session stores."""
        facts_cleared = self.long_term.clear(user_id=user_id)
        if user_id is None or user_id == "all":
            self.vector_store.clear()
        return {"status": "cleared", "facts_cleared": facts_cleared}


friday_memory_manager = FridayMemoryManager()
