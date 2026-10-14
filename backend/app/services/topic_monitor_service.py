"""
Friday AI Assistant - Autonomous Topic & News Monitoring Service.
Permanently tracks news, public developments, policies, and topics that Friday promised
to 'keep monitoring' or that the user requested to follow.

Periodically queries live web feeds in the background, detects significant developments,
delivers native Windows toast notifications, publishes WebSocket updates, and informs
Harishan proactively during chat sessions.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("friday.services.topic_monitor")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
MONITOR_FILE = DATABASE_DIR / "monitored_topics.json"


class TopicMonitorService:
    """
    Autonomous background watcher for user topics, news stories, and policy developments.
    Ensures that promises like "I'll keep monitoring for official statements" are backed
    by real background tracking and proactive user notifications.
    """

    def __init__(self, check_interval_minutes: int = 45):
        self.check_interval_seconds = check_interval_minutes * 60
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._topics: List[Dict[str, Any]] = self._load_topics()

    def _load_topics(self) -> List[Dict[str, Any]]:
        """Loads registered topics from JSON file."""
        if not MONITOR_FILE.exists():
            return []
        try:
            with open(MONITOR_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("topics", [])
        except Exception as e:
            logger.error(f"[TopicMonitor] Error loading topics: {e}")
            return []

    def _save_topics(self) -> None:
        """Saves registered topics atomically."""
        try:
            temp_file = MONITOR_FILE.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump({"topics": self._topics, "updated_at": datetime.now().isoformat()}, f, indent=2)
            temp_file.replace(MONITOR_FILE)
        except Exception as e:
            logger.error(f"[TopicMonitor] Error saving topics: {e}")

    def register_topic(
        self,
        title: str,
        search_query: str,
        initial_summary: str = "",
        keywords: Optional[List[str]] = None,
        source: str = "assistant_promise"
    ) -> Dict[str, Any]:
        """
        Registers a new topic to monitor.
        If a very similar topic is already being monitored, updates its query/summary.
        """
        with self._lock:
            # Check for existing matching topic
            title_lower = title.lower().strip()
            for t in self._topics:
                if t.get("status") == "active":
                    existing_title = t.get("title", "").lower().strip()
                    if title_lower in existing_title or existing_title in title_lower:
                        t["last_checked"] = datetime.now().isoformat()
                        if initial_summary:
                            t["last_summary"] = initial_summary
                        self._save_topics()
                        logger.info(f"[TopicMonitor] Updated existing topic: {t['title']}")
                        return t

            topic_id = f"top_{uuid.uuid4().hex[:8]}"
            now_iso = datetime.now().isoformat()
            new_topic = {
                "id": topic_id,
                "title": title.strip(),
                "search_query": search_query.strip(),
                "keywords": keywords or [],
                "created_at": now_iso,
                "last_checked": now_iso,
                "last_headline": "",
                "last_summary": initial_summary.strip(),
                "status": "active",
                "source": source,
                "updates": [],
                "unnotified_updates": []
            }
            self._topics.append(new_topic)
            self._save_topics()
            logger.info(f"[TopicMonitor] Successfully registered new topic to monitor: {title} (ID: {topic_id})")
            return new_topic

    def auto_register_from_interaction(self, user_query: str, agent_reply: str) -> Optional[Dict[str, Any]]:
        """
        Inspects an interaction to detect if:
        1. Friday explicitly promised to monitor something:
           e.g. "I'll keep monitoring for any official press releases..."
        2. Or the user explicitly asked Friday to monitor/track:
           e.g. "keep monitoring this", "track this story", "let me know when there's an update"
        """
        if not agent_reply:
            return None

        reply_lower = agent_reply.lower()
        query_lower = (user_query or "").lower()

        # Check for monitoring intent triggers
        monitoring_phrases = [
            "keep monitoring", "i'll keep monitoring", "i will keep monitoring",
            "keep you updated", "i'll monitor", "i will monitor", "tracking this",
            "keep tracking", "watch for any official", "watch for updates",
            "monitor for any official", "monitor this situation"
        ]
        user_track_phrases = [
            "keep monitoring", "track this", "monitor this", "keep an eye on",
            "let me know if there's any update", "let me know if any update",
            "keep me updated on", "alert me if"
        ]

        agent_promised = any(p in reply_lower for p in monitoring_phrases)
        user_requested = any(p in query_lower for p in user_track_phrases)

        if not (agent_promised or user_requested):
            return None

        # Extract target subject
        # 1. Look for topic description in agent reply after "monitoring for" / "monitoring"
        match = re.search(r'(?:monitoring\s+for|monitoring|tracking|watch\s+for)\s+([^\.\n\,]+)', agent_reply, re.IGNORECASE)
        topic_target = match.group(1).strip() if match else ""

        # Clean subject
        topic_target = re.sub(r'^(?:any|the|an|a|official)\s+', '', topic_target, flags=re.IGNORECASE).strip()

        # Combine with user query context if reply target was too vague
        clean_user = re.sub(r'^(?:user|friday)\s*(?:🔊\s*Speak)?\s*[:\-\s]*', '', user_query, flags=re.IGNORECASE).strip()
        clean_user = re.sub(r'\b(?:i think|can you|please|let me know|keep monitoring|track this)\b', '', clean_user, flags=re.IGNORECASE).strip()
        clean_user = ' '.join(clean_user.split())

        title = ""
        search_query = ""

        if clean_user and len(clean_user) >= 6:
            title = clean_user[:80].capitalize()
            search_query = f"{clean_user} latest news update"
        elif topic_target:
            title = topic_target[:80].capitalize()
            search_query = f"{topic_target} latest news update"
        else:
            return None

        # Generate initial summary from agent reply
        sentences = [s.strip() for s in re.split(r'[\.\n]', agent_reply) if len(s.strip()) > 15]
        initial_summary = sentences[0] if sentences else agent_reply[:140]

        return self.register_topic(
            title=title,
            search_query=search_query,
            initial_summary=initial_summary,
            source="conversation_promise"
        )

    def send_desktop_notification(self, title: str, message: str) -> None:
        """Dispatches a native Windows Toast notification."""
        try:
            safe_title = title.replace('"', '`"').replace("'", "''")
            safe_msg = message.replace('"', '`"').replace("'", "''")
            ps_script = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; "
                "$template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02; "
                "$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template); "
                f"$xml.GetElementsByTagName('text')[0].AppendChild($xml.CreateTextNode('Friday Monitor: {safe_title}')) | Out-Null; "
                f"$xml.GetElementsByTagName('text')[1].AppendChild($xml.CreateTextNode('{safe_msg}')) | Out-Null; "
                "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml); "
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Friday AI Assistant').Show($toast);"
            )
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            )
            logger.info(f"[TopicMonitor] Dispatched native Windows Toast for: {title}")
        except Exception as e:
            logger.debug(f"[TopicMonitor] Toast notification notice: {e}")

    async def check_topic_for_updates(self, topic: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes a targeted news and web search for the topic.
        Compares findings with last known summary to identify fresh developments.
        """
        search_q = topic.get("search_query") or topic.get("title")
        if not search_q:
            return None

        try:
            from app.services.web_search_context import gather_all_web_context
            fresh_context = await gather_all_web_context(f"{search_q} latest breaking news")
            if not fresh_context or len(fresh_context) < 80:
                return None

            # Extract headlines or key update snippets
            lines = [l.strip() for l in fresh_context.split("\n") if l.strip().startswith(("- **", "###", "1.", "2."))]
            first_headline = ""
            for l in lines:
                clean_line = re.sub(r'[\*\#\-]', '', l).strip()
                if len(clean_line) > 15:
                    first_headline = clean_line[:140]
                    break

            if not first_headline:
                first_headline = fresh_context[:120].strip()

            last_headline = topic.get("last_headline", "")
            now_iso = datetime.now().isoformat()
            topic["last_checked"] = now_iso

            # Detect if a significant new development is mentioned
            # (Headline differs noticeably from previously seen headline)
            if first_headline and first_headline.lower() != last_headline.lower():
                update_item = {
                    "timestamp": now_iso,
                    "headline": first_headline,
                    "summary": fresh_context[:350].strip()
                }
                topic["last_headline"] = first_headline
                topic["last_summary"] = update_item["summary"]
                topic["updates"].append(update_item)
                topic["unnotified_updates"].append(update_item)
                self._save_topics()

                # 1. Trigger desktop notification
                self.send_desktop_notification(
                    title=topic["title"],
                    message=f"New update: {first_headline}"
                )

                # 2. Publish on EventBus
                try:
                    from app.core.event_bus import event_bus
                    await event_bus.publish("topic.update", {
                        "topic_id": topic["id"],
                        "title": topic["title"],
                        "headline": first_headline,
                        "summary": update_item["summary"]
                    })
                except Exception:
                    pass

                # 3. Ingest into persistent memory
                try:
                    from app.memory.memory_manager import friday_memory_manager
                    friday_memory_manager.long_term.remember_fact(
                        fact=f"Update on monitored topic '{topic['title']}': {first_headline}",
                        category="monitored_topics",
                        user_id="Harishan"
                    )
                except Exception:
                    pass

                logger.info(f"[TopicMonitor] Discovered new update for topic '{topic['title']}': {first_headline}")
                return update_item

        except Exception as e:
            logger.debug(f"[TopicMonitor] Check error for topic {topic.get('title')}: {e}")

        return None

    async def check_all_topics_async(self) -> List[Dict[str, Any]]:
        """Checks all active monitored topics concurrently."""
        active_topics = [t for t in self._topics if t.get("status") == "active"]
        if not active_topics:
            return []

        logger.info(f"[TopicMonitor] Running background check across {len(active_topics)} active monitored topics...")
        results = []
        for t in active_topics:
            upd = await self.check_topic_for_updates(t)
            if upd:
                results.append(upd)
            await asyncio.sleep(1.0)  # Gentle spacing between searches
        return results

    def get_pending_notifications_prompt_context(self) -> str:
        """
        Retrieves unnotified updates to inject into Friday's prompt so Friday
        can proactively inform Harishan on his next conversation turn.
        Once retrieved, marks them as acknowledged.
        """
        with self._lock:
            pending = []
            for t in self._topics:
                unnotified = t.get("unnotified_updates", [])
                if unnotified:
                    latest = unnotified[-1]
                    pending.append(
                        f"- Monitored Topic: \"{t.get('title')}\"\n"
                        f"  Latest Development: {latest.get('headline')}\n"
                        f"  Summary: {latest.get('summary')}"
                    )
                    t["unnotified_updates"] = []

            if pending:
                self._save_topics()
                return (
                    "=== PROACTIVE MONITORED TOPIC NOTIFICATIONS FOR HARISHAN ===\n"
                    "You have been actively tracking the following topics in the background and found verified new updates:\n"
                    + "\n\n".join(pending) + "\n\n"
                    "INSTRUCTION: Naturally inform Harishan about this update as his trusted assistant who has been keeping an eye on it for him!\n"
                    "============================================================"
                )
        return ""

    def get_active_topics_summary(self) -> str:
        """Returns a natural language summary of all currently tracked topics."""
        active = [t for t in self._topics if t.get("status") == "active"]
        if not active:
            return "I am not currently monitoring any specific news topics. You can ask me to monitor any story or policy, and I will track it in the background."

        lines = [f"I am actively monitoring **{len(active)} topic{'s' if len(active) > 1 else ''}** in the background:"]
        for idx, t in enumerate(active, 1):
            created = t.get("created_at", "")[:10]
            last_head = t.get("last_headline") or t.get("last_summary") or "Tracking for official announcements."
            lines.append(f"{idx}. **{t.get('title')}** (Since {created}):\n   - Current status: {last_head[:140]}")

        lines.append("\nI will automatically notify you whenever an official press release or significant update emerges.")
        return "\n".join(lines)

    def _background_worker(self) -> None:
        """Runs periodic monitoring loop in a background thread with its own event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Initial check 30 seconds after startup
        time.sleep(30)
        while self._running:
            try:
                loop.run_until_complete(self.check_all_topics_async())
            except Exception as e:
                logger.debug(f"[TopicMonitor] Background worker loop note: {e}")

            # Sleep in small increments to allow responsive shutdown
            slept = 0
            while self._running and slept < self.check_interval_seconds:
                time.sleep(5)
                slept += 5

        loop.close()

    def start(self) -> None:
        """Starts the autonomous topic monitoring background worker."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._background_worker, daemon=True, name="FridayTopicMonitor")
            self._thread.start()
            logger.info("[TopicMonitor] Autonomous background topic monitoring service online.")

    def stop(self) -> None:
        """Stops the monitoring thread."""
        self._running = False


topic_monitor_service = TopicMonitorService()
