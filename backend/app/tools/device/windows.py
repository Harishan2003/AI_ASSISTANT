"""
Windows Desktop Window Management and Application Context System.
Allows Friday to identify active/open windows, switch between applications,
and manipulate window state (minimize, maximize, close).
"""

from __future__ import annotations

import os
import sys
import logging
from typing import Any, Dict, List, Optional

from app.tools.device.device_state import is_device_monitoring_enabled, device_state_tracker

logger = logging.getLogger(__name__)


def get_active_window_info() -> Dict[str, Any]:
    """
    Retrieves detailed metadata about the currently focused active window.
    Returns: title, application process name, PID, HWND, bounding rectangle.
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to allow Friday to access desktop context.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    info: Dict[str, Any] = {
        "title": "Desktop / System",
        "application": "Explorer",
        "pid": None,
        "hwnd": None,
        "bounds": None,
        "window_under_cursor": None
    }

    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            def get_win_details(h):
                if not h:
                    return None
                l = user32.GetWindowTextLengthW(h)
                t = "Untitled Window"
                if l > 0:
                    b = ctypes.create_unicode_buffer(l + 1)
                    user32.GetWindowTextW(h, b, l + 1)
                    t = b.value or "Untitled Window"
                p = wintypes.DWORD()
                user32.GetWindowThreadProcessId(h, ctypes.byref(p))
                a = "Explorer"
                if p.value:
                    try:
                        import psutil
                        proc = psutil.Process(p.value)
                        a_name = proc.name()
                        if a_name.lower().endswith(".exe"):
                            a_name = a_name[:-4]
                        a = a_name
                    except Exception:
                        pass
                return {"hwnd": int(h), "title": t, "application": a, "pid": p.value}

            hwnd = user32.GetForegroundWindow()
            if hwnd:
                details = get_win_details(hwnd)
                if details:
                    info["hwnd"] = details["hwnd"]
                    info["title"] = details["title"]
                    info["pid"] = details["pid"]
                    info["application"] = details["application"]

                # Get Bounding Rectangle
                rect = wintypes.RECT()
                if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    info["bounds"] = {
                        "x": rect.left,
                        "y": rect.top,
                        "width": max(0, rect.right - rect.left),
                        "height": max(0, rect.bottom - rect.top)
                    }

            # Check window under mouse cursor via WindowFromPoint
            pt = wintypes.POINT()
            if user32.GetCursorPos(ctypes.byref(pt)):
                chwnd = user32.WindowFromPoint(pt)
                if chwnd and chwnd != hwnd:
                    # Get root ancestor window for child controls
                    root_h = user32.GetAncestor(chwnd, 2)  # GA_ROOT = 2
                    target_h = root_h if root_h else chwnd
                    cdetails = get_win_details(target_h)
                    if cdetails and cdetails.get("title") not in ("", "Desktop", "FolderView"):
                        info["window_under_cursor"] = cdetails
        except Exception as e:
            logger.error(f"Error fetching active window info: {e}")

    device_state_tracker.update_snapshot(
        active_app=info.get("application"),
        active_window=info.get("title")
    )

    return {
        "success": True,
        "active_window": info
    }


def get_open_windows_list() -> Dict[str, Any]:
    """
    Enumerates all visible, top-level application windows currently running on the desktop.
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to access open windows.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    windows: List[Dict[str, Any]] = []

    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            import psutil

            user32 = ctypes.windll.user32
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

            def enum_proc(hwnd, lparam):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value.strip()

                        # Exclude system utility layers without title
                        if title and title not in ("Program Manager", "Settings", "Default IME", "MSCTFIME UI"):
                            pid = wintypes.DWORD()
                            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                            app_name = "Unknown"
                            if pid.value:
                                try:
                                    proc = psutil.Process(pid.value)
                                    app_name = proc.name().replace(".exe", "")
                                except Exception:
                                    pass

                            rect = wintypes.RECT()
                            bounds = None
                            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                                w = rect.right - rect.left
                                h = rect.bottom - rect.top
                                if w > 50 and h > 50:
                                    bounds = {"x": rect.left, "y": rect.top, "width": w, "height": h}

                            if bounds:
                                windows.append({
                                    "hwnd": int(hwnd),
                                    "title": title,
                                    "application": app_name,
                                    "pid": pid.value,
                                    "bounds": bounds
                                })
                return True

            user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
        except Exception as e:
            logger.error(f"Error enumerating open windows: {e}")

    return {
        "success": True,
        "count": len(windows),
        "windows": windows
    }


def switch_to_application(name_or_title: str) -> Dict[str, Any]:
    """
    Locates and activates an open window matching the specified app name or window title.
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to allow application switching.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    target = name_or_title.lower().strip()
    if not target:
        return {"success": False, "error": "Application name or window title is required."}

    # First, list running windows
    win_res = get_open_windows_list()
    if not win_res.get("success"):
        return win_res

    windows = win_res.get("windows", [])
    matched_win = None

    # Exact or substring match on app name or title
    for win in windows:
        win_title = win["title"].lower()
        win_app = win["application"].lower()

        if target == win_app or target == win_title:
            matched_win = win
            break
        elif target in win_app or target in win_title:
            matched_win = win
            break

    if not matched_win:
        return {
            "success": False,
            "error": f"Could not find open application or window matching '{name_or_title}'.",
            "error_code": "WINDOW_NOT_FOUND",
            "available_windows": [w["title"] for w in windows[:10]]
        }

    hwnd = matched_win["hwnd"]
    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            SW_RESTORE = 9

            # Bring to front & restore if minimized
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)

            device_state_tracker.update_snapshot(
                active_app=matched_win["application"],
                active_window=matched_win["title"]
            )

            return {
                "success": True,
                "message": f"Successfully switched to '{matched_win['title']}' ({matched_win['application']}).",
                "active_window": matched_win
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to activate window '{matched_win['title']}': {str(e)}",
                "error_code": "ACTIVATION_FAILED"
            }

    return {"success": False, "error": "Window switching is supported on Windows OS."}


def set_window_state(name_or_title: str, state: str) -> Dict[str, Any]:
    """
    Changes window state: 'minimize', 'maximize', 'restore', or 'close'.
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to control desktop windows.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    state_cmd = state.lower().strip()
    win_res = get_open_windows_list()
    if not win_res.get("success"):
        return win_res

    target = name_or_title.lower().strip()
    matched_win = None
    for win in win_res.get("windows", []):
        if target in win["application"].lower() or target in win["title"].lower():
            matched_win = win
            break

    if not matched_win:
        return {
            "success": False,
            "error": f"Window or application '{name_or_title}' not found.",
            "error_code": "WINDOW_NOT_FOUND"
        }

    hwnd = matched_win["hwnd"]
    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.windll.user32

            if state_cmd == "minimize":
                user32.ShowWindow(hwnd, 6) # SW_MINIMIZE
            elif state_cmd == "maximize":
                user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
            elif state_cmd in ("restore", "normal"):
                user32.ShowWindow(hwnd, 9) # SW_RESTORE
            elif state_cmd == "close":
                WM_CLOSE = 0x0010
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            else:
                return {"success": False, "error": f"Invalid state action '{state}'. Use minimize, maximize, restore, or close."}

            return {
                "success": True,
                "message": f"Successfully applied '{state_cmd}' to window '{matched_win['title']}'.",
                "target_window": matched_win
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to modify window state: {e}"}

    return {"success": False, "error": "Supported on Windows OS."}
