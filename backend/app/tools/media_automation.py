"""
Friday Media & Web Playback Automation Tool

Handles playing media on YouTube, Spotify, and executing browser search queries across Google and Chrome.
"""

from __future__ import annotations

import re
import urllib.parse
import webbrowser


class MediaAutomationTool:

    def parse_command(self, message: str) -> dict[str, str | None]:
        text = str(message).lower().strip()

        # -----------------------------------------------------
        # 1. Phonetic STT Corrections
        # -----------------------------------------------------
        text = text.replace("vhs with the blocks", "vj siddhu vlogs")
        text = text.replace("vj sidhu", "vj siddhu")
        text = text.replace("whats up", "whatsapp").replace("what's up", "whatsapp")

        # -----------------------------------------------------
        # 2. Clean Wake Words & Salutations
        # -----------------------------------------------------
        text = re.sub(
            r"^\s*(friday|hey friday|hello friday|freddy)\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        # -----------------------------------------------------
        # 3. Detect Platform (YouTube vs Spotify vs Google Search)
        # -----------------------------------------------------
        is_spotify = "spotify" in text
        is_youtube = any(
            k in text for k in ["youtube", "play", "watch", "video", "song", "stream"]
        ) and not is_spotify

        if is_spotify:
            platform = "spotify"
        elif is_youtube:
            platform = "youtube"
        else:
            platform = "google"

        # -----------------------------------------------------
        # 4. Clean Compound Search Prefixes
        # -----------------------------------------------------
        # Handles prefixes like: "open chrome and search...", "open google and find..."
        query = re.sub(
            r"^\s*(open chrome and|open google and|open browser and|open youtube and|open spotify and)\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        # Strip action keywords: "search for", "search", "play", "watch", "find"
        query = re.sub(
            r"^\s*(search for|search|play|watch|find|look up|show me)\s+",
            "",
            query,
            flags=re.IGNORECASE,
        ).strip()

        # Strip trailing platform keywords: "... in youtube", "... on google"
        query = re.sub(
            r"\s+(on|in|using)\s+(youtube|chrome|google|spotify|browser)$",
            "",
            query,
            flags=re.IGNORECASE,
        ).strip()

        return {
            "query": query,
            "platform": platform,
        }

    def execute(self, user_message: str) -> str:
        parsed = self.parse_command(user_message)
        query = parsed["query"]
        platform = parsed["platform"]

        print()
        print("[MediaAutomation] EXECUTING WEB/MEDIA AUTOMATION:")
        print(f"  Platform : {platform}")
        print(f"  Query    : {query}")

        if not query:
            return "Please tell me what you want to search or play."

        encoded_query = urllib.parse.quote(query)

        # -----------------------------------------------------
        # Execute Web/Media Dispatch
        # -----------------------------------------------------
        if platform == "youtube":
            if not query or query.lower() in ["youtube", "open youtube", "browse youtube"]:
                webbrowser.open("https://www.youtube.com")
                return "Opened Google Chrome and navigated to YouTube."
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            webbrowser.open(url)
            return f"Opened Google Chrome and searched for '{query}' on YouTube."

        elif platform == "spotify":
            if not query or query.lower() in ["spotify", "open spotify"]:
                webbrowser.open("https://open.spotify.com")
                return "Opened Spotify."
            url = f"https://open.spotify.com/search/{encoded_query}"
            webbrowser.open(url)
            return f"Playing '{query}' on Spotify."

        else:
            url = f"https://www.google.com/search?q={encoded_query}"
            webbrowser.open(url)
            return f"Opened Google Chrome and searched for '{query}'."


# Singleton Instance
media_automation_tool = MediaAutomationTool()


def automate_media(user_message: str) -> str:
    return media_automation_tool.execute(user_message)