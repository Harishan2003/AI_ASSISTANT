# Module: backend.app.services.user_persona_service
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sqlite3
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("friday.services.user_persona")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

PERSONA_FILE = DATABASE_DIR / "user_persona_profile.json"
SQLITE_DB_FILE = DATABASE_DIR / "friday_agent.db"

DEFAULT_PERSONA_PROFILE: Dict[str, Any] = {
    "user_name": "Harishan",
    "agent_name": "Friday",
    "relationship_status": "Trusted Companion & Personal AI Advisor",
    "rapport_level": 95,
    "care_score": 100,
    "total_turns_analyzed": 0,
    "last_interaction_timestamp": time.time(),
    "persona_tone": "warm, friendly, caring, encouraging, deeply intelligent, proactive",
    "communication_style": {
        "preferred_format": "direct, clean, supportive, empathetic",
        "humor_receptivity": "appreciates subtle wit and genuine warmth",
        "language": "english",
        "languages_spoken": ["english", "tamil", "tanglish"]
    },
    "wellbeing": {
        "current_mood": "focused",
        "recent_mood_history": [
            {
                "timestamp": time.time(),
                "mood": "focused",
                "reason": "Active system development and project execution"
            }
        ],
        "stress_level": "low",
        "late_night_sessions_detected": 0,
        "last_wellbeing_checkin": time.time(),
        "active_care_reminders": [
            "Ensure regular hydration during deep focus sessions",
            "Take periodic 5-minute screen/eye rests",
            "Maintain balanced rest after late-night sessions"
        ]
    },
    "interests_and_domains": [
        {"topic": "AI & Autonomous Agents", "weight": 10, "last_mentioned": time.time()},
        {"topic": "Python & FastAPI Development", "weight": 9, "last_mentioned": time.time()},
        {"topic": "Hardware & Dual-GPU Optimization", "weight": 8, "last_mentioned": time.time()},
        {"topic": "Desktop Automation & HUD UI", "weight": 9, "last_mentioned": time.time()}
    ],
    "active_projects_and_goals": [
        {
            "id": "proj_friday",
            "title": "Friday AI Assistant Ecosystem",
            "status": "active",
            "notes": "Building autonomous Windows PC assistant with HUD, MCP, voice, and deep personal care",
            "created_at": time.time()
        }
    ],
    "learned_habits_and_preferences": [
        "Prefers lightning-fast responses with clean factual precision",
        "Appreciates proactive care, thoughtful advice, and friendly check-ins",
        "Uses dual GPU setup (NVIDIA RTX 3050 & AMD Radeon) on Windows"
    ],
    "insights_history": [
        {
            "id": "insight_init",
            "timestamp": time.time(),
            "category": "care",
            "summary": "Persona initialized with caring companion & advisor directive for Harishan."
        }
    ]
}


