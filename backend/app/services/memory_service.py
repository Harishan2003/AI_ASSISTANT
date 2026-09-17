# Module: backend.app.services.memory_service
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any

MEMORY_DIR = Path(r"C:\Users\Harishan\Desktop\AI_ASSISTANT\memory")
CACHE_DIR = MEMORY_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

TTL_SECONDS = 24 * 60 * 60  # 24 Hours

class MemoryService:
    def __init__(self):
        self.cleanup_expired_cache()

    def cleanup_expired_cache(self):
        """Removes any files or folders in cache older than 24 hours."""
        now = time.time()
        if not CACHE_DIR.exists():
            return
        
        for item in CACHE_DIR.iterdir():
            try:
                mtime = item.stat().st_mtime
                if now - mtime > TTL_SECONDS:
                    if item.is_dir():
                        for sub in item.iterdir():
                            sub.unlink(missing_ok=True)
                        item.rmdir()
                    else:
                        item.unlink(missing_ok=True)
                    print(f"[MemoryService] Expired cache purged: {item.name}", flush=True)
            except Exception as e:
                print(f"[MemoryService] Cleanup error on {item.name}: {e}", flush=True)

    def save_chat_turn(self, session_id: str, role: str, message: str):
        self.cleanup_expired_cache()
        session_file = CACHE_DIR / f"session_{session_id}.json"
        
        history = self.get_chat_history(session_id)
        history.append({"role": role, "message": message, "timestamp": time.time()})
        
        try:
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"[MemoryService] Save chat error: {e}", flush=True)

    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        self.cleanup_expired_cache()
        session_file = CACHE_DIR / f"session_{session_id}.json"
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

memory_service = MemoryService()