# Module: backend.app.services.conversation_memory_service
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.memory.memory_manager import friday_memory_manager

logger = logging.getLogger("friday.services.conversation_memory")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_DIR = BASE_DIR / "database"
CONV_DIR = DATABASE_DIR / "conversations"
CONV_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TTL_DAYS = int(os.getenv("CONVERSATION_TTL_DAYS", "15"))


class ConversationMemoryService:
    """
    Manages persistent JSON conversation storage, TTL expiration, sliding windows,
    as well as semantic vector search and durable ingestion pipelines.
    """

    def __init__(self, storage_dir: Optional[Path] = None, ttl_days: int = DEFAULT_TTL_DAYS):
        self.storage_dir = storage_dir or CONV_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_days = ttl_days
        self.cleanup_expired_conversations()

    def _get_file_path(self, conversation_id: str) -> Path:
        safe_id = "".join(c for c in conversation_id if c.isalnum() or c in "-_")
        return self.storage_dir / f"{safe_id}.json"

    def _load_json(self, file_path: Path) -> Optional[Dict[str, Any]]:
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _save_json(self, file_path: Path, data: Dict[str, Any]) -> None:
        try:
            temp_path = file_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_path.replace(file_path)
        except Exception as e:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception as e2:
                logger.error(f"[ConversationMemory Error] Saving failed: {e2}", exc_info=True)

    def cleanup_expired_conversations(self) -> int:
        now = time.time()
        removed_count = 0
        try:
            for file_path in self.storage_dir.glob("*.json"):
                data = self._load_json(file_path)
                if data:
                    expires_at = data.get("expires_at", 0)
                    if now > expires_at:
                        file_path.unlink(missing_ok=True)
                        removed_count += 1
        except Exception as e:
            logger.warning(f"[ConversationMemory Notice] Cleanup error: {e}")
        return removed_count

    async def create_conversation(self, title: Optional[str] = None) -> Dict[str, Any]:
        self.cleanup_expired_conversations()
        conv_id = "conv_" + uuid.uuid4().hex[:12]
        now = time.time()
        expires_at = now + (self.ttl_days * 86400)

        conv_data = {
            "conversation_id": conv_id,
            "title": title or "New Chat",
            "created_at": now,
            "updated_at": now,
            "expires_at": expires_at,
            "messages": [],
        }

        file_path = self._get_file_path(conv_id)
        self._save_json(file_path, conv_data)
        return conv_data

    async def list_conversations(self) -> List[Dict[str, Any]]:
        self.cleanup_expired_conversations()
        conversations = []
        try:
            for file_path in self.storage_dir.glob("*.json"):
                data = self._load_json(file_path)
                if data:
                    conversations.append({
                        "conversation_id": data["conversation_id"],
                        "title": data.get("title", "New Chat"),
                        "created_at": data.get("created_at", 0),
                        "updated_at": data.get("updated_at", 0),
                        "message_count": len(data.get("messages", [])),
                    })
            conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        except Exception as e:
            logger.error(f"[ConversationMemory Error] Listing failed: {e}", exc_info=True)
        return conversations

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        file_path = self._get_file_path(conversation_id)
        data = self._load_json(file_path)
        if not data:
            return None

        # Sliding expiration refresh on access
        now = time.time()
        data["expires_at"] = now + (self.ttl_days * 86400)
        self._save_json(file_path, data)
        return data

    def _sanitize_message_content(self, content: str) -> str:
        """Strips out massive base64 payloads and replaces with static server image URLs to keep JSON tiny and fast."""
        if not content:
            return ""
        if "data:image/" in content and "base64," in content:
            # Extract image filename if path is present in markdown tag
            path_match = re.search(r'path=([^\]|]+)', content)
            if path_match:
                img_path = path_match.group(1).strip()
                filename = Path(img_path).name
                server_url = f"http://localhost:8000/api/v1/images/{filename}"
                clean_content = re.sub(r'\(data:image\/[a-zA-Z]+;base64,[^\)]+\)', f'({server_url})', content)
                return clean_content
        return content

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        index_vector: bool = True,
    ) -> Optional[Dict[str, Any]]:
        file_path = self._get_file_path(conversation_id)
        data = self._load_json(file_path)
        if not data:
            data = {
                "conversation_id": conversation_id,
                "title": "New Chat",
                "created_at": time.time(),
                "updated_at": time.time(),
                "expires_at": time.time() + (self.ttl_days * 86400),
                "messages": [],
            }

        sanitized_content = self._sanitize_message_content(content)

        # Skip duplicate adjacent message additions
        if data["messages"]:
            last_msg = data["messages"][-1]
            if last_msg.get("role") == role and last_msg.get("content") == sanitized_content:
                return last_msg

        now = time.time()
        msg_id = "msg_" + uuid.uuid4().hex[:10]
        new_msg = {
            "message_id": msg_id,
            "role": role,
            "content": sanitized_content,
            "created_at": now,
        }

        data["messages"].append(new_msg)
        data["updated_at"] = now
        data["expires_at"] = now + (self.ttl_days * 86400)

        # Auto-generate title from first user message
        if role == "user" and (data.get("title") == "New Chat" or not data.get("title")):
            clean_title = sanitized_content.strip().replace("\n", " ")
            if len(clean_title) > 45:
                clean_title = clean_title[:42] + "..."
            data["title"] = clean_title

        self._save_json(file_path, data)

        # Automatically index into Friday's semantic memory vector store
        if index_vector and sanitized_content.strip():
            try:
                friday_memory_manager.ingest_turn_sync(
                    user_query=sanitized_content if role == "user" else "",
                    agent_response=sanitized_content if role != "user" else "",
                    session_id=conversation_id,
                    metadata={"role": role, "conversation_id": conversation_id, "message_id": msg_id},
                )
            except Exception as ex:
                logger.warning(f"[ConversationMemory] Vector indexing notice: {ex}")

        return new_msg

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        before_message_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conv = await self.get_conversation(conversation_id)
        if not conv:
            return []
        messages = conv.get("messages", [])
        if before_message_id:
            idx = next((i for i, m in enumerate(messages) if m["message_id"] == before_message_id), len(messages))
            messages = messages[:idx]
        return messages[-limit:]

    async def rename_conversation(self, conversation_id: str, title: str) -> bool:
        file_path = self._get_file_path(conversation_id)
        data = self._load_json(file_path)
        if not data:
            return False
        data["title"] = title.strip()[:60] or "New Chat"
        data["updated_at"] = time.time()
        self._save_json(file_path, data)
        return True

    async def delete_conversation(self, conversation_id: str) -> bool:
        file_path = self._get_file_path(conversation_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def clear_messages(self, conversation_id: str) -> bool:
        file_path = self._get_file_path(conversation_id)
        data = self._load_json(file_path)
        if not data:
            return False
        data["messages"] = []
        data["updated_at"] = time.time()
        self._save_json(file_path, data)
        return True

    # --- ENTERPRISE SEMANTIC MEMORY ADAPTERS ---
    async def fetch_relevant_memory(
        self,
        query: str,
        user_id: str = "default",
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant memory sources for context augmentation in conversation turns.
        """
        return await friday_memory_manager.fetch_memory_context(
            query=query,
            user_id=user_id,
            top_k=top_k,
        )

    async def ingest_conversation(
        self,
        query: str,
        answer_text: str,
        user_id: str = "default",
        session_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Asynchronously ingest a conversation turn into memory with durable job tracking.
        """
        job, created = await friday_memory_manager.ingest_turn_async(
            user_query=query,
            agent_response=answer_text,
            user_id=user_id,
            session_id=session_id,
        )
        return {
            "success": True,
            "job_id": job.job_id,
            "status": job.status.value,
            "created": created,
            "status_url": f"/api/v1/memory/jobs/{job.job_id}/status",
        }


conversation_memory_service = ConversationMemoryService()