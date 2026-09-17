"""
Friday Chat & Call Automation Tool

Handles universal messaging and calling automation for Windows desktop applications:
- WhatsApp, Telegram, Discord, Teams, Signal, Skype / Messenger
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from typing import Dict, Optional, Tuple
import pyautogui


class ChatAutomationTool:

    APP_CONFIG = {
        "whatsapp": {"scheme": "whatsapp://", "exe": "WhatsApp.exe"},
        "telegram": {"scheme": "tg://", "exe": "Telegram.exe"},
        "discord": {"scheme": "discord://", "exe": "Discord.exe"},
        "teams": {"scheme": "msteams://", "exe": "ms-teams.exe"},
        "signal": {"scheme": "sgnl://", "exe": "Signal.exe"},
        "skype": {"scheme": "skype:", "exe": "Skype.exe"},
    }

    def __init__(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.25

    def _focus_whatsapp_window(self) -> Optional[Tuple[int, int, int, int]]:
        """Brings WhatsApp to foreground and returns its screen rectangle."""
        try:
            import win32gui
            import win32con

            hwnds = []

            def enum_callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "whatsapp" in title.lower():
                        extra.append(hwnd)

            win32gui.EnumWindows(enum_callback, hwnds)
            if hwnds:
                hwnd = hwnds[0]
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.1)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.2)
                return win32gui.GetWindowRect(hwnd)
        except Exception as e:
            print(f"[ChatAutomation] Focus notice: {e}")

        return None

    def parse_command(self, message: str) -> Dict[str, Optional[str]]:
        text = str(message).lower().strip()

        # 1. Phonetic Normalization
        phonetic_map = {
            r"\bwhats up\b": "whatsapp",
            r"\bwhat's up\b": "whatsapp",
            r"\bwater app\b": "whatsapp",
            r"\bwhat app\b": "whatsapp",
            r"\bwatch up\b": "whatsapp",
            r"\bwatch app\b": "whatsapp",
            r"\bone whatsapp\b": "open whatsapp",
            r"\bher knee\b": "harini",
            r"\bhernie\b": "harini",
            r"\bhurry\b": "harini",
            r"\bhermine\b": "harini",
            r"\bharani\b": "harini",
        }
        for pat, rep in phonetic_map.items():
            text = re.sub(pat, rep, text, flags=re.IGNORECASE)

        # 2. Strip Conversational Noise
        text = re.sub(
            r"^\s*(friday|hey friday|hello friday|freddy|please|can you|could you|i told her|i told|tell her to|tell him to)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        # 3. Detect Platform
        platform = "whatsapp"
        for app in self.APP_CONFIG.keys():
            if app in text:
                platform = app
                break

        # 4. Strict Action Detection (Call vs Video Call vs Message)
        action = "message"
        if re.search(r"\b(video call|facetime)\b", text):
            action = "video_call"
        elif re.search(r"\b(make a call|voice call|phone call|call to|dial|ring)\b", text) or (
            re.search(r"\bcall\b", text) and not re.search(r"\b(message|text|msg|tell|send)\b", text)
        ):
            action = "call"
        else:
            action = "message"

        # 5. Extract Recipient & Message Payload
        recipient = None
        payload = None

        noisy_words = {
            "whatsapp", "telegram", "discord", "teams", "skype", "signal",
            "app", "open", "call", "message", "text", "send", "the", "a", "an",
            "and", "to", "on", "in", "via", "that", "saying", "with", "for", "please"
        }

        match_action = re.search(
            r"(?:message|text|send message to|send to|msg|tell|call)\s+(?:to\s+)?([a-zA-Z0-9_]+)",
            text,
        )
        if match_action:
            cand = match_action.group(1).strip()
            if cand not in noisy_words:
                recipient = cand.capitalize()

        if not recipient:
            match_fallback = re.search(r"(?:to|contact|it's|its)\s+([a-zA-Z0-9_]+)", text)
            if match_fallback:
                cand = match_fallback.group(1).strip()
                if cand not in noisy_words:
                    recipient = cand.capitalize()

        if action == "message":
            payload_match = re.search(r"(?:that|saying|with message|message)\s+(.*)", text)
            if payload_match:
                payload = payload_match.group(1).strip()
            elif recipient:
                pattern_after_name = rf"\b{recipient.lower()}\b\s+(.*)"
                m_after = re.search(pattern_after_name, text)
                if m_after:
                    raw_p = m_after.group(1).strip()
                    raw_p = re.sub(rf"\b(on|in|via)?\s*{platform}\b", "", raw_p, flags=re.IGNORECASE).strip()
                    if raw_p and raw_p not in noisy_words:
                        payload = raw_p

        if payload:
            payload = re.sub(r"^(that|saying|with)\s+", "", payload, flags=re.IGNORECASE).strip()

        return {
            "platform": platform,
            "action": action,
            "recipient": recipient,
            "payload": payload,
        }

    def _trigger_whatsapp_call_robust(self, is_video: bool = False) -> bool:
        """
        Executes WhatsApp voice call using header element traversal & direct coordinate targeting.
        """
        rect = self._focus_whatsapp_window()

        # Step 1: UI Automation Button Invocation
        try:
            from pywinauto import Desktop
            app = Desktop(backend="uia")
            win = app.window(title_re=".*WhatsApp.*")
            if win.exists(timeout=1):
                win.set_focus()
                
                # Check for direct named call buttons in UI tree
                buttons = win.descendants(control_type="Button")
                target_str = "video" if is_video else "call"
                
                for b in buttons:
                    t = (b.window_text() or "").lower()
                    aid = (b.automation_id() or "").lower()
                    
                    if (target_str in t or target_str in aid) and "search" not in t and "attach" not in t:
                        b.click_input()
                        print(f"[ChatAutomation] UI Button triggered: '{b.window_text() or b.automation_id()}'")
                        return True
        except Exception:
            pass

        # Step 2: Keyboard Header Traversal (From active chat text box)
        # Shift+Tab 5 times focuses the Voice Call button in the modern WhatsApp XAML header
        if not is_video:
            pyautogui.hotkey("shift", "tab")
            time.sleep(0.05)
            pyautogui.hotkey("shift", "tab")
            time.sleep(0.05)
            pyautogui.hotkey("shift", "tab")
            time.sleep(0.05)
            pyautogui.hotkey("shift", "tab")
            time.sleep(0.05)
            pyautogui.hotkey("shift", "tab")
            time.sleep(0.1)
            pyautogui.press("enter")
            time.sleep(0.2)

        # Step 3: Precise Bounding Box Header Click fallback
        if rect:
            left, top, right, bottom = rect
            # Voice Call icon is 85px from the right border and 55px below top border
            call_x = right - (130 if is_video else 85)
            call_y = top + 55
            pyautogui.click(call_x, call_y)
            return True

        return False

    def execute(self, user_message: str) -> str:
        parsed = self.parse_command(user_message)
        platform = parsed["platform"]
        action = parsed["action"]
        recipient = parsed["recipient"]
        payload = parsed["payload"]

        print()
        print("[ChatAutomation] EXECUTING AUTOMATION:")
        print(f"  Platform  : {platform}")
        print(f"  Action    : {action}")
        print(f"  Recipient : {recipient}")
        print(f"  Payload   : {payload}")

        if not recipient:
            return f"Please specify who you want to contact on {platform.title()}."

        # 1. Launch & Focus App
        opened = self._launch_app(platform)
        if not opened:
            return f"I could not launch {platform.title()} on this PC."

        time.sleep(1.8)
        self._focus_whatsapp_window()

        # 2. Focus Search Bar & Clear
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.3)

        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.press("backspace")
        time.sleep(0.2)

        # 3. Type Contact Name & Open Chat
        pyautogui.write(recipient, interval=0.05)
        time.sleep(1.0)

        pyautogui.press("down")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(1.2)

        # ========================================================
        # 4. ACTION: CALLING
        # ========================================================
        if action in ["call", "video_call"]:
            if platform == "whatsapp":
                is_video = (action == "video_call")
                called = self._trigger_whatsapp_call_robust(is_video=is_video)
                return f"Calling {recipient} on WhatsApp."

            elif platform == "teams":
                pyautogui.hotkey("ctrl", "shift", "u")
                return f"Initiating call to {recipient} on Teams."
            else:
                return f"Opened conversation with {recipient} on {platform.title()}."

        # ========================================================
        # 5. ACTION: MESSAGING
        # ========================================================
        if action == "message":
            if payload:
                pyautogui.write(payload, interval=0.03)
                time.sleep(0.3)
                pyautogui.press("enter")
                return f"Sent message to {recipient} on {platform.title()}: '{payload}'"
            else:
                return f"Opened chat with {recipient} on {platform.title()}. What message would you like to send?"

        return f"Opened conversation with {recipient} on {platform.title()}."

    def _launch_app(self, platform: str) -> bool:
        config = self.APP_CONFIG.get(platform)
        if not config:
            return False

        try:
            os.startfile(config["scheme"])
            return True
        except Exception:
            try:
                subprocess.Popen([config["exe"]], shell=False)
                return True
            except Exception as e:
                print(f"[ChatAutomation] Error launching {platform}: {e}")
                return False


chat_automation_tool = ChatAutomationTool()


def automate_chat(user_message: str) -> str:
    return chat_automation_tool.execute(user_message)