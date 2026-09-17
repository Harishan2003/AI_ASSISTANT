# Module: backend.app.memory.profile_memory
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("friday.memory.profile")

PROFILE_FILE = Path(r"C:\Users\Harishan\Desktop\AI_ASSISTANT\database\user_profile.json")
PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_PROFILE: Dict[str, Any] = {
    "name": "Harishan",
    "agent_name": "Friday",
    "wake_word": "friday",
    "age": "",
    "email": "",
    "city": "",
    "preferences": {
        "theme": "dark",
        "voice": "en_US-amy-medium",
        "speed": 1.0,
        "language": "english",
        "auto_speech": True,
    },
}


class ProfileMemory:
    """
    Manages user profile, personality, and operational preferences.
    """

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or PROFILE_FILE
        self._lock = threading.RLock()

    def get_profile(self) -> Dict[str, Any]:
        with self._lock:
            if self.file_path.exists():
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        merged = {**DEFAULT_PROFILE, **data}
                        if "preferences" in data and isinstance(data["preferences"], dict):
                            merged["preferences"] = {**DEFAULT_PROFILE["preferences"], **data["preferences"]}
                        return merged
                except Exception as e:
                    logger.warning(f"[ProfileMemory] Reading profile failed: {e}")
            return dict(DEFAULT_PROFILE)

    def update_profile(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            current = self.get_profile()
            for k, v in updates.items():
                if k == "preferences" and isinstance(v, dict):
                    current["preferences"] = {**current.get("preferences", {}), **v}
                else:
                    current[k] = v

            agent = current.get("agent_name") or current.get("wake_word") or "Friday"
            current["agent_name"] = str(agent).strip()
            current["wake_word"] = str(agent).strip().lower()

            try:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(current, f, indent=2)
                logger.info(f"[ProfileMemory] Profile successfully updated: {current.get('name')}")
            except Exception as e:
                logger.error(f"[ProfileMemory] Failed to write profile: {e}", exc_info=True)
            return current

    def get_formatted_context(self) -> str:
        """Return formatted user context string for LLM system prompt."""
        p = self.get_profile()
        lines = [f"User Name: {p.get('name', 'Harishan')}"]
        if p.get("age"):
            lines.append(f"Age: {p.get('age')}")
        if p.get("email"):
            lines.append(f"Email: {p.get('email')}")
        if p.get("city"):
            lines.append(f"Location: {p.get('city')}")
        lines.append(f"AI Assistant Name: {p.get('agent_name', 'Friday')}")
        return "\n".join(lines)


profile_memory = ProfileMemory()
