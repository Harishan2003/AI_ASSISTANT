# Module: backend.app.memory.short_term
from collections import defaultdict
from threading import Lock

from app.core.llm.models import ChatMessage


class SessionMemory:
    """
    Stores conversation history per session.

    Later this can be replaced with Redis,
    PostgreSQL or ChromaDB without changing
    the ChatService.
    """

    def __init__(self):
        self._sessions = defaultdict(list)
        self._lock = Lock()

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        with self._lock:
            return list(self._sessions[session_id])

    def add_message(
        self,
        session_id: str,
        message: ChatMessage,
    ):
        with self._lock:
            self._sessions[session_id].append(message)

    def clear(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)

    def session_exists(self, session_id: str):
        return session_id in self._sessions


session_memory = SessionMemory()