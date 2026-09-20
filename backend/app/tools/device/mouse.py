"""
Mouse Cursor Control, Click, Scroll, and Drag-and-Drop System for Windows Desktop.
Enforces Device Monitoring authorization and handles DPI coordinate scaling.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any, Dict, Optional, Tuple

from app.tools.device.device_state import is_device_monitoring_enabled

logger = logging.getLogger(__name__)

# Try importing pyautogui
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False


def _setup_dpi():
    if _PYAUTOGUI_AVAILABLE:
        try:
            pyautogui.FAILSAFE = False
        except Exception:
            pass
    if os.name == "nt":
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def move_mouse_to(x: int, y: int, duration: float = 0.15) -> Dict[str, Any]:
    """Moves mouse cursor to specified screen coordinates (x, y)."""
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to perform mouse actions.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    _setup_dpi()
    if _PYAUTOGUI_AVAILABLE:
        try:
            pyautogui.moveTo(x, y, duration=0.01)
            return {"success": True, "target": {"x": x, "y": y}}
        except Exception as e:
            logger.warning(f"PyAutoGUI moveTo fallback: {e}")

    # Win32 fallback
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.SetCursorPos(x, y)
            return {"success": True, "target": {"x": x, "y": y}}
        except Exception as e:
            return {"success": False, "error": f"SetCursorPos failed: {e}"}

    return {"success": True, "target": {"x": x, "y": y}}


def click_at_coordinates(
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
    interval: float = 0.1
) -> Dict[str, Any]:
    """
    Executes a mouse click (left, right, or double) at specified screen coordinates (x, y).
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to perform mouse actions.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    _setup_dpi()
    btn = button.lower().strip()
    if btn not in ("left", "right", "middle"):
        btn = "left"

    if _PYAUTOGUI_AVAILABLE:
        try:
            pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=btn)
            return {
                "success": True,
                "action": f"{btn}_click" if clicks == 1 else "double_click",
                "coordinates": {"x": x, "y": y}
            }
        except Exception as e:
            logger.warning(f"PyAutoGUI click fallback: {e}")

    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetCursorPos(x, y)
            time.sleep(0.02)

            if btn == "left":
                MOUSEEVENTF_LEFTDOWN = 0x0002
                MOUSEEVENTF_LEFTUP = 0x0004
                for _ in range(clicks):
                    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.01)
                    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    if clicks > 1:
                        time.sleep(interval)
            elif btn == "right":
                MOUSEEVENTF_RIGHTDOWN = 0x0008
                MOUSEEVENTF_RIGHTUP = 0x0010
                user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                time.sleep(0.01)
                user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

            return {
                "success": True,
                "action": f"{btn}_click",
                "coordinates": {"x": x, "y": y}
            }
        except Exception as e:
            return {"success": False, "error": f"Win32 mouse_event failed: {e}"}

    return {"success": True, "action": f"{btn}_click", "coordinates": {"x": x, "y": y}}



def drag_and_drop_coordinates(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: float = 0.5
) -> Dict[str, Any]:
    """
    Performs mouse drag-and-drop from (start_x, start_y) to (end_x, end_y).
    Includes smooth movement interpolation and click release.
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to perform drag and drop.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    _setup_dpi()
    if _PYAUTOGUI_AVAILABLE:
        try:
            pyautogui.moveTo(start_x, start_y, duration=0.1)
            time.sleep(0.1)
            pyautogui.dragTo(end_x, end_y, duration=duration, button="left")
            time.sleep(0.1)
            return {
                "success": True,
                "from": {"x": start_x, "y": start_y},
                "to": {"x": end_x, "y": end_y}
            }
        except Exception as e:
            logger.error(f"PyAutoGUI dragTo failed: {e}")

    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            MOUSEEVENTF_LEFTDOWN = 0x0002
            MOUSEEVENTF_LEFTUP = 0x0004

            user32.SetCursorPos(start_x, start_y)
            time.sleep(0.1)
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.1)

            steps = 20
            for i in range(1, steps + 1):
                cur_x = int(start_x + (end_x - start_x) * (i / steps))
                cur_y = int(start_y + (end_y - start_y) * (i / steps))
                user32.SetCursorPos(cur_x, cur_y)
                time.sleep(duration / steps)

            time.sleep(0.1)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

            return {
                "success": True,
                "from": {"x": start_x, "y": start_y},
                "to": {"x": end_x, "y": end_y}
            }
        except Exception as e:
            return {"success": False, "error": f"Win32 drag and drop failed: {e}"}

    return {"success": False, "error": "Drag and drop operation failed."}


def scroll_mouse(clicks: int = 3, direction: str = "down") -> Dict[str, Any]:
    """Scrolls mouse wheel up or down by specified click units."""
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to perform mouse scrolling.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    amount = clicks if direction.lower() == "up" else -clicks
    if _PYAUTOGUI_AVAILABLE:
        try:
            pyautogui.scroll(amount * 100)
            return {"success": True, "scrolled": amount}
        except Exception as e:
            return {"success": False, "error": f"Scroll failed: {e}"}

    return {"success": False, "error": "Scrolling operation requires PyAutoGUI."}
