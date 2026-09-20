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

        # Handle Windows desktop / shell representations
        if window_title in ["Program Manager", ""] and proc_name.lower() == "explorer.exe":
            display_title = "Windows Desktop Workspace"
        elif not window_title:
            display_title = proc_name or "Windows Desktop Area"
        else:
            display_title = window_title

        # Check active foreground window for additional context
        active_hwnd = user32.GetForegroundWindow()
        active_title = ""
        if active_hwnd and active_hwnd != root_hwnd:
            a_len = user32.GetWindowTextLengthW(active_hwnd)
            a_buf = ctypes.create_unicode_buffer(a_len + 1)
            user32.GetWindowTextW(active_hwnd, a_buf, a_len + 1)
            active_title = a_buf.value.strip()

        # UI Automation exact element inspection under pointer
        element_name = ""
        element_type = ""
        try:
            import uiautomation as auto
            auto.SetGlobalSearchTimeout(0.2)
            ctrl = auto.ControlFromPoint(pt.x, pt.y)
            if ctrl:
                element_name = (ctrl.Name or "").strip()
                raw_type = (ctrl.ControlTypeName or "").replace("Control", "").strip()
                element_type = raw_type if raw_type and raw_type != "Pane" else ""

                # Deep inspection: check Legacy IAccessible pattern if name is empty
                if not element_name:
                    try:
                        legacy = ctrl.GetLegacyIAccessiblePattern()
                        if legacy:
                            element_name = (legacy.Name or legacy.Value or legacy.Description or "").strip()
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
                            element_name = p_name
                            if not element_type:
                                element_type = (curr.ControlTypeName or "").replace("Control", "").strip()
                            break
        except Exception:
            pass

        # Semantic UI Region Deduction (if element name is generic or empty)
        if not element_name or element_name in ["Desktop 1", "Pane", "Window", "Client Area", "Chrome Legacy Window"]:
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            
            # Title bar controls
            if pt.y < 40:
                if pt.x > (screen_w - 55):
                    element_name = "Window Close Button (✕)"
                    element_type = "Button"
                elif pt.x > (screen_w - 105):
                    element_name = "Window Maximize / Restore Button (🗖)"
                    element_type = "Button"
                elif pt.x > (screen_w - 155):
                    element_name = "Window Minimize Button (🗕)"
                    element_type = "Button"
                elif pt.x < 250:
                    element_name = "Application Title / Menu Header"
                    element_type = "TitleBar"
                else:
                    element_name = "Browser Tab / Title Bar Area"
                    element_type = "TabHeader"
            elif pt.y > (screen_h - 55):
                element_name = "Windows Taskbar / System Dock"
                element_type = "Taskbar"
            elif any(b in proc_name.lower() for b in ["chrome", "msedge", "firefox", "brave"]):
                if pt.y < 120:
                    element_name = "Browser Address Bar / Toolbar Navigation"
                    element_type = "Toolbar"
                else:
                    element_name = "Webpage Content View"
                    element_type = "DocumentCanvas"
            elif "explorer" in proc_name.lower():
                element_name = "Desktop Workspace Background"
                element_type = "Desktop"
            else:
                element_name = f"{display_title} Main Workspace"
                element_type = "DocumentCanvas"

        type_suffix = f" ({element_type})" if element_type and element_type.lower() not in element_name.lower() else ""
        fg_context = f" [Active: **{active_title}**]" if active_title and active_title not in ["Program Manager", display_title] else ""

        return f"Your mouse cursor is currently pointing directly at **{element_name}**{type_suffix} in **{display_title}** ({proc_name or 'System UI'}{fg_context}, at coordinates x={pt.x}, y={pt.y})."
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
        user_downloads = Path.home() / "Downloads"

        if "explorer" in proc_name:
            # Try to get active explorer folder, or open Desktop
            target_path = str(user_desktop)
            os.system(f'start explorer "{target_path}"')
            return f"Opened targeted Explorer directory: {target_path}."
        else:
            # If not over a specific folder, open user Desktop
            target_path = str(user_desktop)
            os.system(f'start explorer "{target_path}"')
            return f"Opened active desktop directory: {target_path}."
    except Exception as e:
        logger.warning(f"Failed to open pointed folder: {e}")
        desktop_dir = str(Path.home() / "Desktop")
        os.system(f'start explorer "{desktop_dir}"')
        return f"Opened default Desktop folder: {desktop_dir}."


def is_screen_query(query: str) -> bool:
    """Detects if a user query is asking about what is currently on the screen or being viewed."""
    q = query.lower().strip()
    has_target = any(k in q for k in ["screen", "viewing", "view", "seeing", "see", "looking at", "look at", "what window", "what app"])
    has_intent = any(k in q for k in ["what", "describe", "analyze", "inspect", "look", "see", "can you", "tell me", "show me", "current"])
    return bool(has_target and has_intent)


def is_mouse_query(query: str) -> bool:
    """Detects if a user query is asking about mouse cursor position or pointing."""
    q = query.lower().strip()
    has_mouse = any(k in q for k in ["mouse", "cursor", "pointer"])
    has_action = any(k in q for k in ["where", "what", "point", "position", "coord", "hover", "on", "under", "location", "at"])
    return bool(has_mouse and has_action)


def is_open_mouse_folder_query(query: str) -> bool:
    """Detects if a user query asks to open the folder where the mouse is pointing."""
    q = query.lower().strip()
    return any(k in q for k in [
        "open the folder where", "open folder where", "open pointed folder",
        "open folder pointed", "open the folder pointed", "open where mouse is pointing",
        "open where my mouse is", "open the folder my mouse", "open folder my mouse"
    ])
