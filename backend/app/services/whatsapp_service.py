"""
WhatsApp Desktop Automation and Background Monitoring Service for Friday AI Assistant.
Supports UI automation, contact search, messaging, voice/video calls, and background Windows toast monitoring with AI auto-replies.
"""

from __future__ import annotations

import os
import sys
import time
import json
import asyncio
import logging
import threading
import subprocess
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
    "auto_reply": True,
    "monitoring_active": False,
    "custom_auto_reply_message": None,
    "auto_reply_template": "default",
    "replied_count": 0,
    "last_activity": None
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
        self._replied_ids: set = set()
        self.settings = self._load_settings()
        self.window = None

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

    # -------------------------------------------------------------
    # WINDOW FOCUS & DETECTION
    # -------------------------------------------------------------
    def find_or_focus_whatsapp(self, timeout: float = 3.5) -> bool:
        """Locates and brings WhatsApp Desktop to the foreground safely."""
        self.window = None
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 1. Win32 HWND direct foreground unlock
            hwnd = find_whatsapp_hwnd()
            if hwnd:
                force_focus_hwnd(hwnd)
                time.sleep(0.3)

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
                            time.sleep(0.2)
                        except Exception:
                            pass
                        return True
                except Exception as e:
                    logger.warning(f"UIA WhatsApp search error: {e}")

            # 3. Launch protocol if window not visible
            if time.time() - start_time < 1.0:
                try:
                    os.system("start whatsapp:")
                except Exception:
                    pass

            time.sleep(0.4)

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
            self.find_or_focus_whatsapp(timeout=2.0)
            answered = False
            if _UIA_AVAILABLE and self.window:
                try:
                    for name in ["Accept", "Answer", "Accept call", "Accept voice call", "Accept video call", "Pick up"]:
                        btn = self.window.ButtonControl(searchDepth=15, Name=name)
                        if btn.Exists(0.3, 1):
                            btn.Click(waitTime=0.2)
                            answered = True
                            break
                except Exception:
                    pass

            if not answered and _PYAUTOGUI_AVAILABLE and is_whatsapp_in_foreground():
                pyautogui.hotkey('alt', 'a')
                time.sleep(0.2)
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
    def generate_auto_reply(self, sender: str, incoming_message: str) -> str:
        """
        Generates a smart, polite, multilingual AI chat agent reply on Harishan's behalf.
        - Converses intelligently like an AI chat / customer service agent based on the sender's message.
        - Tells the sender about Friday when asked.
        - Supports English, Tanglish (e.g. 'Enna panra Friday?'), and Tamil (e.g. 'ஹரிஷன் எங்கே?').
        - Flags urgency immediately if critical.
        - Compulsorily includes Friday's identity as Harishan's personal AI Assistant.
        """
        lang = self.detect_language(incoming_message)
        is_urgent = self.check_is_urgent(incoming_message)

        # 1. If user set a custom auto-reply message template in settings
        custom_reply = self.settings.get("custom_auto_reply_message")
        if custom_reply and custom_reply.strip():
            clean_msg = custom_reply.strip()
            if "friday" in clean_msg.lower() and "assistant" in clean_msg.lower():
                return clean_msg
            return f"Hello! I am Friday, Harishan's personal AI Assistant. {clean_msg}"

        # 2. Dynamic AI Chat Agent with Groq LLM
        from app.services.llm_service import llm_service

        system_instruction = (
            "You are Friday, Harishan's intelligent personal AI Assistant and customer service chat agent on WhatsApp.\n"
            "You are conversing with '{sender}' on Harishan's behalf while he is occupied with work.\n\n"
            "MANDATORY IDENTITY REQUIREMENT:\n"
            "Every single response MUST clearly include your introduction as Harishan's AI Assistant:\n"
            "- In English: 'Hello! I am Friday, Harishan's personal AI Assistant.'\n"
            "- In Tanglish: 'Hello! Naan Friday, Harishan-oda AI Assistant.'\n"
            "- In Tamil: 'வணக்கம்! நான் Friday, ஹரிஷனின் AI உதவியாளர்.'\n\n"
            "LANGUAGE RULES:\n"
            "- If the incoming message is in Tamil (தமிழ்), reply entirely in Tamil script.\n"
            "- If the incoming message is in Tanglish (Tamil written in English alphabet, like 'enna panra', 'eppo varuvaaru', 'epdi iruka'), reply entirely in natural, fluent Tanglish.\n"
            "- If the incoming message is in English (or other), reply in clear, professional English.\n\n"
            "AGENT BEHAVIOR & CONVERSATION RULES:\n"
            "1. If the sender asks about Friday (e.g., 'tell me more about you', 'what can you do', 'who are you', 'who made you'): Explain Friday's role as Harishan's intelligent personal AI assistant who manages tasks, WhatsApp, schedule, and desktop automation on Windows.\n"
            "2. If the sender asks about Harishan or asks him to call/message back: State that Harishan is currently engaged in high-priority work, and you have recorded their message and notified him.\n"
            "3. If the message indicates URGENCY / EMERGENCY (e.g., 'urgent', 'emergency', 'accident', 'call immediately'): Acknowledge the urgency immediately and confirm that you have marked it as HIGH PRIORITY and alerted Harishan right away.\n"
            "4. Conversational Style: Be polite, warm, concise, and helpful (like a top-tier AI customer service assistant). Limit response to 2 to 3 well-formed complete sentences. Never leave sentences unfinished."
        )

        prompt = (
            f"Sender Name: {sender}\n"
            f"Incoming Message: \"{incoming_message}\"\n"
            f"Detected Language: {lang}\n"
            f"Urgency Status: {'URGENT' if is_urgent else 'Normal'}\n"
            f"Generate Friday's WhatsApp reply:"
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
            for tag in ["friday:", "assistant:", "reply:", "response:"]:
                if reply_text.lower().startswith(tag):
                    reply_text = reply_text[len(tag):].strip()

            # Ensure proper prefix identity is present
            if lang == "tamil":
                if "friday" not in reply_text.lower() and "உதவியாளர்" not in reply_text:
                    reply_text = f"வணக்கம்! நான் Friday, ஹரிஷனின் AI உதவியாளர். {reply_text}"
            elif lang == "tanglish":
                if "friday" not in reply_text.lower() and "assistant" not in reply_text.lower():
                    reply_text = f"Hello! Naan Friday, Harishan-oda AI Assistant. {reply_text}"
            else:
                if "friday" not in reply_text.lower() and "assistant" not in reply_text.lower():
                    reply_text = f"Hello! I am Friday, Harishan's personal AI Assistant. {reply_text}"

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
                return f"வணக்கம்! நான் Friday, ஹரிஷனின் AI உதவியாளர். {sender}, உங்கள் அவசர செய்தியைப் பெற்றுக்கொண்டேன்; உடனடியாக ஹரிஷனிடம் தெரிவித்துள்ளேன்!"
            elif lang == "tanglish":
                return f"Hello! Naan Friday, Harishan-oda AI Assistant. Hi {sender}, idhu urgent message nu therinjidhu, udane Harishan kitta inform pannitten!"
            else:
                return f"Hello! I am Friday, Harishan's personal AI Assistant. Hi {sender}, I have recognized your message as URGENT and immediately alerted Harishan!"
        else:
            if lang == "tamil":
                return f"வணக்கம்! நான் Friday, ஹரிஷனின் AI உதவியாளர். {sender}, உங்கள் செய்தியைப் பெற்றுக்கொண்டேன். ஹரிஷன் தற்போது முக்கிய பணியில் உள்ளார், விரைவில் உங்களைத் தொடர்புகொள்வார்."
            elif lang == "tanglish":
                return f"Hello! Naan Friday, Harishan-oda AI Assistant. Hi {sender}, Harishan ipo important work-la irukkaru. Unga message-a avartta sollitten, seekiram ungala contact pannuvaaru."
            else:
                return f"Hello! I am Friday, Harishan's personal AI Assistant. Hi {sender}, Harishan is currently occupied with high-priority work. I have forwarded your message to him and alerted him!"

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
        """Reads active Windows WhatsApp notifications."""
        if not _WINSDK_AVAILABLE:
            return []

        try:
            listener = UserNotificationListener.current
            try:
                access = await asyncio.wait_for(listener.request_access_async(), timeout=1.5)
            except Exception:
                return []

            if int(access) != 1:
                return []

            try:
                notifs = await asyncio.wait_for(listener.get_notifications_async(NotificationKinds.TOAST), timeout=1.5)
            except Exception:
                return []

            results = []
            for n in notifs:
                try:
                    app_name = (n.app_info.display_info.display_name or "").lower()
                    app_id = (n.app_info.id or "").lower()
                    if "whatsapp" in app_name or "whatsapp" in app_id:
                        bindings = n.notification.visual.bindings
                        texts = []
                        for b in bindings:
                            for t in b.get_text_elements():
                                if t.text and t.text.strip():
                                    texts.append(t.text.strip())

                        if texts:
                            sender = texts[0]
                            msg = " - ".join(texts[1:]) if len(texts) > 1 else ""
                            is_group = self._is_group_notification(sender, texts, msg)
                            results.append({
                                "id": n.id,
                                "sender": sender,
                                "message": msg,
                                "is_group": is_group
                            })
                except Exception:
                    continue
            return results
        except Exception as e:
            logger.error(f"Error reading toast notifications: {e}")
            return []

    def _monitor_loop(self):
        """Background thread polling incoming notifications."""
        logger.info("[WhatsApp Monitor] Background thread started.")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self._monitoring_active:
            try:
                notifications = loop.run_until_complete(self._fetch_toast_notifications())
                for notif in notifications:
                    notif_id = notif.get("id")
                    sender = notif.get("sender", "Unknown")
                    msg_text = notif.get("message", "")
                    is_group = notif.get("is_group", False)

                    if notif_id and notif_id not in self._replied_ids:
                        self._replied_ids.add(notif_id)

                        # STRICT REQUIREMENT 1: Never auto-reply to group chats
                        if is_group:
                            logger.info(f"[WhatsApp Monitor] Skipped auto-reply for group message from '{sender}': '{msg_text}'")
                            continue

                        # STRICT REQUIREMENT 2: Never auto-reply to unknown / unsaved numbers
                        if self._is_unknown_number(sender):
                            logger.info(f"[WhatsApp Monitor] Skipped auto-reply for unknown number '{sender}': '{msg_text}'")
                            continue

                        logger.info(f"[WhatsApp Monitor] New direct message from saved contact {sender}: {msg_text}")

                        is_urgent = self.check_is_urgent(msg_text)

                        # If Auto-Reply is enabled for direct saved contacts
                        if self.settings.get("auto_reply", True):
                            reply = self.generate_auto_reply(sender, msg_text)
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

            except Exception as e:
                logger.error(f"[WhatsApp Monitor] Polling error: {e}")

            for _ in range(15):
                if not self._monitoring_active:
                    break
                time.sleep(0.2)

        loop.close()
        logger.info("[WhatsApp Monitor] Background thread terminated.")

    def set_monitoring(self, enabled: bool, auto_reply: Optional[bool] = None, custom_auto_reply_message: Optional[str] = None) -> Dict[str, Any]:
        """Toggles background WhatsApp monitoring on or off."""
        self.settings["enabled"] = enabled
        if auto_reply is not None:
            self.settings["auto_reply"] = auto_reply
        if custom_auto_reply_message is not None:
            self.settings["custom_auto_reply_message"] = custom_auto_reply_message

        if enabled:
            if not self._monitoring_active:
                self._monitoring_active = True
                self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                self._monitor_thread.start()
        else:
            self._monitoring_active = False

        self.settings["monitoring_active"] = self._monitoring_active
        self._save_settings()

        return {
            "status": "success",
            "monitoring_active": self._monitoring_active,
            "auto_reply": self.settings.get("auto_reply", True),
            "custom_auto_reply_message": self.settings.get("custom_auto_reply_message"),
            "winsdk_available": _WINSDK_AVAILABLE,
            "uia_available": _UIA_AVAILABLE
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns the current status of the WhatsApp Plugin."""
        return {
            "enabled": self.settings.get("enabled", False),
            "monitoring_active": self._monitoring_active,
            "auto_reply": self.settings.get("auto_reply", True),
            "custom_auto_reply_message": self.settings.get("custom_auto_reply_message"),
            "replied_count": self.settings.get("replied_count", 0),
            "last_activity": self.settings.get("last_activity"),
            "winsdk_available": _WINSDK_AVAILABLE,
            "uia_available": _UIA_AVAILABLE,
            "pyautogui_available": _PYAUTOGUI_AVAILABLE
        }


whatsapp_service = WhatsAppService()
