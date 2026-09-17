# Module: backend.app.agents.memory_agent
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from app.memory.long_term_memory import long_term_memory
from app.memory.memory_manager import friday_memory_manager
from app.memory.profile_memory import profile_memory
from app.services.conversation_memory_service import conversation_memory_service

logger = logging.getLogger("friday.agents.memory")


class MemoryAgent:
    """
    Dedicated agent for explicit memory commands:
    - Storing facts ("remember that...", "remember the number 5", "note down that...")
    - Recalling facts ("what is the number I told you to remember", "what did I tell you", "what do you remember")
    - Inspecting last conversation turns ("what is the last conversation between you and me", "what did we just discuss")
    - Forgetting/clearing specific memories
    """

    def __init__(self):
        self.name = "MemoryAgent"

    async def handle_query(
        self,
        query: str,
        user_id: str = "default",
        session_id: str = "default",
        past_turns: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        raw_query = query.strip()
        clean = raw_query.lower()

        # 1. Storing explicit memories / facts
        remember_patterns = [
            r"^remember\s+that\s+(?P<fact>.+)$",
            r"^remember\s+(?P<fact>.+)$",
            r"^please\s+remember\s+(?P<fact>.+)$",
            r"^note\s+down\s+that\s+(?P<fact>.+)$",
            r"^keep\s+in\s+mind\s+that\s+(?P<fact>.+)$",
            r"^save\s+fact\s+(?P<fact>.+)$",
        ]
        for pattern in remember_patterns:
            match = re.match(pattern, raw_query, re.IGNORECASE)
            if match:
                raw_fact = match.group("fact").strip()
                # Determine category
                category = "number" if any(char.isdigit() for char in raw_fact) else "user_preference"
                fact_id = long_term_memory.remember_fact(
                    fact=raw_fact,
                    category=category,
                    user_id=user_id,
                )
                return f"I've committed that to memory, boss: \"{raw_fact}\"."

        # 2. Last conversation / previous turns query
        last_conv_patterns = [
            r"(what|what's|whats)\s+(is|was)\s+(the|our)\s+(last|previous|recent)\s+(conversation|chat|discussion|exchange|message)",
            r"what\s+did\s+(we|you\s+and\s+i)\s+(just|last|previously|earlier)\s+(talk|discuss|chat)\s+about",
            r"what\s+was\s+the\s+last\s+thing\s+(i|we)\s+(said|talked\s+about)",
            r"show\s+(me\s+)?(the\s+)?(last|previous)\s+(conversation|exchange)",
        ]
        if any(re.search(p, clean) for p in last_conv_patterns):
            # Fetch recent turns from conversation memory service or passed history
            all_messages = []
            if session_id and session_id != "default":
                try:
                    all_messages = await conversation_memory_service.get_messages(session_id, limit=10)
                except Exception:
                    all_messages = []
            
            if not all_messages and past_turns:
                all_messages = past_turns

            # Exclude current query
            filtered_turns = [
                m for m in all_messages
                if m.get("content", m.get("message", "")).strip().lower() != clean
            ]

            if not filtered_turns:
                return "This is the start of our session, boss. We don't have any prior exchanges recorded yet."

            # Get the last 1 or 2 turns (User + Assistant exchange)
            recent_exchanges = filtered_turns[-4:]
            formatted_turns = []
            for t in recent_exchanges:
                role = t.get("role", "user")
                role_label = "User" if role == "user" else "Friday"
                text = t.get("content") or t.get("message") or ""
                if text:
                    formatted_turns.append(f"• **{role_label}:** \"{text}\"")

            return "Here is our recent conversation history, boss:\n\n" + "\n".join(formatted_turns)

        # 3. Recalling specific remembered items (e.g. "what is the number I told you to remember")
        told_to_remember_patterns = [
            r"what\s+(is|was)\s+the\s+(?P<item>[a-zA-Z0-9_\s]+?)\s+(i\s+)?(told|asked)\s+you\s+to\s+remember",
            r"what\s+did\s+i\s+(tell|ask)\s+you\s+to\s+remember",
            r"what\s+did\s+i\s+ask\s+you\s+to\s+(keep\s+in\s+mind|save|note)",
            r"do\s+you\s+remember\s+(what|the\s+[a-zA-Z0-9_\s]+)\s+i\s+(told|asked)\s+you",
            r"what\s+do\s+you\s+remember\s+about\s+(?P<topic>.+)",
            r"what\s+do\s+you\s+know\s+about\s+(?P<topic>.+)",
            r"recall\s+(?P<topic>.+)",
            r"search\s+memory\s+for\s+(?P<topic>.+)",
        ]
        for pattern in told_to_remember_patterns:
            match = re.search(pattern, clean)
            if match:
                topic = match.groupdict().get("topic") or match.groupdict().get("item") or ""
                topic = topic.strip()
                all_facts = long_term_memory.list_facts(user_id=user_id)
                if not all_facts:
                    # Check global or all facts
                    all_facts = long_term_memory.list_facts(user_id="all")

                if topic:
                    # Look for keyword match first
                    matched = [f for f in all_facts if topic in f.get("fact", "").lower() or topic in f.get("category", "").lower()]
                    if not matched:
                        # Vector search
                        vec_results = long_term_memory.recall_facts(topic, user_id=user_id, top_k=4)
                        matched = [{"fact": r.content} for r in vec_results]

                    if matched:
                        facts_text = "\n".join(f"• {f['fact']}" for f in matched)
                        return f"You asked me to remember:\n\n{facts_text}"

                # If no specific topic or asking generally what did I tell you to remember
                if all_facts:
                    facts_text = "\n".join(f"• {f['fact']}" for f in all_facts[:6])
                    return f"Here are the items I have remembered for you, boss:\n\n{facts_text}"
                return "I don't have any specific facts or items stored in memory yet, boss."

        # 4. Forgetting facts
        forget_patterns = [
            r"^forget\s+about\s+(?P<topic>.+)$",
            r"^delete\s+memory\s+about\s+(?P<topic>.+)$",
            r"^remove\s+fact\s+(?P<topic>.+)$",
            r"^clear\s+(all\s+)?(facts|memories)$",
        ]
        for pattern in forget_patterns:
            match = re.match(pattern, raw_query, re.IGNORECASE)
            if match:
                topic = match.groupdict().get("topic", "").strip()
                if not topic or "all" in clean:
                    count = long_term_memory.clear(user_id=user_id)
                    return f"All long-term facts ({count} items) have been cleared, boss."

                matching_facts = long_term_memory.recall_facts(topic, user_id=user_id, top_k=5)
                if matching_facts:
                    deleted = 0
                    for f in matching_facts:
                        if long_term_memory.forget_fact(f.id):
                            deleted += 1
                    return f"Cleared {deleted} memory item(s) related to \"{topic}\", boss."
                return f"No memories found matching \"{topic}\" to forget."

        return None


memory_agent = MemoryAgent()
