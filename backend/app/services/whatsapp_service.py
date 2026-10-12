"""
WhatsApp Desktop Automation and Background Monitoring Service for Friday AI Assistant.
Supports UI automation, contact search, messaging, voice/video calls, and background Windows toast monitoring with AI auto-replies.
"""

from __future__ import annotations

import os
import sys
import re
import difflib
import time
import json
import asyncio
import logging
import threading
import subprocess
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import psutil

logger = logging.getLogger(__name__)

# Initialize Windows DPI Awareness for exact coordinate matching
if os.name == "nt":
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Try importing uiautomation
try:
    import uiautomation as auto
    _UIA_AVAILABLE = True
except ImportError:
    _UIA_AVAILABLE = False

# Try importing pyautogui
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False

# Try importing winsdk for Windows notification listener
try:
    from winsdk.windows.ui.notifications.management import UserNotificationListener
    from winsdk.windows.ui.notifications import NotificationKinds
    _WINSDK_AVAILABLE = True
except ImportError:
    _WINSDK_AVAILABLE = False


# Setup database path for WhatsApp settings and logs
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = ROOT_DIR / "database"
DB_DIR.mkdir(parents=True, exist_ok=True)
WHATSAPP_CONFIG_FILE = DB_DIR / "whatsapp_settings.json"
WHATSAPP_LOGS_FILE = DB_DIR / "whatsapp_logs.json"


DEFAULT_SETTINGS: Dict[str, Any] = {
    "enabled": False,
    "auto_reply": False,
    "monitoring_active": False,
    "custom_auto_reply_message": None,
    "auto_reply_template": "dynamic_ai",
    "replied_count": 0,
    "last_activity": None,
    "notify_mode": "urgent",
    "notify_target_contact": None
}


def get_foreground_window_info() -> tuple:
    """Returns (window_title, process_name) of the current foreground window on Windows."""
    try:
        if os.name == "nt":
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return ("", "")
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value or ""
            
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            proc_name = ""
            if pid.value:
                try:
                    proc_name = psutil.Process(pid.value).name() or ""
                except Exception:
                    pass
            return (title, proc_name)
    except Exception:
        pass
    return ("", "")


