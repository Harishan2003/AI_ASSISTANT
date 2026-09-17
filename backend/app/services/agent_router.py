"""
Friday Agent Router

Determines which part of Friday should handle
the user's request.

Router does NOT execute commands.
It only returns the tool name.
"""

from __future__ import annotations

import re


class AgentRouter:

    def __init__(self):
        print("[AgentRouter] Initialized.")

    def route(
        self,
        message: str,
    ) -> str | None:

        if not message:
            return None

        original = str(message).strip()
        if not original:
            return None

        text = self._normalize(original)
        if not text:
            return None

        print()
        print(f"[AgentRouter] Message: {original}")
        print(f"[AgentRouter] Normalized: {text}")

        from app.services.context_service import context_service
        from app.services.context_state import context_state

        # =====================================================
        # 1. SCREENSHOT & CAMERA CAPTURE
        # =====================================================
        if any(k in text for k in ["screenshot", "screen shot", "capture screen", "snip"]):
            print("[AgentRouter] -> take_screenshot")
            return "take_screenshot"

        if any(k in text for k in ["take a photo", "take photo", "take pic", "take a picture", "click photo", "open camera", "capture photo"]):
            print("[AgentRouter] -> take_photo")
            return "take_photo"

        # =====================================================
        # 2. GLOBAL TAB CONTROLS
        # =====================================================
        if any(k in text for k in ["new tab", "new table", "open tab", "open a new tab", "open new tab"]):
            print("[AgentRouter] -> open_new_tab")
            return "open_new_tab"

        if any(k in text for k in ["close tab", "close the tab", "close current tab", "close this tab"]):
            print("[AgentRouter] -> close_current_tab")
            return "close_current_tab"

        # =====================================================
        # 3. EXPLICIT FILE SHARING / ATTACHMENT
        # =====================================================
        file_send_triggers = [
            "send this file", "send the file", "send the selected file",
            "send selected file", "send file", "share this file", "share file",
            "send this document", "send document", "send this folder", "send the selected folder"
        ]
        if any(f in text for f in file_send_triggers):
            match = re.search(r"to\s+([a-zA-Z0-9_]+)", text)
            if match:
                contact_name = match.group(1).strip()
                if contact_name.lower() not in ["whatsapp", "gmail", "chat"]:
                    context_state.set_selected_contact(contact_name)

            context_result = context_service.try_handle_context(text)
            if context_result is not None:
                self._last_context_result = context_result
                return "context_execution"

        # =====================================================
        # 4. EXPLICIT URL / LINK NAVIGATION
        # =====================================================
        if self._is_url_or_link_request(text):
            print("[AgentRouter] -> open_link")
            return "open_link"

        # =====================================================
        # 5. MEDIA & BROWSER SEARCH (Compound browser/media commands)
        # =====================================================
        if self._is_media_or_browser_search_request(text):
            print("[AgentRouter] -> MEDIA & SEARCH: automate_media")
            return "automate_media"

        # =====================================================
        # 6. EXPLICIT APPLICATION / FILE / FOLDER / DRIVE LAUNCH
        # =====================================================
        if self._is_explicit_launch_request(text):
            system_tool = self._get_system_tool(text)
            if system_tool:
                print(f"[AgentRouter] -> EXPLICIT SYSTEM: {system_tool}")
                return system_tool

        # =====================================================
        # 7. ACTIVE APPLICATION CONTEXT ROUTING
        # =====================================================
        informational_starters = [
            "who is", "who are", "what is", "what are", "where is", "where are",
            "why is", "why does", "when is", "when did", "how to", "how do",
            "tell me", "explain", "describe", "can you"
        ]
        is_info_query = any(text.startswith(q) for q in informational_starters)

        if not is_info_query:
            context_result = context_service.try_handle_context(text)
            if context_result is not None:
                print(f"[AgentRouter] -> ACTIVE CONTEXT EXECUTION: {context_result}")
                self._last_context_result = context_result
                return "context_execution"

        # =====================================================
        # 8. CHAT & CALL AUTOMATION
        # =====================================================
        if self._is_chat_automation_request(text):
            print("[AgentRouter] -> CHAT AUTOMATION: automate_chat")
            return "automate_chat"

        # =====================================================
        # 9. DIRECT WEB SEARCH
        # =====================================================
        if self._is_direct_web_search(text):
            print("[AgentRouter] -> web_search")
            return "web_search"

        # =====================================================
        # 10. TIME / CALC / WEATHER
        # =====================================================
        if self._is_time_request(text):
            return "get_current_time"

        if self._is_calculator_request(text):
            return "calculate"

        if self._is_weather_request(text):
            return "weather"

        # =====================================================
        # 11. GENERAL SYSTEM LAUNCHER
        # =====================================================
        system_tool = self._get_system_tool(text)
        if system_tool:
            print(f"[AgentRouter] -> SYSTEM: {system_tool}")
            return system_tool

        # =====================================================
        # 12. NORMAL LLM
        # =====================================================
        print("[AgentRouter] -> normal LLM")
        return None

    def _normalize(
        self,
        message: str,
    ) -> str:
        if message is None:
            return ""

        text = str(message).lower().strip()
        text = re.sub(r"^(?:s|is|as|fridays|friday's|friday s|todays|today's|today s|today|friday)\s+", "", text).strip()

        stt_fixes = {
            "what app": "whatsapp",
            "whats app": "whatsapp",
            "vhs with the blocks": "vj siddhu vlogs",
            "vj sidhu": "vj siddhu",
            "spider man": "spiderman",
            "such": "search",
            "read me": "readme",
            "dot m d": ".md",
            "dot md": ".md",
            "dot txt": ".txt",
            "dot text": ".txt",
            "dot pdf": ".pdf",
            "dot py": ".py",
            "dot docx": ".docx",
            "dot doc": ".doc",
            "gauge file": "edge file",
            "local disk": "local disk",
            "local drive": "drive",
        }

        for wrong, correct in stt_fixes.items():
            text = re.sub(rf"\b{re.escape(wrong)}\b", correct, text)

        noise_patterns = [
            r"\b(?:in\s+)?(?:activated|inactivated|active|current|existing|opening|open|the|depth|ta|window)\s+(?:tab|window|the\s+tab|the\s+open\s+the\s+tab)\b",
            r"\b(?:in\s+depth|in\s+ta|in\s+tab|in\s+existing\s+tab|in\s+current\s+tab)\b",
            r"\b(?:existing|current|active)\s+tab\b",
        ]
        for pat in noise_patterns:
            text = re.sub(pat, "", text, flags=re.IGNORECASE).strip()

        if "whatsapp" in text and any(w in text for w in ["search", "find", "send", "message", "text", "write", "type", "draft"]):
            chained_match = re.search(
                r"(?:search(?:\s+for)?|find)\s+([a-zA-Z0-9_]+)\s+and\s+(send|write|type|draft|message|text)(?:\s+a\s+message|\s+message)?(?:\s*:\s*|\s+that\s+|\s+)(.+)$",
                text
            )
            if chained_match:
                contact = chained_match.group(1).strip()
                action = chained_match.group(2).strip().lower()
                msg = chained_match.group(3).strip()
                if action in ["write", "type", "draft"]:
                    text = f"whatsapp write to {contact}: {msg}"
                else:
                    text = f"whatsapp send to {contact}: {msg}"
            else:
                for prefix in [
                    "open whatsapp and search for",
                    "open whatsapp and search",
                    "open whatsapp and find",
                    "search in whatsapp for",
                    "search whatsapp for",
                    "open whatsapp search",
                ]:
                    if prefix in text:
                        contact = text.split(prefix, 1)[1].replace("in whatsapp", "").replace("on whatsapp", "").strip()
                        contact = re.split(r"\s+and\s+", contact)[0].strip()
                        text = f"search {contact}"
                        break
                else:
                    if "search" in text:
                        contact = text.split("search", 1)[1].replace("in whatsapp", "").replace("on whatsapp", "").replace("whatsapp", "").replace("for", "").strip()
                        contact = re.split(r"\s+and\s+", contact)[0].strip()
                        text = f"search {contact}"

        text = text.replace('"', "").replace("'", "")
        text = re.sub(r"[.,!?;:]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _is_url_or_link_request(self, text: str) -> bool:
        clean = text.lower().strip()
        if re.search(r"https?://[^\s]+", clean):
            return True
        if re.search(r"\b[a-zA-Z0-9-]+\.(com|org|net|in|io|ai|co|edu|gov|dev)\b", clean):
            return True
        if any(clean.startswith(p) for p in ["open link", "open url", "go to link", "visit ", "browse to "]):
            return True
        known_sites = ["youtube", "google", "github", "reddit", "twitter", "x.com", "chatgpt", "linkedin"]
        if any(clean.startswith(act) for act in ["open ", "go to "]):
            target = clean.split(" ", 1)[1].strip()
            if target in known_sites:
                return True
        return False

    def _is_chat_automation_request(self, message: str) -> bool:
        text = message.lower().strip()
        if text.startswith(("did i", "what did i", "have i", "who said")):
            return False
        if "whatsapp" in text and any(w in text for w in ["search", "find", "draft", "write", "send to"]):
            return False
        chat_actions = [
            "message", "msg", "text", "send message", "send a message",
            "tell", "call", "voice call", "video call", "dial", "ring", "send"
        ]
        chat_apps = ["whatsapp", "telegram", "discord", "teams", "signal", "skype", "messenger"]
        has_action = any(re.search(rf"\b{action}\b", text) for action in chat_actions)
        has_app = any(app in text for app in chat_apps)
        return has_action and has_app

    def _is_explicit_launch_request(self, text: str) -> bool:
        if any(w in text for w in ["new tab", "close tab", "screenshot", "screen shot", "photo", "camera", "send this file", "send the selected file", "send selected file", "send file"]):
            return False
        if "whatsapp" in text and any(k in text for k in ["search", "find", "message", "text", "look for", "send", "write"]):
            return False

        explicit_targets = [
            "chrome", "edge", "firefox", "notepad", "calculator", "paint",
            "task manager", "whatsapp", "spiderman", "spider man 2",
            "file explorer", "folder", "directory", "file", "document", "disk", "drive"
        ]
        has_open = any(text.startswith(act) for act in ["open ", "launch ", "start ", "run ", "play "])
        has_target = any(app in text for app in explicit_targets) or any(text.endswith(ext) for ext in [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"])
        return has_open and has_target

    def _is_media_or_browser_search_request(self, message: str) -> bool:
        text = message.lower().strip()
        if any(k in text for k in ["play", "youtube", "watch", "stream", "video", "song"]):
            return True
        search_triggers = [
            r"\bopen chrome and search\b",
            r"\bopen google and search\b",
            r"\bsearch in chrome\b",
            r"\bsearch on google\b",
            r"\bsearch in google\b",
            r"\bsearch on chrome\b",
            r"\bgoogle search\b",
            r"\bsearch youtube for\b",
            r"\bsearch on youtube\b",
        ]
        return any(re.search(pat, text) for pat in search_triggers)

    def _is_direct_web_search(self, message: str) -> bool:
        patterns = (
            "search the web for", "search online for",
            "search the internet for", "look up online", "find online",
        )
        return any(pattern in message for pattern in patterns)

    def _get_system_tool(
        self,
        message: str,
    ) -> str | None:
        text = message.lower().strip()

        if self._is_url_or_link_request(text):
            return "open_link"

        if self._is_file_explorer_request(text):
            return "open_file_explorer"

        drive_path = self._get_drive_request(text)
        if drive_path:
            return "open_path"

        if self._contains_windows_path(text) and self._has_open_action(text):
            return "open_path"

        if any(f in text for f in ["folder", "directory"]) and self._has_open_action(text):
            return "open_folder"

        file_extensions = [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".md", ".csv", ".png", ".jpg"]
        if any(ext in text for ext in file_extensions) or any(k in text for k in ["open file", "open document", "open the file"]):
            return "open_file"

        if self._is_folder_request(text):
            return "open_folder"

        if self._is_application_request(text):
            return "open_application"

        return None

    def _has_open_action(self, message: str) -> bool:
        actions = ("open", "launch", "start", "run", "show", "bring", "play")
        words = set(message.split())
        return any(action in words for action in actions)

    def _is_file_explorer_request(self, message: str) -> bool:
        if not self._has_open_action(message):
            return False
        explorer_names = (
            "file explorer", "files explorer", "fire explorer",
            "tile explorer", "windows explorer", "explorer", "my files",
        )
        return any(name in message for name in explorer_names)

    def _get_drive_request(self, message: str) -> str | None:
        if not self._has_open_action(message):
            return None
        patterns = (
            r"\b([a-z])\s+drive\b",
            r"\bdrive\s+([a-z])\b",
            r"\blocal\s+disk\s+([a-z])\b",
            r"\bdisk\s+([a-z])\b",
            r"\b([a-z])\s*:\s*$",
        )
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                letter = match.group(1).upper()
                return f"{letter}:\\"
        return None

    def _contains_windows_path(self, message: str) -> bool:
        return bool(re.search(r"\b[A-Za-z]:[\\/]", message))

    def _is_folder_request(self, message: str) -> bool:
        if not self._has_open_action(message):
            return False
        folders = (
            "downloads", "download", "documents", "document", "desktop",
            "pictures", "picture", "videos", "video", "music", "onedrive",
        )
        return any(folder in message for folder in folders)

    def _is_application_request(self, message: str) -> bool:
        return self._has_open_action(message)

    def _is_time_request(self, message: str) -> bool:
        patterns = ("what time is it", "current time", "tell me the time", "time now", "what is the time", "whats the time")
        return any(pattern in message for pattern in patterns)

    def _is_calculator_request(self, message: str) -> bool:
        if not self._contains_math_expression(message):
            return False
        patterns = ("calculate", "how much", "solve", "plus", "minus", "multiply", "times", "divide", "percentage", "percent", "square root")
        return any(pattern in message for pattern in patterns)

    def _is_weather_request(self, message: str) -> bool:
        patterns = ("weather", "temperature", "rain today", "will it rain", "is it raining", "forecast")
        return any(pattern in message for pattern in patterns)

    def _contains_math_expression(self, message: str) -> bool:
        math_words = ("plus", "minus", "multiply", "times", "divide", "percentage", "percent", "square root")
        if any(word in message for word in math_words):
            return True
        return bool(re.search(r"\d+\s*[\+\-\*\/\%]\s*\d+", message))


agent_router = AgentRouter()