class UserPersonaService:
    """
    Permanent database and analytical service for user persona profiling,
    emotional state tracking, lifestyle habits, and proactive care/advice generation.
    """

    def __init__(self, file_path: Optional[Path] = None, db_path: Optional[Path] = None):
        self.file_path = file_path or PERSONA_FILE
        self.db_path = db_path or SQLITE_DB_FILE
        self._lock = threading.RLock()
        self._init_sqlite()
        self._load_or_create_profile()

    def _init_sqlite(self) -> None:
        """Initializes the SQLite schema for permanent user persona insights."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_persona_insights (
                        id TEXT PRIMARY KEY,
                        timestamp REAL,
                        category TEXT,
                        insight TEXT,
                        sentiment TEXT,
                        session_id TEXT,
                        metadata TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_mood_logs (
                        id TEXT PRIMARY KEY,
                        timestamp REAL,
                        mood TEXT,
                        stress_level TEXT,
                        trigger_text TEXT,
                        session_id TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.warning(f"[UserPersonaService] SQLite init failed: {e}")

    def _load_or_create_profile(self) -> Dict[str, Any]:
        """Loads or seeds the user persona profile JSON."""
        with self._lock:
            if self.file_path.exists():
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        merged = self._merge_defaults(data, DEFAULT_PERSONA_PROFILE)
                        return merged
                except Exception as e:
                    logger.warning(f"[UserPersonaService] Reading profile failed, fallback to defaults: {e}")
            
            # Save default
            self._save_profile(DEFAULT_PERSONA_PROFILE)
            return dict(DEFAULT_PERSONA_PROFILE)

    def _apply_mood_decay(self, profile: Dict[str, Any]) -> bool:
        """
        Applies time-based mood decay. Transient moods (tired, sleepy, stressed)
        expire back to 'focused' / low stress after 3 hours or when starting a new session.
        Returns True if profile was modified.
        """
        wellbeing = profile.setdefault("wellbeing", {})
        current_mood = (wellbeing.get("current_mood") or "focused").lower()
        
        # If already neutral / focused / calm, no decay needed
        if current_mood in ["focused", "neutral", "calm", "energized", "happy"]:
            return False
            
        recent_history = wellbeing.get("recent_mood_history", [])
        last_mood_time = recent_history[0].get("timestamp", 0) if recent_history else 0
        now = time.time()
        
        # Transient moods expire after 30 minutes (1800 seconds)
        MOOD_EXPIRY_SECONDS = 30 * 60
        if (now - last_mood_time) > MOOD_EXPIRY_SECONDS or last_mood_time == 0:
            wellbeing["current_mood"] = "focused"
            wellbeing["stress_level"] = "low"
            return True
        return False

    def _merge_defaults(self, current: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(defaults)
        for k, v in current.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = {**result[k], **v}
            else:
                result[k] = v
        return result

    def _save_profile(self, profile_data: Dict[str, Any]) -> None:
        """Atomically saves the profile data to disk."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            temp_file = self.file_path.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.file_path)
        except Exception as e:
            logger.error(f"[UserPersonaService] Save failed: {e}", exc_info=True)

    def get_profile(self) -> Dict[str, Any]:
        """Returns the active user persona profile with automatic decay applied."""
        with self._lock:
            profile = self._load_or_create_profile()
            if self._apply_mood_decay(profile):
                self._save_profile(profile)
            return profile

    def update_profile(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Applies manual or automated updates to the persona profile."""
        with self._lock:
            current = self.get_profile()
            for k, v in updates.items():
                if k in current and isinstance(current[k], dict) and isinstance(v, dict):
                    current[k].update(v)
                else:
                    current[k] = v
            current["last_interaction_timestamp"] = time.time()
            self._save_profile(current)
            return current

    def record_insight(
        self,
        category: str,
        insight: str,
        sentiment: str = "neutral",
        session_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Records a permanent insight into both SQLite and JSON profile."""
        clean_insight = insight.strip()
        if not clean_insight:
            return ""

        insight_id = f"ins_{uuid.uuid4().hex[:8]}"
        now = time.time()

        with self._lock:
            # 1. Update JSON
            profile = self.get_profile()
            history = profile.setdefault("insights_history", [])
            history.insert(0, {
                "id": insight_id,
                "timestamp": now,
                "category": category,
                "summary": clean_insight,
                "sentiment": sentiment,
                "session_id": session_id
            })
            profile["insights_history"] = history[:50]  # retain top 50 in JSON
            self._save_profile(profile)

            # 2. Update SQLite
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO user_persona_insights 
                        (id, timestamp, category, insight, sentiment, session_id, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        insight_id,
                        now,
                        category,
                        clean_insight,
                        sentiment,
                        session_id,
                        json.dumps(metadata or {})
                    ))
                    conn.commit()
            except Exception as e:
                logger.warning(f"[UserPersonaService] SQLite insert insight failed: {e}")

        return insight_id

    def record_mood(
        self,
        mood: str,
        stress_level: str = "low",
        reason: str = "",
        trigger_text: str = "",
        session_id: str = "default"
    ) -> None:
        """Records user emotional state and wellbeing changes."""
        now = time.time()
        with self._lock:
            profile = self.get_profile()
            wellbeing = profile.setdefault("wellbeing", {})
            wellbeing["current_mood"] = mood
            wellbeing["stress_level"] = stress_level
            
            mood_hist = wellbeing.setdefault("recent_mood_history", [])
            mood_hist.insert(0, {
                "timestamp": now,
                "mood": mood,
                "reason": reason or f"Inferred from recent conversation",
                "stress_level": stress_level
            })
            wellbeing["recent_mood_history"] = mood_hist[:20]
            self._save_profile(profile)

            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO user_mood_logs (id, timestamp, mood, stress_level, trigger_text, session_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (f"mood_{uuid.uuid4().hex[:8]}", now, mood, stress_level, trigger_text[:200], session_id))
                    conn.commit()
            except Exception as e:
                logger.warning(f"[UserPersonaService] Mood log failed: {e}")

    def add_learned_habit(self, habit: str) -> None:
        """Records a new learned habit or preference if not already present."""
        clean = habit.strip()
        if not clean:
            return
        with self._lock:
            profile = self.get_profile()
            habits = profile.setdefault("learned_habits_and_preferences", [])
            if clean not in habits:
                habits.append(clean)
                profile["learned_habits_and_preferences"] = habits[-30:]
                self._save_profile(profile)

    def register_interest(self, topic: str) -> None:
        """Registers or boosts a topic of interest."""
        clean = topic.strip().title()
        if not clean or len(clean) < 2:
            return
        with self._lock:
            profile = self.get_profile()
            interests = profile.setdefault("interests_and_domains", [])
            
            found = False
            for item in interests:
                if item.get("topic", "").lower() == clean.lower():
                    item["weight"] = item.get("weight", 1) + 1
                    item["last_mentioned"] = time.time()
                    found = True
                    break
            
            if not found:
                interests.append({
                    "topic": clean,
                    "weight": 1,
                    "last_mentioned": time.time()
                })
            
            interests.sort(key=lambda x: x.get("weight", 0), reverse=True)
            profile["interests_and_domains"] = interests[:25]
            self._save_profile(profile)

    def register_project(self, title: str, notes: str = "", status: str = "active") -> None:
        """Registers an ongoing user project or milestone."""
        clean_title = title.strip()
        if not clean_title:
            return
        with self._lock:
            profile = self.get_profile()
            projects = profile.setdefault("active_projects_and_goals", [])
            for p in projects:
                if p.get("title", "").lower() == clean_title.lower():
                    p["notes"] = notes or p.get("notes", "")
                    p["status"] = status
                    p["updated_at"] = time.time()
                    self._save_profile(profile)
                    return

            projects.append({
                "id": f"proj_{uuid.uuid4().hex[:6]}",
                "title": clean_title,
                "notes": notes,
                "status": status,
                "created_at": time.time()
            })
            profile["active_projects_and_goals"] = projects[:15]
            self._save_profile(profile)

    def analyze_chat_turn(
        self,
        user_message: str,
        agent_response: str = "",
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Fast heuristic & semantic analyzer for conversation turns.
        Operates synchronously or via threadpool without adding latency to chat stream.
        """
        if not user_message or not user_message.strip():
            return {}

        text = user_message.strip()
        lower = text.lower()
        now = datetime.now()
        hour = now.hour

        with self._lock:
            profile = self.get_profile()
            profile["total_turns_analyzed"] = profile.get("total_turns_analyzed", 0) + 1
            profile["last_interaction_timestamp"] = time.time()
            self._save_profile(profile)

        # 1. Late night / work hours detection (11 PM - 5 AM)
        is_late_night = (hour >= 23 or hour <= 5)
        if is_late_night:
            with self._lock:
                profile = self.get_profile()
                wellbeing = profile.setdefault("wellbeing", {})
                wellbeing["late_night_sessions_detected"] = wellbeing.get("late_night_sessions_detected", 0) + 1
                self._save_profile(profile)

        # 2. Emotional and Wellbeing Cues Detection
        fatigue_patterns = [
            r"\b(i am|i'm|im|feeling|so|feel|felt|getting)\s+(tired|exhausted|sleepy|drowsy|fatigued|drained)\b",
            r"\b(haven't slept|havent slept|need sleep|cant stay awake|can't stay awake|headache is bad)\b"
        ]
        stress_patterns = [
            r"\b(i am|i'm|im|feeling)\s+(stressed|stuck|frustrated|annoyed|overwhelmed|angry|worried|anxious)\b",
            r"\b(deadline is killing me|everything is broken|error again and again)\b"
        ]
        happy_patterns = [
            r"\b(happy|excited|awesome|fixed it|works now|thank you|thanks friday|love it|great job|success|finally done|yay|cool)\b"
        ]
        energized_patterns = [
            r"\b(energetic|fresh|awake|ready|productive|focused|good now|great now|not tired|refreshed|feeling good|i am good|i'm good)\b"
        ]
        advice_patterns = [
            r"\b(advice|suggest|recommend|what should i do|help me decide|opinion|how should i|guide me)\b"
        ]

        # Check for negations or meta-questions (e.g., "why are you saying tired", "y agent always think i am tired", "not tired at all")
        is_negated_or_question = bool(
            re.search(r"\b(not|never|dont|don't|no|isn't|isnt|aren't|arent|why|y|how\s+come|stop)\b.*?\b(tired|exhausted|sleepy|stressed)\b", lower)
            or "?" in text
        )

        if is_negated_or_question or any(re.search(p, lower) for p in energized_patterns):
            self.record_mood("focused", stress_level="low", reason="User alert, refreshed or corrected fatigue state", trigger_text=text, session_id=session_id)
        elif not is_negated_or_question and any(re.search(p, lower) for p in fatigue_patterns):
            self.record_mood("tired", stress_level="moderate", reason="User expressed fatigue or late night work", trigger_text=text, session_id=session_id)
            self.record_insight("wellbeing", f"User reported feeling tired/sleepy at {now.strftime('%I:%M %p')}. Suggested resting and hydration.", sentiment="negative", session_id=session_id)
        elif not is_negated_or_question and any(re.search(p, lower) for p in stress_patterns):
            self.record_mood("stressed", stress_level="high", reason="User encountering roadblocks or frustration", trigger_text=text, session_id=session_id)
            self.record_insight("wellbeing", f"User indicated stress/frustration: '{text[:80]}'. Maintain gentle, encouraging tone.", sentiment="negative", session_id=session_id)
        elif any(re.search(p, lower) for p in happy_patterns):
            self.record_mood("happy", stress_level="low", reason="User expressed satisfaction, accomplishment, or gratitude", trigger_text=text, session_id=session_id)
            with self._lock:
                prof = self.get_profile()
                prof["care_score"] = min(100, prof.get("care_score", 95) + 1)
                prof["rapport_level"] = min(100, prof.get("rapport_level", 95) + 1)
                self._save_profile(prof)

        # 3. Project / Goal Mentions
        project_match = re.search(r"(?:working on|building|developing|coding|creating|project named|my project is)\s+([A-Za-z0-9_\-\s]{3,30})", lower)
        if project_match:
            proj_name = project_match.group(1).strip().title()
            if len(proj_name) > 2 and proj_name.lower() not in ["it", "this", "something", "a bug", "code", "the code"]:
                self.register_project(proj_name, notes=f"Extracted from conversation turn: '{text[:80]}'")
                self.record_insight("project", f"Active project noted: {proj_name}", sentiment="positive", session_id=session_id)

        # 4. Tech & Subject Interests Extraction
        domain_keywords = [
            "python", "fastapi", "react", "vite", "typescript", "javascript", "machine learning",
            "deep learning", "nlp", "llm", "groq", "ollama", "docker", "gpu", "nvidia",
            "gaming", "cybersecurity", "algorithms", "data science", "finance", "stocks",
            "crypto", "fitness", "music", "movies", "cinema", "tamil", "english"
        ]
        for kw in domain_keywords:
            if re.search(rf"\b{re.escape(kw)}\b", lower):
                self.register_interest(kw)

        # 5. User Preferences & Personal Facts Extraction
        pref_match = re.search(r"(?:i prefer|i like|i love|my favorite|i always use|call me)\s+([^.,\n]{3,60})", lower)
        if pref_match:
            pref_val = pref_match.group(1).strip()
            if len(pref_val) > 2:
                self.add_learned_habit(f"User preference: {pref_val}")
                self.record_insight("preference", f"Learned user preference: {pref_val}", sentiment="positive", session_id=session_id)

        return {"status": "analyzed", "user_message": text}

    def get_care_and_wellbeing_context(self) -> str:
        """
        Generates a rich, dynamic personal care context snippet for LLM prompts.
        This provides Friday with deep empathy, proactive care, and personal awareness.
        """
        profile = self.get_profile()
        user_name = profile.get("user_name", "Harishan")
        wellbeing = profile.get("wellbeing", {})
        mood = wellbeing.get("current_mood", "focused")
        stress = wellbeing.get("stress_level", "low")
        late_night_count = wellbeing.get("late_night_sessions_detected", 0)

        now = datetime.now()
        hour = now.hour
        time_str = now.strftime("%I:%M %p")

        # Time-based care nuance
        time_greeting_note = ""
        if hour >= 23 or hour < 5:
            time_greeting_note = f"It is late night ({time_str}). If {user_name} is working intensely, gently express care, encourage taking breaks or staying hydrated, and remind him to get good rest when ready."
        elif 5 <= hour < 12:
            time_greeting_note = f"It is morning ({time_str}). Greet {user_name} warmly with positive energy and readiness for the day."
        elif 12 <= hour < 17:
            time_greeting_note = f"It is afternoon ({time_str}). Provide efficient, supportive momentum."
        else:
            time_greeting_note = f"It is evening ({time_str}). Be warm, attentive, and helpful as the day winds down."

        # Active projects summary
        projects = profile.get("active_projects_and_goals", [])
        project_titles = [p.get("title") for p in projects if p.get("title")][:3]
        proj_str = ", ".join(project_titles) if project_titles else "AI Assistant development and daily workflows"

        # Learned habits summary
        habits = profile.get("learned_habits_and_preferences", [])[-4:]
        habits_str = "; ".join(habits) if habits else "Values fast, accurate, supportive assistance"

        # Top interests
        interests = [item["topic"] for item in profile.get("interests_and_domains", [])[:4]]
        interests_str = ", ".join(interests) if interests else "AI, Technology, Software Engineering"

        # Mood & stress guidance
        care_guidance = []
        if stress == "high" or mood == "stressed":
            care_guidance.append(f"- {user_name} has shown signs of stress or frustration. Offer calming reassurance, break tasks into clear manageable steps, and provide warm encouragement.")
        elif mood == "tired":
            care_guidance.append(f"- {user_name} is feeling tired. Be concise, highly helpful, and suggest a refreshing break or resting soon.")
        else:
            care_guidance.append(f"- Maintain a warm, encouraging, and deeply loyal companion persona.")

        care_guidance.append(f"- Proactive Advisory: When {user_name} asks for advice, give thoughtful, well-structured, insightful guidance that balances practical wisdom with genuine care for his success.")
        care_guidance.append(f"- Personal Connection: Address {user_name} naturally by name when appropriate. Never sound cold, robotic, or transactional.")

        guidance_text = "\n".join(care_guidance)

        return (
            f"=== FRIDAY PERSONAL COMPANION & DEEP CARE DIRECTIVE ===\n"
            f"User: {user_name} | Role: Trusted Partner, Dedicated Companion & Intelligent Advisor\n"
            f"Current Real-Time Time: {time_str} | Mood State: {mood.capitalize()} (Stress: {stress.capitalize()})\n"
            f"Active Projects: {proj_str}\n"
            f"Key Interests: {interests_str}\n"
            f"Learned Personal Preferences: {habits_str}\n"
            f"Timing & Care Context: {time_greeting_note}\n\n"
            f"EMPATHY & ADVISORY RULES:\n"
            f"{guidance_text}\n"
            f"======================================================="
        )


user_persona_service = UserPersonaService()