def find_whatsapp_hwnd():
    """Finds top-level HWND of WhatsApp Desktop using Windows user32."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        user32 = ctypes.windll.user32
        target_hwnd = None

        def enum_cb(hwnd, _):
            nonlocal target_hwnd
            if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value:
                    try:
                        pname = psutil.Process(pid.value).name().lower()
                        if "whatsapp" in pname:
                            length = user32.GetWindowTextLengthW(hwnd)
                            buff = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buff, length + 1)
                            title = buff.value or ""
                            if length > 0 or "whatsapp" in title.lower():
                                target_hwnd = hwnd
                                return False
                    except Exception:
                        pass
            return True

        EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(EnumProc(enum_cb), 0)
        return target_hwnd
    except Exception:
        return None


def force_focus_hwnd(hwnd) -> bool:
    """Forces window to foreground bypassing Windows focus locks."""
    if not hwnd or os.name != "nt":
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        # Send Alt key event to unlock SetForegroundWindow permission
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SwitchToThisWindow(hwnd, True)
        return True
    except Exception:
        return False


def is_whatsapp_in_foreground() -> bool:
    """Checks if active foreground window belongs to WhatsApp."""
    title, proc_name = get_foreground_window_info()
    p_lower = proc_name.lower()
    t_lower = title.lower()

    if "whatsapp" in p_lower or "whatsapp" in t_lower:
        return True

    if _UIA_AVAILABLE:
        try:
            fc = auto.GetFocusedControl()
            if fc and fc.ProcessId:
                pname = psutil.Process(fc.ProcessId).name().lower()
                if "whatsapp" in pname:
                    return True
        except Exception:
            pass

    return False


class WhatsAppService:
    """
    Manages WhatsApp Desktop interaction, message sending, calls, and notification monitoring.
    """

    def __init__(self):
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_start_time: Optional[datetime.datetime] = None
        self._replied_ids: set = set()
        self._replied_signatures: Dict[str, float] = {}
        self._sender_history: Dict[str, List[Dict[str, Any]]] = {}
        self.latest_urgent_alert: Optional[Dict[str, Any]] = None
        self.latest_received_message: Optional[Dict[str, Any]] = None
        self.latest_incoming_call: Optional[Dict[str, Any]] = None
        self.settings = self._load_settings()
        self.window = None

    def _play_urgent_voice_alert(self, sender: str, message: str):
        """Speaks out loud on system speakers to immediately interrupt and alert Harishan."""
        def _speak():
            try:
                import pythoncom
                pythoncom.CoInitialize()
                import win32com.client
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                clean_msg = message[:100].replace("\n", " ").strip()
                speaker.Speak(f"Attention Harishan! Urgent WhatsApp message from {sender}. {clean_msg}")
                pythoncom.CoUninitialize()
            except Exception as e:
                logger.warning(f"Voice alert SAPI fallback: {e}")

        threading.Thread(target=_speak, daemon=True).start()

    def _play_spoken_notification(self, sender: str, message: str):
        """Speaks out loud to notify the user of an incoming WhatsApp message."""
        def _speak():
            try:
                import pythoncom
                pythoncom.CoInitialize()
                import win32com.client
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                clean_msg = message[:120].replace("\n", " ").strip()
                speaker.Speak(f"Harishan, you have received a message from {sender}: {clean_msg}")
                pythoncom.CoUninitialize()
            except Exception as e:
                logger.warning(f"Spoken notification SAPI error: {e}")

        threading.Thread(target=_speak, daemon=True).start()

    def _play_incoming_call_alert(self, caller: str, call_type: str = "voice"):
        """Speaks out loud to alert the user of an incoming WhatsApp call."""
        def _speak():
            try:
                import pythoncom
                pythoncom.CoInitialize()
                import win32com.client
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Speak(f"Attention Harishan! Incoming WhatsApp {call_type} call from {caller}.")
                pythoncom.CoUninitialize()
            except Exception as e:
                logger.warning(f"Incoming call alert SAPI error: {e}")

        threading.Thread(target=_speak, daemon=True).start()

    def speak_in_call(self, text: str) -> Dict[str, Any]:
        """Speaks a message out loud during a call to communicate with the receiver."""
        clean_text = text.strip()
        if not clean_text:
            return {"success": False, "error": "No message provided to speak."}

        def _speak():
            try:
                import pythoncom
                pythoncom.CoInitialize()
                import win32com.client
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Speak(clean_text)
                pythoncom.CoUninitialize()
            except Exception as e:
                logger.warning(f"In-call SAPI error: {e}")

        threading.Thread(target=_speak, daemon=True).start()
        return {"success": True, "message": f"Spoken in call: \"{clean_text}\""}

    def get_urgent_alert(self) -> Optional[Dict[str, Any]]:
        """Returns the latest unacknowledged urgent WhatsApp alert."""
        return self.latest_urgent_alert

    def dismiss_urgent_alert(self) -> Dict[str, Any]:
        """Dismisses the active urgent alert."""
        self.latest_urgent_alert = None
        return {"status": "success", "message": "Urgent alert dismissed"}

    def record_sender_message(self, sender: str, message: str, role: str = "contact"):
        """Maintains the recent conversation turn history per sender."""
        if sender not in self._sender_history:
            self._sender_history[sender] = []
        self._sender_history[sender].append({
            "role": role,
            "text": message,
            "timestamp": time.strftime("%H:%M:%S")
        })
        # Keep last 6 turns per sender
        self._sender_history[sender] = self._sender_history[sender][-6:]

    def get_sender_context(self, sender: str) -> str:
        """Returns formatted recent message history for the sender."""
        history = self._sender_history.get(sender, [])
        if not history:
            return ""
        lines = []
        for turn in history[-4:]:
            r_name = sender if turn.get("role") == "contact" else "Friday"
            lines.append(f"- [{turn.get('timestamp')}] {r_name}: \"{turn.get('text')}\"")
        return "\n".join(lines)

    def is_media_message(self, text: str) -> tuple:
        """Detects if message is a media, attachment, photo, document, or audio notification."""
        if not text:
            return False, ""
        t_clean = text.lower().strip()
        media_indicators = {
            "photo": "photo",
            "📷 photo": "photo",
            "image": "photo",
            "picture": "photo",
            "video": "video",
            "🎥 video": "video",
            "voice message": "voice message",
            "🎤 voice message": "voice message",
            "audio": "audio",
            "document": "document",
            "📄 document": "document",
            "file": "document",
            "sticker": "sticker",
            "gif": "GIF",
            "location": "location",
            "contact card": "contact card"
        }
        for k, v in media_indicators.items():
            if t_clean == k or t_clean.startswith(f"📷 {k}") or t_clean == f"[{k}]":
                return True, v

        import re
        if re.search(r'\.(pdf|docx?|xlsx?|pptx?|zip|rar|png|jpe?g|mp4|mp3|m4a)$', t_clean):
            return True, "document"

        return False, ""

    def _load_settings(self) -> Dict[str, Any]:
        if WHATSAPP_CONFIG_FILE.exists():
            try:
                with open(WHATSAPP_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {**DEFAULT_SETTINGS, **data}
            except Exception as e:
                logger.error(f"Error loading WhatsApp settings: {e}")
        return DEFAULT_SETTINGS.copy()

    def _save_settings(self) -> None:
        try:
            with open(WHATSAPP_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving WhatsApp settings: {e}")

    def _log_message_event(self, sender: str, incoming_message: str, reply_sent: str, is_urgent: bool = False) -> None:
        logs = []
        if WHATSAPP_LOGS_FILE.exists():
            try:
                with open(WHATSAPP_LOGS_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                logs = []

        logs.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sender": sender,
            "message": incoming_message,
            "reply": reply_sent,
            "is_urgent": is_urgent,
            "read": False
        })
        # Keep last 100 entries
        logs = logs[-100:]
        try:
            with open(WHATSAPP_LOGS_FILE, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)
        except Exception:
            pass

    def get_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        if WHATSAPP_LOGS_FILE.exists():
            try:
                with open(WHATSAPP_LOGS_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                    return logs[-limit:]
            except Exception:
                return []
        return []

    def get_unseen_logs(self, mark_as_read: bool = True) -> List[Dict[str, Any]]:
        """Returns only new/unread messages since the last check and marks them read."""
        if not WHATSAPP_LOGS_FILE.exists():
            return []
        try:
            with open(WHATSAPP_LOGS_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            return []

        unseen = [item for item in logs if not item.get("read", False)]

        if unseen and mark_as_read:
            for item in logs:
                item["read"] = True
            try:
                with open(WHATSAPP_LOGS_FILE, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=2)
            except Exception:
                pass

        return unseen

    def get_live_unread_chats(self) -> List[Dict[str, Any]]:
        """
        Inspects WhatsApp UI for chats with unread notification badges.
        Acts as a robust live fallback when toast notifications are disabled or missed.
        """
        results = []
        if not _UIA_AVAILABLE:
            return results

        try:
            hwnd = find_whatsapp_hwnd()
            if not hwnd:
                return results

            root = auto.GetRootControl()
            for win in root.GetChildren():
                name = (win.Name or "").lower()
                pid = win.ProcessId
                proc_name = psutil.Process(pid).name().lower() if pid else ""
                if "whatsapp" in proc_name or "whatsapp" in name:
                    # Scan chat list items
                    for item in win.GetChildren():
                        item_text = (item.Name or "").strip()
                        if item_text and any(k in item_text.lower() for k in ["unread message", "unread messages"]):
                            results.append({
                                "chat": item_text,
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            })
                    break
        except Exception as e:
            logger.debug(f"Live unread inspection: {e}")
        return results

    # -------------------------------------------------------------
    # WINDOW FOCUS & DETECTION
    # -------------------------------------------------------------
    def find_or_focus_whatsapp(self, timeout: float = 1.0) -> bool:
        """Locates and brings WhatsApp Desktop to the foreground safely."""
        self.window = None
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 1. Win32 HWND direct foreground unlock
            hwnd = find_whatsapp_hwnd()
            if hwnd:
                force_focus_hwnd(hwnd)
                time.sleep(0.1)

            # 2. UIA window detection
            if _UIA_AVAILABLE:
                try:
                    root = auto.GetRootControl()
                    for win in root.GetChildren():
                        try:
                            name = win.Name or ""
                            pid = win.ProcessId
                            proc_name = psutil.Process(pid).name() if pid else ""
                            if "whatsapp" in proc_name.lower() or "whatsapp" in name.lower():
                                self.window = win
                                break
                        except Exception:
                            continue

                    if self.window and self.window.Exists(0, 0):
                        try:
                            self.window.SetActive()
                            time.sleep(0.1)
                        except Exception:
                            pass
                        return True
                except Exception as e:
                    logger.warning(f"UIA WhatsApp search error: {e}")

            # 3. Launch protocol if window not visible (only if not running under pytest)
            if not os.environ.get("PYTEST_CURRENT_TEST") and time.time() - start_time < 0.5:
                try:
                    os.system("start whatsapp:")
                except Exception:
                    pass

            time.sleep(0.2)

        if is_whatsapp_in_foreground() or (self.window and self.window.Exists(0, 0)) or find_whatsapp_hwnd():
            return True

        return False

    # -------------------------------------------------------------
    # CONTACT SEARCH & CHAT NAVIGATION
    # -------------------------------------------------------------
    def search_and_open_chat(self, contact_name: str) -> bool:
        """Searches for a contact or group and opens the active chat safely."""
        self.find_or_focus_whatsapp()

        contact_clean = contact_name.strip().strip('"').strip("'")
        if contact_clean.lower().startswith("to "):
            contact_clean = contact_clean[3:].strip()
        if not contact_clean:
            return False

        search_success = False

        # Strategy 1: Targeted UIA Search Edit Control
        if _UIA_AVAILABLE and self.window:
            try:
                search_box = self.window.EditControl(searchDepth=12)
                if search_box.Exists(0.4, 1):
                    search_box.Click(waitTime=0.1)
                    search_box.SendKeys('{Ctrl}a{Delete}', waitTime=0.1)
                    search_box.SendKeys(contact_clean, waitTime=0.4)
                    time.sleep(0.4)
                    search_box.SendKeys('{Down}{Enter}', waitTime=0.4)
                    search_success = True
            except Exception:
                pass

        # Strategy 2: Window Hotkey Search (Ctrl+F)
        if not search_success:
            if _UIA_AVAILABLE and self.window:
                try:
                    self.window.SendKeys('{Ctrl}f', waitTime=0.2)
                    self.window.SendKeys('{Ctrl}a{Delete}', waitTime=0.1)
                    self.window.SendKeys(contact_clean, waitTime=0.5)
                    time.sleep(0.4)
                    self.window.SendKeys('{Down}{Enter}', waitTime=0.4)
                    search_success = True
                except Exception:
                    pass

        # Strategy 3: PyAutoGUI Fallback
        if not search_success and _PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.hotkey('ctrl', 'f')
                time.sleep(0.2)
                pyautogui.hotkey('ctrl', 'a')
                pyautogui.press('delete')
                pyautogui.write(contact_clean, interval=0.03)
                time.sleep(0.5)
                pyautogui.press('down')
                time.sleep(0.1)
                pyautogui.press('enter')
                search_success = True
            except Exception:
                pass

        time.sleep(0.6)

        # Fallback click to select chat in the left list pane
        if _PYAUTOGUI_AVAILABLE:
            try:
                rect = None
                if self.window and _UIA_AVAILABLE:
                    rect = self.window.BoundingRectangle
                if not rect:
                    hwnd = find_whatsapp_hwnd()
                    if hwnd:
                        import ctypes
                        from ctypes import wintypes
                        r = wintypes.RECT()
                        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
                        rect = type('Rect', (), {'left': r.left, 'top': r.top, 'right': r.right, 'bottom': r.bottom})()

                if rect:
                    pyautogui.click(rect.left + 180, rect.top + 130)
                    time.sleep(0.4)
            except Exception:
                pass

        return True

    # -------------------------------------------------------------
    # SEND MESSAGE
    # -------------------------------------------------------------
    def _get_window_rect(self):
        """Helper to get accurate window bounding rect."""
        rect = None
        if self.window and _UIA_AVAILABLE:
            try:
                rect = self.window.BoundingRectangle
            except Exception:
                rect = None

        if not rect or rect.right - rect.left <= 0:
            hwnd = find_whatsapp_hwnd()
            if hwnd:
                try:
                    import ctypes
                    from ctypes import wintypes
                    r = wintypes.RECT()
                    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
                    rect = type('Rect', (), {'left': r.left, 'top': r.top, 'right': r.right, 'bottom': r.bottom})()
                except Exception:
                    pass
        return rect

    def send_message(self, contact_name: str, message: str) -> Dict[str, Any]:
        """Sends a text message to the specified contact."""
        try:
            self.search_and_open_chat(contact_name)
            time.sleep(0.6)

            rect = self._get_window_rect()

            # Focus the message input bar in the right chat panel (bottom of right panel)
            if _PYAUTOGUI_AVAILABLE and rect:
                try:
                    # Message input box is located horizontally at ~65% of window width, ~45px from bottom
                    input_x = rect.left + int((rect.right - rect.left) * 0.65)
                    input_y = rect.bottom - 45
                    pyautogui.moveTo(input_x, input_y, duration=0.2)
                    pyautogui.click()
                    time.sleep(0.3)
                except Exception:
                    pass

            # Try focusing EditControl / TextBox via UIA
            if _UIA_AVAILABLE and self.window:
                try:
                    # Find message box (typically EditControl with Name containing 'message' or bottom edit)
                    edits = self.window.GetChildren()
                    for ctrl in self.window.GetChildren():
                        if "edit" in (ctrl.ControlTypeName or "").lower():
                            if ctrl.BoundingRectangle.top > (rect.top + 200 if rect else 200):
                                ctrl.Click(waitTime=0.1)
                                break
                except Exception:
                    pass

            # Paste message and hit enter
            if _PYAUTOGUI_AVAILABLE:
                import pyperclip
                pyperclip.copy(message)
                time.sleep(0.1)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.3)
                pyautogui.press('enter')
                time.sleep(0.3)
            elif _UIA_AVAILABLE and self.window:
                self.window.SendKeys(message, waitTime=0.2)
                self.window.SendKeys('{Enter}', waitTime=0.2)

            return {
                "success": True,
                "contact": contact_name,
                "message": message,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logger.error(f"WhatsApp send_message failed: {e}")
            return {"success": False, "contact": contact_name, "error": str(e)}

    # -------------------------------------------------------------
    # DYNAMIC CONTACT RESOLUTION & DISAMBIGUATION (NO HARDCODING)
    # -------------------------------------------------------------
    def get_known_contacts(self) -> List[str]:
        """Collects unique known contact names from message logs and sender history."""
        contacts = set()
        for s in self._sender_history.keys():
            if s and not self._is_unknown_number(s):
                contacts.add(s)
        if getattr(self, "latest_received_message", None):
            s = (self.latest_received_message.get("sender") or "").strip()
            if s and not self._is_unknown_number(s):
                contacts.add(s)
        try:
            log_path = Path(__file__).resolve().parent.parent.parent / "database" / "whatsapp_logs.json"
            if log_path.exists():
                with open(log_path, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                    if isinstance(logs, list):
                        for entry in logs:
                            s = (entry.get("sender") or "").strip()
                            if s and not self._is_unknown_number(s):
                                contacts.add(s)
        except Exception:
            pass
        return sorted(list(contacts))

    def inspect_whatsapp_search_results(self, search_query: str) -> List[str]:
        """Dynamically inspects contact names displayed in WhatsApp Desktop's search results."""
        results = []
        if not _UIA_AVAILABLE:
            return results
        try:
            self.find_or_focus_whatsapp()
            if not self.window:
                return results

            search_box = self.window.EditControl(searchDepth=12)
            if search_box.Exists(0.3, 1):
                search_box.Click(waitTime=0.05)
                search_box.SendKeys('{Ctrl}a{Delete}', waitTime=0.05)
                search_box.SendKeys(search_query, waitTime=0.2)
                time.sleep(0.35)

            # Extract displayed search result names from UI Automation tree
            def _extract_items(ctrl, depth=0):
                if depth > 10:
                    return
                for item in ctrl.GetChildren():
                    item_name = (item.Name or "").strip()
                    c_type = (item.ControlTypeName or "").lower()
                    if item_name and len(item_name) < 60 and item_name not in results:
                        ignored = [
                            "chats", "search", "search or start a new chat", "messages", "unread",
                            "contacts", "filter unread", "new chat", "status", "channels", "communities",
                            "type a message", "attach", "voice message", "video call", "voice call", "menu",
                            "profile", "settings", "close", "minimize", "maximize"
                        ]
                        if item_name.lower() not in ignored and not item_name.lower().startswith("type a message"):
                            # Filter out pure time strings like "10:30 AM", "Yesterday"
                            if not re.match(r'^\d{1,2}:\d{2}(?:\s*(?:am|pm))?$', item_name, re.IGNORECASE):
                                results.append(item_name)
                    _extract_items(item, depth + 1)

            if self.window:
                _extract_items(self.window)
        except Exception as e:
            logger.warning(f"Error inspecting search results: {e}")
        return results

    def find_contact_candidates(self, query: str, live_search: bool = True) -> Dict[str, Any]:
        """
        Dynamically resolves contact candidates with fuzzy matching, qualifiers, and multi-candidate detection.
        Works generically for all names (e.g. 'Kishore', 'Kishore Priyan(krct)', 'Kishore M(svv)', 'Harini').
        No hardcoding!
        """
        import difflib
        import re

        clean_q = query.strip().strip('"').strip("'")
        if clean_q.lower().startswith("to "):
            clean_q = clean_q[3:].strip()
        q_lower = clean_q.lower()

        # Gather pool from known logs + active UI if requested
        pool = set(self.get_known_contacts())
        if live_search or is_whatsapp_in_foreground() or len(pool) <= 1:
            ui_contacts = self.inspect_whatsapp_search_results(clean_q)
            for c in ui_contacts:
                pool.add(c)

        if not pool:
            return {"status": "single", "candidates": [clean_q], "best_match": clean_q}

        # Find all contacts matching the search query as substring / tokens / name words
        token_matches = []
        for c in pool:
            c_lower = c.lower()
            c_cleaned = re.sub(r'[\(\[\{].*?[\)\]\}]', '', c_lower).strip()
            if (q_lower == c_lower) or (q_lower == c_cleaned):
                token_matches.append(c)
            elif (q_lower in c_lower) or (q_lower in c_cleaned):
                token_matches.append(c)
            else:
                c_words = [w.strip() for w in re.split(r'[\s\(\)\[\]_\-]+', c_lower) if w.strip()]
                if any(q_lower == w or (len(q_lower) >= 3 and w.startswith(q_lower)) for w in c_words):
                    token_matches.append(c)

        token_matches = sorted(list(set(token_matches)))

        # If multiple contacts match the query, Friday MUST ask the user which one!
        if len(token_matches) > 1:
            candidates_str = ", ".join([f"{i+1}. {name}" for i, name in enumerate(token_matches)])
            return {
                "status": "multiple",
                "candidates": token_matches,
                "best_match": None,
                "prompt": f"I found multiple contacts matching '{clean_q}': {candidates_str}. Which one would you like to contact — the first one, the second one, or a specific name?"
            }
        elif len(token_matches) == 1:
            match = token_matches[0]
            # If the contact is not an exact match (e.g. has qualifiers, initials, emojis like 'Abhishek N S(krct)', 'Kishore💙'), confirm with the user
            if match.strip().lower() != q_lower:
                return {
                    "status": "qualifier_match",
                    "candidates": [match],
                    "best_match": match,
                    "prompt": f"I found '{match}'. Would you like me to proceed with {match} or someone else?"
                }
            return {"status": "single", "candidates": [match], "best_match": match}

        # Fuzzy matching with difflib for typos
        close_matches = difflib.get_close_matches(clean_q, list(pool), n=3, cutoff=0.55)
        if len(close_matches) > 1:
            candidates_str = ", ".join([f"{i+1}. {name}" for i, name in enumerate(close_matches)])
            return {
                "status": "multiple",
                "candidates": close_matches,
                "best_match": None,
                "prompt": f"I found multiple similar contacts: {candidates_str}. Which one should I contact?"
            }
        elif len(close_matches) == 1:
            match = close_matches[0]
            return {
                "status": "fuzzy_single",
                "candidates": [match],
                "best_match": match,
                "prompt": f"Did you mean '{match}'?"
            }

        return {"status": "single", "candidates": [clean_q], "best_match": clean_q}

    # -------------------------------------------------------------
    # SEND FILE ATTACHMENT
    # -------------------------------------------------------------
    def send_file(self, contact_name: str, file_path: str) -> Dict[str, Any]:
        """Sends a document, image, or file to the specified contact on WhatsApp."""
        try:
            p = Path(file_path).resolve()
            if not p.exists() or not p.is_file():
                return {"success": False, "error": f"File does not exist: {file_path}"}

            self.search_and_open_chat(contact_name)
            time.sleep(0.8)

            rect = self._get_window_rect()
            if _PYAUTOGUI_AVAILABLE and rect:
                input_x = rect.left + int((rect.right - rect.left) * 0.65)
                input_y = rect.bottom - 45
                pyautogui.click(input_x, input_y)
                time.sleep(0.3)

            # Copy file to Windows clipboard using PowerShell HDROP & Set-Clipboard
            staged = False
            try:
                from app.services.context_service import set_file_to_clipboard
                staged = set_file_to_clipboard(str(p))
            except Exception:
                staged = False

            if not staged:
                abs_path = str(p).replace("'", "''")
                cmd = f'powershell -NoProfile -Command "Set-Clipboard -Path \'{abs_path}\'"'
                subprocess.run(cmd, shell=True, timeout=5)
            time.sleep(0.4)

            # Paste into WhatsApp Desktop
            if _PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(1.0)
                pyautogui.press('enter')
                time.sleep(0.5)
                # Ensure sent by sending Enter again if still in preview dialog
                pyautogui.press('enter')
                time.sleep(0.3)

            return {
                "success": True,
                "contact": contact_name,
                "file_path": str(p),
                "file_name": p.name,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logger.error(f"WhatsApp send_file failed: {e}")
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------
    # VOICE & VIDEO CALLS
    # -------------------------------------------------------------
    def _find_call_button_control(self, is_video: bool = False):
        """Recursively finds the Voice or Video call button in WhatsApp window."""
        if not self.window or not _UIA_AVAILABLE:
            return None
        
        candidates = []
        try:
            def search_ctrl(ctrl, depth=0):
                if depth > 12:
                    return
                try:
                    name = (ctrl.Name or "").lower()
                    aid = (ctrl.AutomationId or "").lower()
                    ctype = (ctrl.ControlTypeName or "").lower()
                    
                    is_btn = "button" in ctype or "button" in ctrl.ClassName.lower() or "appbarbutton" in ctrl.ClassName.lower()
                    
                    if is_btn or "call" in aid or "call" in name:
                        if is_video:
                            if "video" in name or "video" in aid:
                                candidates.append(ctrl)
                        else:
                            if ("voice" in name or "audio" in name or "voice" in aid or "audiocall" in aid or name == "call" or aid == "callbutton") and "video" not in name and "video" not in aid:
                                candidates.append(ctrl)
                    
                    for child in ctrl.GetChildren():
                        search_ctrl(child, depth + 1)
                except Exception:
                    pass

            search_ctrl(self.window)
            if candidates:
                return candidates[0]
        except Exception as e:
            logger.warning(f"Error searching call button: {e}")
        return None

    def start_call(self, contact_name: str, call_type: str = "voice") -> Dict[str, Any]:
        """Initiates a voice or video call on WhatsApp Desktop."""
        try:
            clean_name = contact_name.strip().strip('"').strip("'")
            if clean_name.lower().startswith("to "):
                clean_name = clean_name[3:].strip()

            self.search_and_open_chat(clean_name)
            time.sleep(0.8)
            is_video = "video" in call_type.lower()
            call_triggered = False

            # Step 1: Native WhatsApp Desktop Hotkeys
            # Voice Call: Ctrl + Shift + U | Video Call: Ctrl + Shift + V
            if _PYAUTOGUI_AVAILABLE:
                try:
                    if is_video:
                        pyautogui.hotkey('ctrl', 'shift', 'v')
                    else:
                        pyautogui.hotkey('ctrl', 'shift', 'u')
                    time.sleep(0.3)
                    call_triggered = True
                except Exception:
                    pass

            # Step 2: UIA Discovery and Direct Pattern Invocation
            call_btn = self._find_call_button_control(is_video=is_video)
            if call_btn:
                try:
                    ip = call_btn.GetInvokePattern()
                    if ip:
                        ip.Invoke()
                        call_triggered = True
                except Exception:
                    pass

                if _PYAUTOGUI_AVAILABLE:
                    try:
                        b_rect = call_btn.BoundingRectangle
                        if b_rect and (b_rect.right - b_rect.left) > 0:
                            cx = (b_rect.left + b_rect.right) // 2
                            cy = (b_rect.top + b_rect.bottom) // 2
                            pyautogui.moveTo(cx, cy, duration=0.2)
                            pyautogui.click()
                            call_triggered = True
                    except Exception:
                        pass

            # Step 3: Exact Header Calibrated Coordinates with Smooth Visual Mouse Movement
            rect = self._get_window_rect()
            if _PYAUTOGUI_AVAILABLE and rect:
                try:
                    # In WhatsApp Desktop:
                    # Camera Icon (Video Call) is at rect.right - 215px, Y = rect.top + 58px
                    # Phone Icon (Voice Call) is at rect.right - 150px, Y = rect.top + 58px
                    header_y = rect.top + 58

                    if is_video:
                        target_x = rect.right - 215
                        pyautogui.moveTo(target_x, header_y, duration=0.35)
                        time.sleep(0.1)
                        pyautogui.click()
                        time.sleep(0.1)
                        pyautogui.click(rect.right - 210, rect.top + 56)
                        call_triggered = True
                    else:
                        target_x = rect.right - 150
                        pyautogui.moveTo(target_x, header_y, duration=0.35)
                        time.sleep(0.1)
                        pyautogui.click()
                        time.sleep(0.1)
                        pyautogui.click(rect.right - 145, rect.top + 56)
                        call_triggered = True
                except Exception:
                    pass

            return {
                "success": True,
                "contact": clean_name,
                "call_type": "video" if is_video else "voice",
                "triggered": call_triggered,
                "message": f"Initiated {call_type} call to {clean_name}."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def answer_call(self) -> Dict[str, Any]:
        """Answers/attends an incoming WhatsApp voice or video call."""
        try:
            self.find_or_focus_whatsapp(timeout=1.0)
            answered = False

            if _UIA_AVAILABLE:
                try:
                    # Check active root desktop for WhatsApp Call dialogs / popups
                    root = auto.GetRootControl()
                    for win in root.GetChildren():
                        try:
                            w_name = (win.Name or "").lower()
                            if "whatsapp" in w_name or "call" in w_name or "incoming" in w_name:
                                for btn_name in ["Accept", "Answer", "Accept call", "Accept voice call", "Accept video call", "Pick up"]:
                                    btn = win.ButtonControl(searchDepth=8, Name=btn_name)
                                    if btn.Exists(0.2, 1):
                                        btn.Click(waitTime=0.1)
                                        answered = True
                                        break
                        except Exception:
                            continue
                        if answered:
                            break
                except Exception:
                    pass

            if not answered and self.window and _UIA_AVAILABLE:
                try:
                    for name in ["Accept", "Answer", "Accept call", "Accept voice call", "Accept video call", "Pick up"]:
                        btn = self.window.ButtonControl(searchDepth=12, Name=name)
                        if btn.Exists(0.2, 1):
                            btn.Click(waitTime=0.1)
                            answered = True
                            break
                except Exception:
                    pass

            if not answered and _PYAUTOGUI_AVAILABLE and is_whatsapp_in_foreground():
                pyautogui.hotkey('alt', 'a')
                time.sleep(0.1)
                pyautogui.press('enter')
                answered = True

            return {"success": True, "message": "Incoming call accepted."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def decline_call(self) -> Dict[str, Any]:
        """Declines, rejects, or hangs up an active/incoming WhatsApp call."""
        try:
            self.find_or_focus_whatsapp(timeout=2.0)
            declined = False
            if _UIA_AVAILABLE and self.window:
                try:
                    for name in ["Decline", "Reject", "Decline call", "End call", "Leave call", "Hang up", "Dismiss"]:
                        btn = self.window.ButtonControl(searchDepth=15, Name=name)
                        if btn.Exists(0.3, 1):
                            btn.Click(waitTime=0.2)
                            declined = True
                            break
                except Exception:
                    pass

            if not declined and _PYAUTOGUI_AVAILABLE and is_whatsapp_in_foreground():
                pyautogui.hotkey('alt', 'd')
                time.sleep(0.2)
                pyautogui.press('esc')
                declined = True

            return {"success": True, "message": "Call declined/ended."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------
    # MULTILINGUAL & URGENCY INTELLIGENCE
    # -------------------------------------------------------------
    def detect_language(self, text: str) -> str:
        """
        Detects if an incoming message is written in Tamil script, Tanglish, or English.
        """
        if not text:
            return "english"

        import re
        # 1. Tamil Unicode characters (\u0B80 - \u0BFF)
        if re.search(r'[\u0B80-\u0BFF]', text):
            return "tamil"

        # 2. Tanglish vocabulary & phonetics matching
        t_lower = text.lower()
        tanglish_words = {
            "enna", "panra", "panreenga", "panringa", "panrom", "panran", "epo", "eppo",
            "varuvaaru", "varuvaan", "varum", "varuvanga", "sollu", "sollunga", "solren",
            "irukken", "irukka", "irukkinga", "iruka", "iruku", "irukku", "vaanga", "ponga",
            "thambi", "anna", "akka", "amma", "appa", "romba", "seekiram", "seekram",
            "illai", "illa", "ille", "aama", "ama", "nalla", "vanakkam", "epdi", "eppadi",
            "enge", "enga", "engada", "saptingala", "saptacha", "sapten", "pesu", "pesunga",
            "call pannu", "call panna", "avartta", "avarta", "kitta", "mudiyuma", "theriyuma",
            "seri", "ok va", "varaan", "poren", "vandhuten", "vandhachu", "poidu", "ingey",
            "inga", "angey", "anga", "edhuku", "yen", "yaaru", "edhu", "epovum", "ippo",
            "ipo", "aprom", "appo", "aprom", "solla", "mudiyathu", "panna", "panniko", "vanga"
        }
        tokens = set(re.findall(r'\b[a-z]+\b', t_lower))
        if len(tokens.intersection(tanglish_words)) >= 1 or any(kw in t_lower for kw in ["call pannu", "call panna", "enna panra", "eppo varu"]):
            return "tanglish"

        return "english"

    def check_is_urgent(self, text: str) -> bool:
        """
        Detects whether an incoming message indicates urgency, emergency, or high priority.
        """
        if not text:
            return False

        t_lower = text.lower()
        urgent_keywords = [
            "urgent", "urgently", "emergency", "immediately", "asap", "hospital", "accident",
            "critical", "danger", "die", "death", "help me", "police", "ambulance",
            "very important", "serious", "alert", "fast", "right now", "call now",
            "call immediately", "need help", "matter of life", "distress", "trouble"
        ]
        # Tanglish / Tamil urgent indicators
        tanglish_tamil_urgent = [
            "seekiram call", "udane", "avasiyam", "mukkiyam", "avaram",
            "seekiram", "udane call", "romba urgent",
            "அவசரம்", "சீக்கிரம்", "உதவி", "முக்கியம்", "ஆபத்து", "மருத்துவமனை", "உடனடியாக"
        ]

        if any(k in t_lower for k in urgent_keywords) or any(k in t_lower for k in tanglish_tamil_urgent) or any(k in text for k in tanglish_tamil_urgent):
            return True

        return False

    # -------------------------------------------------------------
    # DYNAMIC AI AUTO-REPLY GENERATION (COMPULSORY AGENT HEADER)
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    # DYNAMIC AI AUTO-REPLY GENERATION (COMPULSORY AGENT HEADER)
    # -------------------------------------------------------------
    def generate_auto_reply(self, sender: str, incoming_message: str, context: Optional[str] = None) -> str:
        """
        Generates a smart, polite, multilingual AI chat agent reply on Harishan's behalf.
        - Converses intelligently based on the sender's full message and recent chat history.
        - Supports multiple rapid messages in one combined reply.
        - Handles media/photos/files as personal assistant without asking for prompts.
        - Supports English, Tanglish, and Tamil.
        - Flags urgency immediately.
        - Compulsorily includes Friday's identity as Harishan's personal AI Assistant.
        """
        lang = self.detect_language(incoming_message)
        is_urgent = self.check_is_urgent(incoming_message)
        is_media, media_type = self.is_media_message(incoming_message)

        # 1. If user set a custom auto-reply message template in settings
        custom_reply = self.settings.get("custom_auto_reply_message")
        if custom_reply and custom_reply.strip():
            clean_msg = custom_reply.strip()
            return clean_msg

        # 2. Dynamic AI Chat Agent with Groq LLM
        from app.services.llm_service import llm_service

        agent_name = "Friday"
        user_name = "Harishan"
        try:
            from app.services.command_executor import load_user_profile
            prof = load_user_profile()
            agent_name = prof.get("agent_profile", {}).get("agent_name") or prof.get("agent_name") or "Friday"
            user_name = prof.get("profile", {}).get("name") or prof.get("name") or "Harishan"
        except Exception:
            pass

        is_first_interaction = not bool(context and context.strip())

        system_instruction = (
            f"You are {agent_name}, the personal AI Assistant and smart mediator for {user_name}.\n"
            f"You are conversing on WhatsApp with '{{sender}}' on {user_name}'s behalf while he is occupied.\n"
            f"{user_name} is your primary user and boss. You act as the bridge/mediator between {user_name} and '{{sender}}'.\n\n"
            "IDENTITY & ROLE INSTRUCTIONS:\n"
            + (
                f"- INITIAL CONTACT: Introduce yourself politely as {user_name}'s AI Assistant/Mediator "
                f"(e.g., in English: 'Hello! I am {agent_name}, {user_name}'s personal AI Assistant.', "
                f"Tanglish: 'Hello! Naan {agent_name}, {user_name}-oda AI Assistant.', "
                f"Tamil: 'வணக்கம்! நான் {agent_name}, {user_name}-ன் AI உதவியாளர்.').\n"
                if is_first_interaction else
                f"- ONGOING CONVERSATION: Do NOT repeat your full introduction or greeting prefix! "
                f"Converse naturally as a mediator taking messages, answering queries, or assisting on {user_name}'s behalf.\n"
            ) +
            "\nLANGUAGE RULES:\n"
            "- If the incoming message is in Tamil (தமிழ்), reply entirely in Tamil script.\n"
            "- If the incoming message is in Tanglish (Tamil written in English alphabet), reply entirely in natural Tanglish.\n"
            "- If the incoming message is in English (or other), reply in clear, professional English.\n\n"
            "MEDIATOR BEHAVIOR RULES:\n"
            "1. Multi-Message Context: Address all thoughts/questions in the sender's message thoughtfully.\n"
            f"2. Attached Media/Files: Acknowledge receipt of images/documents/audio and confirm you forwarded them to {user_name}. Never ask for vision prompts.\n"
            f"3. Availability/Calls: State that {user_name} is currently engaged in work, and you have recorded their message to notify him.\n"
            f"4. Emergency/Urgency: If urgent, reassure the sender that you have immediately flagged it as HIGH PRIORITY for {user_name}.\n"
            "5. Tone: Polite, warm, concise, professional mediator. Limit reply to 2-3 complete sentences."
        )

        context_info = f"\nRecent Chat History from {sender}:\n{context}\n" if context else ""
        media_info = f"\nAttachment Detected: Sender sent a {media_type}.\n" if is_media else ""

        prompt = (
            f"Sender Name: {sender}\n"
            f"{context_info}"
            f"{media_info}"
            f"Incoming Message: \"{incoming_message}\"\n"
            f"Detected Language: {lang}\n"
            f"Urgency Status: {'URGENT' if is_urgent else 'Normal'}\n"
            f"Generate {agent_name}'s mediator response:"
        )

        try:
            res = llm_service.chat_completion(
                messages=[
                    {"role": "system", "content": system_instruction.format(sender=sender)},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=250
            )
            reply_text = res.get("content", "").strip().strip('"')

            # Clean any leading role tags
            for tag in [f"{agent_name.lower()}:", "friday:", "assistant:", "reply:", "response:"]:
                if reply_text.lower().startswith(tag):
                    reply_text = reply_text[len(tag):].strip()

            # Ensure proper prefix identity is present
            if lang == "tamil":
                if agent_name.lower() not in reply_text.lower() and "உதவியாளர்" not in reply_text:
                    reply_text = f"வணக்கம்! நான் {agent_name}, {user_name}-ன் AI உதவியாளர். {reply_text}"
            elif lang == "tanglish":
                if agent_name.lower() not in reply_text.lower() and "assistant" not in reply_text.lower():
                    reply_text = f"Hello! Naan {agent_name}, {user_name}-oda AI Assistant. {reply_text}"
            else:
                if agent_name.lower() not in reply_text.lower() and "assistant" not in reply_text.lower():
                    reply_text = f"Hello! I am {agent_name}, {user_name}'s personal AI Assistant. {reply_text}"

            # Validate sentence completeness
            dangling_words = ["is", "and", "to", "with", "the", "that", "for", "in", "on", "at", "a", "an", "oru", "la", "oda", "ku"]
            last_word = reply_text.split()[-1].lower().strip(".,!?") if reply_text.split() else ""
            is_cut_off = not reply_text.endswith(('.', '!', '?', '।', 'அ')) or last_word in dangling_words

            if reply_text and not is_cut_off and len(reply_text) > 15:
                return reply_text
            elif reply_text and len(reply_text) > 15:
                if not reply_text.endswith(('.', '!', '?')):
                    return reply_text + "."
                return reply_text
        except Exception as e:
            logger.warning(f"AI auto-reply generation fallback: {e}")

        # Deterministic fallback responses tailored by language and urgency
        if is_urgent:
            if lang == "tamil":
                return f"வணக்கம்! நான் {agent_name}, {user_name}-ன் AI உதவியாளர். {sender}, உங்கள் அவசர செய்தியைப் பெற்றுக்கொண்டேன்; உடனடியாக {user_name}-யிடம் தெரிவித்துள்ளேன்!"
            elif lang == "tanglish":
                return f"Hello! Naan {agent_name}, {user_name}-oda AI Assistant. Hi {sender}, idhu urgent message nu therinjidhu, udane {user_name} kitta inform pannitten!"
            else:
                return f"Hello! I am {agent_name}, {user_name}'s personal AI Assistant. Hi {sender}, I have recognized your message as URGENT and immediately alerted {user_name}!"
        elif is_media:
            if lang == "tamil":
                return f"வணக்கம்! நான் {agent_name}, {user_name}-ன் AI உதவியாளர். {sender}, நீங்கள் அனுப்பிய கோப்பைப் பெற்றுக்கொண்டேன். {user_name} ஓய்வு பெற்றதும் அதைப் பார்வையிடுவார்."
            elif lang == "tanglish":
                return f"Hello! Naan {agent_name}, {user_name}-oda AI Assistant. Hi {sender}, neenga anuppuna file-a safe-a receive pannitten. {user_name} free aana udane check pannuvaaru!"
            else:
                return f"Hello! I am {agent_name}, {user_name}'s personal AI Assistant. Hi {sender}, I have received the attachment you sent and forwarded it to {user_name} for review."
        else:
            if lang == "tamil":
                return f"வணக்கம்! நான் {agent_name}, {user_name}-ன் AI உதவியாளர். {sender}, உங்கள் செய்தியைப் பெற்றுக்கொண்டேன். {user_name} தற்போது முக்கிய பணியில் உள்ளார், விரைவில் உங்களைத் தொடர்புகொள்வார்."
            elif lang == "tanglish":
                return f"Hello! Naan {agent_name}, {user_name}-oda AI Assistant. Hi {sender}, {user_name} ipo important work-la irukkaru. Unga message-a avartta sollitten, seekiram ungala contact pannuvaaru."
            else:
                return f"Hello! I am {agent_name}, {user_name}'s personal AI Assistant. Hi {sender}, {user_name} is currently occupied with high-priority work. I have forwarded your message to him and alerted him!"

    # -------------------------------------------------------------
    # BACKGROUND NOTIFICATION MONITOR LOOP
    # -------------------------------------------------------------
    def _is_group_notification(self, sender: str, texts: List[str], msg: str) -> bool:
        """Detects whether a notification originated from a WhatsApp Group rather than a direct 1-on-1 chat."""
        import re
        # 1. 3 or more text elements in toast: [Group Name, Sender in Group, Message]
        if len(texts) >= 3:
            return True

        # 2. Toast body has sender prefix "PersonName: Message" (standard WhatsApp group format)
        if len(texts) >= 2 and re.match(r'^[A-Za-z0-9_\s\+\(\)\.]{1,35}:\s+', texts[1]):
            return True

        # 3. Sender name contains explicit group indicators
        s_lower = sender.lower()
        group_keywords = [
            "group", "team", "batch", "club", "family", "community",
            "friends", "gang", "class", "official", "announcements",
            "updates", "committee", "society", "dept", "department", "project"
        ]
        if any(k in s_lower for k in group_keywords):
            return True

        # 4. Message or sender has participant counters
        if re.search(r'\(\d+\s*(?:messages?|participants?|members?)\)', s_lower):
            return True

        return False

    def _is_unknown_number(self, sender: str) -> bool:
        """
        Detects whether the sender is an unsaved / unknown phone number rather than a saved contact name.
        """
        import re
        s_clean = sender.strip()
        if not s_clean or s_clean.lower() in ["unknown", "unknown number", "anonymous", "private number"]:
            return True

        # Strip standard international and phone formatting characters (+, spaces, hyphens, parentheses)
        digits_only = re.sub(r'[\s\+\-\(\)]', '', s_clean)

        # If the string consists entirely of digits and is a phone number length (>= 7 digits)
        if digits_only.isdigit() and len(digits_only) >= 7:
            return True

        # If sender starts with '+' and has >= 7 digits
        if s_clean.startswith("+") and sum(c.isdigit() for c in s_clean) >= 7:
            return True

        # If sender matches international phone number regex format
        if re.match(r'^\+?\d{1,4}[\s\-\(\)]*\d{2,5}[\s\-\(\)]*\d{3,6}$', s_clean):
            return True

        return False

    async def _fetch_toast_notifications(self) -> List[Dict[str, Any]]:
        """Reads active Windows WhatsApp notifications, clearing stale backlog toasts."""
        if not _WINSDK_AVAILABLE:
            return []

        try:
            listener = UserNotificationListener.current
            # Only request access if not already validated
            if not getattr(self, "_listener_access_granted", False):
                try:
                    access = await asyncio.wait_for(listener.request_access_async(), timeout=2.0)
                    self._listener_access_granted = (int(access) == 1)
                except Exception:
                    self._listener_access_granted = False
                    return []

            if not getattr(self, "_listener_access_granted", False):
                return []

            try:
                notifs = await asyncio.wait_for(listener.get_notifications_async(NotificationKinds.TOAST), timeout=1.5)
            except Exception:
                return []

            results = []
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            min_allowed_time = (self._monitor_start_time - datetime.timedelta(seconds=60)) if self._monitor_start_time else (now_utc - datetime.timedelta(seconds=90))

            for n in notifs:
                try:
                    app_name = ""
                    app_id = ""
                    try:
                        if hasattr(n, "app_info") and n.app_info:
                            try:
                                if hasattr(n.app_info, "display_info") and n.app_info.display_info:
                                    app_name = str(n.app_info.display_info.display_name or "").lower()
                            except Exception:
                                pass
                            try:
                                app_id = str(n.app_info.id or "").lower()
                            except Exception:
                                pass
                    except Exception:
                        pass

                    texts = []
                    try:
                        if hasattr(n, "notification") and n.notification:
                            if hasattr(n.notification, "visual") and n.notification.visual:
                                for b in n.notification.visual.bindings:
                                    for t in b.get_text_elements():
                                        if t.text and t.text.strip():
                                            texts.append(t.text.strip())
                    except Exception:
                        pass

                    is_wa = "whatsapp" in app_name or "whatsapp" in app_id
                    if not is_wa:
                        for t in texts:
                            if "whatsapp" in t.lower():
                                is_wa = True
                                break

                    if is_wa and texts:
                        # Check timestamp freshness: ignore notifications older than monitor window
                        c_time = getattr(n, "creation_time", None)
                        try:
                            if c_time and hasattr(c_time, "tzinfo") and min_allowed_time and hasattr(min_allowed_time, "tzinfo"):
                                if c_time < min_allowed_time:
                                    try:
                                        listener.remove_notification(n.id)
                                    except Exception:
                                        pass
                                    continue
                        except Exception:
                            pass

                        if texts[0].lower() in ["whatsapp", "whatsapp desktop"] and len(texts) > 1:
                            sender = texts[1]
                            msg = " - ".join(texts[2:]) if len(texts) > 2 else ""
                        else:
                            sender = texts[0]
                            msg = " - ".join(texts[1:]) if len(texts) > 1 else ""

                        is_group = self._is_group_notification(sender, texts, msg)
                        results.append({
                            "id": n.id,
                            "sender": sender,
                            "message": msg,
                            "is_group": is_group,
                            "creation_time": c_time,
                            "raw_texts": texts
                        })
                except Exception:
                    continue
            return results
        except Exception as e:
            logger.error(f"Error reading toast notifications: {e}")
            return []

    def _monitor_loop(self):
        """Background thread polling incoming notifications with deduplication, spoken alerts, and auto-reply."""
        logger.info("[WhatsApp Monitor] Background thread started.")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self._monitoring_active:
            try:
                now_ts = time.time()
                # Sliding window TTL: prune signatures older than 45s
                self._replied_signatures = {k: v for k, v in self._replied_signatures.items() if now_ts - v < 45.0}

                notifications = loop.run_until_complete(self._fetch_toast_notifications())
                for notif in notifications:
                    notif_id = notif.get("id")
                    sender = notif.get("sender", "Unknown").strip()
                    msg_text = notif.get("message", "").strip()
                    is_group = notif.get("is_group", False)
                    raw_texts = notif.get("raw_texts", [])

                    msg_sig = f"{sender.lower()}:{msg_text.lower()}"

                    if notif_id:
                        if notif_id in self._replied_ids or (msg_sig in self._replied_signatures and (now_ts - self._replied_signatures[msg_sig]) < 30.0):
                            if _WINSDK_AVAILABLE:
                                try:
                                    UserNotificationListener.current.remove_notification(notif_id)
                                except Exception:
                                    pass
                            continue

                        self._replied_ids.add(notif_id)
                        self._replied_signatures[msg_sig] = now_ts

                        # Dismiss the notification from Windows Action Center immediately
                        if _WINSDK_AVAILABLE:
                            try:
                                UserNotificationListener.current.remove_notification(notif_id)
                            except Exception:
                                pass

                        # Check if this is an incoming call notification across all text elements
                        full_toast_text = " ".join(raw_texts).lower()
                        is_call = any(k in full_toast_text for k in [
                            "incoming voice call", "incoming video call", "voice call",
                            "video call", "calling...", "incoming call", "whatsapp call"
                        ])
                        if is_call:
                            c_type = "video" if "video" in full_toast_text else "voice"
                            self.latest_incoming_call = {
                                "id": notif_id,
                                "caller": sender,
                                "call_type": c_type,
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            self._play_incoming_call_alert(sender, c_type)
                            continue

                        logger.info(f"[WhatsApp Monitor] Incoming message from '{sender}': {msg_text}")

                        # Check urgency and record for immediate user interruption
                        is_urgent = self.check_is_urgent(msg_text)
                        if is_urgent:
                            self.latest_urgent_alert = {
                                "id": notif_id,
                                "sender": sender,
                                "message": msg_text,
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            }

                        # Save latest received message for quick follow-up replies
                        self.latest_received_message = {
                            "id": notif_id,
                            "sender": sender,
                            "message": msg_text,
                            "timestamp": time.time()
                        }

                        # Spoken notification to user based on notify settings
                        notify_mode = self.settings.get("notify_mode", "all")
                        filter_contact = self.settings.get("notify_target_contact")
                        should_speak = False
                        if notify_mode == "all":
                            should_speak = True
                        elif notify_mode == "urgent" and is_urgent:
                            should_speak = True
                        elif filter_contact and (filter_contact.lower() in sender.lower() or sender.lower() in filter_contact.lower()):
                            should_speak = True

                        if should_speak:
                            self._play_spoken_notification(sender, msg_text)
                        elif is_urgent:
                            self._play_urgent_voice_alert(sender, msg_text)

                        # Record incoming message in sender conversation history
                        self.record_sender_message(sender, msg_text, role="contact")
                        sender_context = self.get_sender_context(sender)

                        # STRICT REQUIREMENT: Only auto-reply if enabled AND not a group AND not an unknown number
                        can_auto_reply = (
                            self.settings.get("auto_reply", False)
                            and bool(msg_text)
                            and not is_group
                            and not self._is_unknown_number(sender)
                        )

                        if can_auto_reply:
                            reply = self.generate_auto_reply(sender, msg_text, context=sender_context)
                            self.record_sender_message(sender, reply, role="assistant")
                            self.send_message(sender, reply)
                            self._log_message_event(sender, msg_text, reply, is_urgent=is_urgent)

                            self.settings["replied_count"] = self.settings.get("replied_count", 0) + 1
                            self.settings["last_activity"] = time.strftime("%Y-%m-%d %H:%M:%S")
                            self._save_settings()

                            # Safely minimize only WhatsApp if open
                            if self.window and _UIA_AVAILABLE:
                                try:
                                    wp = self.window.GetWindowPattern()
                                    if wp:
                                        wp.SetWindowVisualState(auto.WindowVisualState.Minimized)
                                except Exception:
                                    pass
                        else:
                            self._log_message_event(sender, msg_text, reply_sent="", is_urgent=is_urgent)
                            self.settings["last_activity"] = time.strftime("%Y-%m-%d %H:%M:%S")
                            self._save_settings()

            except Exception as e:
                logger.error(f"[WhatsApp Monitor] Polling error: {e}")

            # Adaptive power-aware polling: longer sleep if running on battery to preserve power
            on_battery = False
            try:
                b = psutil.sensors_battery()
                if b and not b.power_plugged:
                    on_battery = True
            except Exception:
                pass

            sleep_steps = 10 if on_battery else 5
            for _ in range(sleep_steps):
                if not self._monitoring_active:
                    break
                time.sleep(0.2)

        loop.close()
        logger.info("[WhatsApp Monitor] Background thread terminated.")

    def set_monitoring(
        self,
        enabled: Optional[bool] = None,
        auto_reply: Optional[bool] = None,
        custom_auto_reply_message: Optional[str] = None,
        notify_mode: Optional[str] = None,
        notify_target_contact: Optional[str] = None
    ) -> Dict[str, Any]:
        """Toggles background WhatsApp monitoring on or off and configures auto-reply parameters."""
        if enabled is not None:
            self.settings["enabled"] = enabled
        if auto_reply is not None:
            self.settings["auto_reply"] = auto_reply
            if auto_reply:
                self.settings["enabled"] = True
        if custom_auto_reply_message is not None:
            self.settings["custom_auto_reply_message"] = custom_auto_reply_message
        if notify_mode is not None:
            self.settings["notify_mode"] = notify_mode
        if notify_target_contact is not None:
            self.settings["notify_target_contact"] = notify_target_contact

        current_enabled = self.settings.get("enabled", False)
        if current_enabled:
            if not self._monitoring_active:
                self._monitoring_active = True
                self._monitor_start_time = datetime.datetime.now(datetime.timezone.utc)
                self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                self._monitor_thread.start()
        else:
            self._monitoring_active = False

        self.settings["monitoring_active"] = self._monitoring_active
        self._save_settings()

        return {
            "status": "success",
            "monitoring_active": self._monitoring_active,
            "auto_reply": self.settings.get("auto_reply", False),
            "custom_auto_reply_message": self.settings.get("custom_auto_reply_message"),
            "notify_mode": self.settings.get("notify_mode", "all"),
            "notify_target_contact": self.settings.get("notify_target_contact"),
            "winsdk_available": _WINSDK_AVAILABLE,
            "uia_available": _UIA_AVAILABLE
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns the current status of the WhatsApp Plugin."""
        return {
            "enabled": self.settings.get("enabled", False),
            "monitoring_active": self._monitoring_active,
            "auto_reply": self.settings.get("auto_reply", False),
            "custom_auto_reply_message": self.settings.get("custom_auto_reply_message"),
            "notify_mode": self.settings.get("notify_mode", "all"),
            "notify_target_contact": self.settings.get("notify_target_contact"),
            "replied_count": self.settings.get("replied_count", 0),
            "last_activity": self.settings.get("last_activity"),
            "winsdk_available": _WINSDK_AVAILABLE,
            "uia_available": _UIA_AVAILABLE,
            "pyautogui_available": _PYAUTOGUI_AVAILABLE
        }


whatsapp_service = WhatsAppService()
