"""
Keyboard Input, Typing, Hotkeys, and Clipboard Integration System.
Allows Friday to type text, dispatch key combinations, and manage selection copy/paste.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any, Dict, List, Optional

from app.tools.device.device_state import is_device_monitoring_enabled

logger = logging.getLogger(__name__)

# Try importing pyautogui & pyperclip
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False

try:
    import pyperclip
    _PYCLIPBOARD_AVAILABLE = True
except ImportError:
    _PYCLIPBOARD_AVAILABLE = False


def type_text_content(text: str, interval: float = 0.02) -> Dict[str, Any]:
    """
    Types text content into the active focused input field.
    Uses clipboard paste for unicode/special characters if PyAutoGUI write encounters issues.
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to allow typing text.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    if not text:
        return {"success": False, "error": "Text to type cannot be empty."}

    # If text contains non-ASCII, use clipboard paste for 100% accuracy
    is_ascii = all(ord(c) < 128 for c in text)

    if _PYCLIPBOARD_AVAILABLE and _PYAUTOGUI_AVAILABLE and (not is_ascii or len(text) > 40):
        try:
            old_clip = pyperclip.paste()
            pyperclip.copy(text)
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.05)
            return {"success": True, "typed_length": len(text), "method": "clipboard_paste"}
        except Exception as e:
            logger.warning(f"Clipboard typing fallback: {e}")

    if _PYAUTOGUI_AVAILABLE:
        try:
            pyautogui.write(text, interval=interval)
            return {"success": True, "typed_length": len(text), "method": "pyautogui_write"}
        except Exception as e:
            return {"success": False, "error": f"Typing failed: {e}"}

    return {"success": False, "error": "Keyboard typing requires PyAutoGUI or Pyperclip."}


def press_single_key(key_name: str, presses: int = 1) -> Dict[str, Any]:
    """Presses a single key (e.g. 'enter', 'tab', 'escape', 'backspace', 'down', 'up', 'f5')."""
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to press keys.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    k = key_name.lower().strip()
    if _PYAUTOGUI_AVAILABLE:
        try:
            pyautogui.press(k, presses=presses, interval=0.05)
            return {"success": True, "key": k, "presses": presses}
        except Exception as e:
            return {"success": False, "error": f"Failed to press key '{k}': {e}"}

    return {"success": False, "error": "PyAutoGUI is required for key presses."}


def press_hotkey_combination(keys: List[str]) -> Dict[str, Any]:
    """
    Executes a keyboard hotkey combination (e.g. ['ctrl', 'c'], ['alt', 'tab'], ['win', 'd']).
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to execute hotkeys.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    if not keys:
        return {"success": False, "error": "Keys list cannot be empty."}

    clean_keys = [k.lower().strip() for k in keys]

    if _PYAUTOGUI_AVAILABLE:
        try:
            pyautogui.hotkey(*clean_keys)
            return {"success": True, "hotkey": "+".join(clean_keys)}
        except Exception as e:
            return {"success": False, "error": f"Failed to execute hotkey {clean_keys}: {e}"}

    return {"success": False, "error": "PyAutoGUI is required for hotkeys."}


def copy_selection() -> Dict[str, Any]:
    """Triggers 'ctrl+c' to copy current active selection to Windows clipboard."""
    res = press_hotkey_combination(["ctrl", "c"])
    if res.get("success") and _PYCLIPBOARD_AVAILABLE:
        time.sleep(0.1)
        clip_val = pyperclip.paste()
        return {"success": True, "clipboard_content": clip_val[:200]}
    return res


def paste_clipboard() -> Dict[str, Any]:
    """Triggers 'ctrl+v' to paste Windows clipboard content into active focus."""
    return press_hotkey_combination(["ctrl", "v"])
