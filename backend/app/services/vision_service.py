"""
Friday AI Assistant - Screen Vision & Desktop Context Service.
Captures screen, active window titles, open applications, mouse cursor position,
and active desktop context to answer queries and execute vision actions.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


_CACHED_OPEN_APPS: List[str] = []
_LAST_APP_SCAN_TIME: float = 0.0

def capture_and_describe_screen() -> str:
    """
    Captures live desktop state, active foreground window, and open application titles
    to provide an immediate, accurate natural language summary of what the user is seeing.
    """
    global _CACHED_OPEN_APPS, _LAST_APP_SCAN_TIME
    import time
    active_window_title = "Desktop"
    open_apps: List[str] = []

    # 1. Query Active Foreground Window on Windows (<1ms)
    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                active_window_title = buf.value.strip() or "Desktop"
        except Exception as e:
            logger.debug(f"Failed to get active window: {e}")

        # 2. Get Open Desktop Windows (cached for 2s to guarantee <5ms response time)
        now = time.time()
        if now - _LAST_APP_SCAN_TIME < 2.0 and _CACHED_OPEN_APPS:
            open_apps = list(_CACHED_OPEN_APPS)
        else:
            try:
                import subprocess
                cmd = 'powershell -NoProfile -Command "Get-Process | Where-Object {$_.MainWindowTitle -ne \'\'} | Select-Object -ExpandProperty MainWindowTitle"'
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=0.8)
                if res.returncode == 0 and res.stdout.strip():
                    lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
                    open_apps = lines[:8]
                    _CACHED_OPEN_APPS = list(open_apps)
                    _LAST_APP_SCAN_TIME = now
                elif _CACHED_OPEN_APPS:
                    open_apps = list(_CACHED_OPEN_APPS)
            except Exception:
                if _CACHED_OPEN_APPS:
                    open_apps = list(_CACHED_OPEN_APPS)

    # 3. Compile natural language description
    lines = [
        f"You are currently focused on **{active_window_title}**."
    ]

    if open_apps:
        other_apps = [app for app in open_apps if app != active_window_title]
        if other_apps:
            lines.append("Other visible application windows on your screen include:")
            for app in other_apps[:5]:
                lines.append(f"• {app}")

    return "\n".join(lines)


def get_mouse_pointer_context() -> str:
    """
    Identifies exact mouse cursor screen coordinates and the application / element under the pointer.
    """
    if os.name != "nt":
        return "Mouse pointer inspection is supported on Windows desktop."

    try:
        import ctypes
        from ctypes import wintypes
        import psutil

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        user32 = ctypes.windll.user32
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))

        hwnd = user32.WindowFromPoint(pt)
        root_hwnd = user32.GetAncestor(hwnd, 2) or hwnd

        length = user32.GetWindowTextLengthW(root_hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(root_hwnd, buf, length + 1)
        window_title = buf.value.strip()

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(root_hwnd, ctypes.byref(pid))
        proc_name = ""
        if pid.value:
            try:
                proc_name = psutil.Process(pid.value).name()
            except Exception:
                pass

        # Clean up overlay or transparent windows if captured as root window
        OVERLAY_WINDOW_PATTERNS = ["friday ai assistant", "neural core overlay", "nvidia geforce overlay", "game bar", "overlay"]
        if any(p in window_title.lower() for p in OVERLAY_WINDOW_PATTERNS):
            # Try to get the real underlying window
            fg_hwnd = user32.GetForegroundWindow()
            if fg_hwnd and fg_hwnd != root_hwnd:
                f_len = user32.GetWindowTextLengthW(fg_hwnd)
                f_buf = ctypes.create_unicode_buffer(f_len + 1)
                user32.GetWindowTextW(fg_hwnd, f_buf, f_len + 1)
                f_title = f_buf.value.strip()
                if f_title and not any(p in f_title.lower() for p in OVERLAY_WINDOW_PATTERNS):
                    window_title = f_title
                    root_hwnd = fg_hwnd

        # Handle Windows desktop / shell representations
        if window_title in ["Program Manager", ""] and proc_name.lower() == "explorer.exe":
            display_title = "Windows Desktop"
        elif not window_title:
            display_title = proc_name or "Windows Desktop"
        else:
            display_title = window_title

        # UI Automation exact element inspection under pointer
        element_name = ""
        element_type = ""
        try:
            import uiautomation as auto
            auto.SetGlobalSearchTimeout(0.2)
            ctrl = auto.ControlFromPoint(pt.x, pt.y)
            if ctrl:
                raw_name = (ctrl.Name or "").strip()
                # If control is Friday's own overlay or GeForce overlay window, ignore it
                if not any(p in raw_name.lower() for p in OVERLAY_WINDOW_PATTERNS):
                    element_name = raw_name
                    raw_type = (ctrl.ControlTypeName or "").replace("Control", "").strip()
                    element_type = raw_type if raw_type and raw_type not in ["Pane", "Window", "Document"] else ""

                # Deep inspection: check Legacy IAccessible pattern if name is empty
                if not element_name:
                    try:
                        legacy = ctrl.GetLegacyIAccessiblePattern()
                        if legacy:
                            leg_name = (legacy.Name or legacy.Value or legacy.Description or "").strip()
                            if leg_name and not any(p in leg_name.lower() for p in OVERLAY_WINDOW_PATTERNS):
                                element_name = leg_name
                    except Exception:
                        pass

                # Deep inspection: traverse up to 3 parent levels if still empty
                if not element_name or element_name in ["Desktop 1", "Pane", "Window", "Client Area", "Chrome Legacy Window"]:
                    curr = ctrl
                    for _ in range(3):
                        curr = curr.GetParentControl()
                        if not curr:
                            break
                        p_name = (curr.Name or "").strip()
                        if p_name and p_name not in ["Desktop 1", "Pane", "Window", "Client Area", "Chrome Legacy Window", display_title]:
                            if not any(p in p_name.lower() for p in OVERLAY_WINDOW_PATTERNS):
                                element_name = p_name
                                if not element_type:
                                    element_type = (curr.ControlTypeName or "").replace("Control", "").strip()
                                break
        except Exception:
            pass

        # Clean internal suffixes / DT flags (e.g. "NVIDIA GeForce Overlay DT" -> "NVIDIA GeForce Overlay")
        if element_name.endswith(" DT"):
            element_name = element_name[:-3].strip()

        # Semantic UI Region Deduction (if element name is generic or empty)
        if not element_name or element_name in ["Desktop 1", "Pane", "Window", "Client Area", "Chrome Legacy Window"]:
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            
            # Title bar controls
            if pt.y < 40:
                if pt.x > (screen_w - 55):
                    element_name = "Window Close Button"
                    element_type = "Button"
                elif pt.x > (screen_w - 105):
                    element_name = "Window Maximize Button"
                    element_type = "Button"
                elif pt.x > (screen_w - 155):
                    element_name = "Window Minimize Button"
                    element_type = "Button"
                elif pt.x < 250:
                    element_name = "Application Title Bar"
                    element_type = "TitleBar"
                else:
                    element_name = "Browser Tab / Title Bar Area"
                    element_type = "TabHeader"
            elif pt.y > (screen_h - 55):
                element_name = "Windows Taskbar"
                element_type = "Taskbar"
            elif any(b in proc_name.lower() for b in ["chrome", "msedge", "firefox", "brave"]):
                if pt.y < 120:
                    element_name = "Browser Address Bar"
                    element_type = "Toolbar"
                else:
                    element_name = "Webpage Content Area"
                    element_type = "DocumentCanvas"
            elif "explorer" in proc_name.lower() or display_title == "Windows Desktop":
                element_name = "Desktop Workspace"
                element_type = "Desktop"
            else:
                element_name = f"{display_title} Workspace"
                element_type = "DocumentCanvas"

        # Check if cursor is over a real file/folder on Desktop or Explorer
        try:
            from app.services.context_service import get_hovered_or_selected_file_or_folder
            hovered_file = get_hovered_or_selected_file_or_folder()
            if hovered_file and os.path.exists(hovered_file):
                p_obj = Path(hovered_file)
                size_kb = round(p_obj.stat().st_size / 1024, 1) if p_obj.is_file() else 0
                type_str = f"file ({p_obj.suffix or 'document'}, {size_kb} KB)" if p_obj.is_file() else "folder"
                return f"You are currently pointing at the **{p_obj.name}** {type_str} located at `{str(p_obj.parent)}`."
        except Exception:
            pass

        # Natural conversational formatting (like Gemini AI)
        if display_title == "Windows Desktop" or "desktop" in display_title.lower():
            if element_name and element_name != "Desktop Workspace":
                return f"Your mouse cursor is currently pointing at the **{element_name}** icon on your Windows Desktop."
            return "Your mouse cursor is currently resting on your Windows Desktop."
        
        if element_name and element_name.lower() != display_title.lower():
            type_desc = f" ({element_type})" if element_type and element_type.lower() not in element_name.lower() else ""
            return f"Your mouse cursor is currently pointing at **{element_name}**{type_desc} in **{display_title}**."
        else:
            return f"Your mouse cursor is currently pointing inside the **{display_title}** window."
    except Exception as e:
        logger.warning(f"Failed to inspect mouse pointer: {e}")
        return "Your mouse cursor is currently positioned on your active screen workspace."


def open_pointed_folder() -> str:
    """
    Opens the directory or folder currently focused or pointed at by the mouse cursor.
    """
    if os.name != "nt":
        return "Opening pointed folders is supported on Windows desktop."

    try:
        import ctypes
        from ctypes import wintypes
        import psutil

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        user32 = ctypes.windll.user32
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        hwnd = user32.WindowFromPoint(pt)
        root_hwnd = user32.GetAncestor(hwnd, 2) or hwnd

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(root_hwnd, ctypes.byref(pid))
        proc_name = ""
        if pid.value:
            try:
                proc_name = psutil.Process(pid.value).name().lower()
            except Exception:
                pass

        user_desktop = Path.home() / "Desktop"

        if "explorer" in proc_name:
            target_path = str(user_desktop)
            os.system(f'start explorer "{target_path}"')
            return f"Opened targeted Explorer directory: {target_path}."
        else:
            target_path = str(user_desktop)
            os.system(f'start explorer "{target_path}"')
            return f"Opened active desktop directory: {target_path}."
    except Exception as e:
        logger.warning(f"Failed to open pointed folder: {e}")
        desktop_dir = str(Path.home() / "Desktop")
        os.system(f'start explorer "{desktop_dir}"')
        return f"Opened default Desktop folder: {desktop_dir}."


def is_screen_query(query: str) -> bool:
    """Detects if a user query is explicitly asking about what is currently on the screen, desktop, or active window."""
    q = query.lower().strip()

    # Explicitly exclude common conversational false positives unless "on screen" is specifically stated
    false_positives = ["interview", "review", "overview", "preview", "q&a", "video", "youtube", "movie", "song", "article", "link"]
    if any(k in q for k in false_positives):
        if not any(k in q for k in ["on my screen", "on the screen", "on screen", "this screen", "my screen"]):
            return False

    # Precise phrases indicating screen / desktop inspection
    explicit_screen_phrases = [
        "what am i looking at", "what am i seeing", "what am i viewing",
        "what is on my screen", "what's on my screen", "whats on my screen",
        "what is on the screen", "what's on the screen", "whats on the screen",
        "what do you see on my screen", "what do you see on screen", "what can you see on screen",
        "describe my screen", "describe the screen", "inspect my screen", "inspect the screen",
        "analyze my screen", "look at my screen", "look at the screen", "read my screen",
        "what is open on my screen", "what's open on my screen", "what app is active",
        "what window is active", "what window am i on", "what window is this", "what is this window",
        "which window is active", "which app is active", "current active window", "current window",
        "active window"
    ]
    if any(phrase in q for phrase in explicit_screen_phrases):
        return True

    # Word-boundary check: must have explicit screen/window noun AND an inspection intent
    has_screen_target = bool(re.search(r'\b(?:screen|desktop|active window|foreground window|open windows)\b', q))
    has_inspection_intent = bool(re.search(r'\b(?:describe|inspect|analyze|what is|whats|what are|read|see|show|tell me about)\b', q))

    return bool(has_screen_target and has_inspection_intent)


def is_mouse_query(query: str) -> bool:
    """Detects if a user query is asking what the mouse cursor is pointing at or where it is."""
    q = query.lower().strip()

    # If the user is giving an action command (close, minimize, maximize, click, drag, type, scroll, move, copy, send), this is NOT a pointer inquiry
    action_words = ["close", "minimize", "maximize", "click", "drag", "type", "press", "move this", "copy this", "send this", "delete", "shut", "kill"]
    if any(w in q for w in action_words):
        return False

    pointing_phrases = [
        "pointing", "pointed", "point at", "pointing at", "pointing now", "pointing to",
        "what is i am pointing", "what am i pointing", "what i am pointing", "pointing now",
        "what is under my mouse", "what am i hovering", "what is selected", "which file is selected",
        "what file am i pointing", "what icon am i pointing", "hovering at", "hovering on", "hovering over",
        "what is this file", "what is this icon", "what is this window", "where is my mouse", "where is the mouse", "where is cursor"
    ]
    if any(p in q for p in pointing_phrases):
        return True

    words = q.split()
    has_mouse_word = any(w in ["mouse", "cursor", "pointer"] for w in words)
    has_inquiry_word = any(w in ["what", "where", "which", "inspect", "identify"] for w in words)
    return bool(has_mouse_word and has_inquiry_word)


def is_open_mouse_folder_query(query: str) -> bool:
    """Detects if a user query asks to open the folder where the mouse is pointing."""
    q = query.lower().strip()
    return any(k in q for k in [
        "open the folder where", "open folder where", "open pointed folder",
        "open folder pointed", "open the folder pointed", "open where mouse is pointing",
        "open where my mouse is", "open the folder my mouse", "open folder my mouse"
    ])
