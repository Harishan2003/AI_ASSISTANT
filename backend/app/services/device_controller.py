"""
Friday AI Assistant - Comprehensive Windows Device Controller Service.
Provides full autonomous control over the operating system, hardware devices,
peripherals, windows, audio, display, power, mouse, keyboard, and screen perception.
"""

from __future__ import annotations

import asyncio
import ctypes
from ctypes import wintypes
import datetime
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

logger = logging.getLogger(__name__)

# Virtual Key Codes for Windows Multimedia and System keys
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3


class DeviceController:
    """Unified controller for all Windows device hardware, peripherals, and OS actions."""

    def __init__(self):
        self.screenshots_dir = Path.home() / "Pictures" / "Screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # 1. AUDIO & VOLUME CONTROL
    # ============================================================

    def set_volume(self, level: int) -> str:
        """Sets master system volume to a specific percentage (0 to 100)."""
        level = max(0, min(100, int(level)))
        try:
            # Use PowerShell audio endpoint control
            ps_script = f"""
            $obj = New-Object -ComObject WScript.Shell
            # Calculate step to 0 first then up
            1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}
            1..{int(level / 2)} | ForEach-Object {{ $obj.SendKeys([char]175) }}
            """
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script], capture_output=True, timeout=5)
            return f"System volume set to {level}%."
        except Exception as e:
            logger.warning(f"PowerShell volume set failed: {e}")
            return f"Volume set to approx {level}%."

    def volume_up(self, step: int = 5) -> str:
        """Increases system volume."""
        times = max(1, min(25, int(step / 2)))
        try:
            user32 = ctypes.windll.user32
            for _ in range(times):
                user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                user32.keybd_event(VK_VOLUME_UP, 0, 2, 0) # 2 = KEYEVENTF_KEYUP
                time.sleep(0.02)
            return "Volume increased."
        except Exception as e:
            return f"Failed to increase volume: {e}"

    def volume_down(self, step: int = 5) -> str:
        """Decreases system volume."""
        times = max(1, min(25, int(step / 2)))
        try:
            user32 = ctypes.windll.user32
            for _ in range(times):
                user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
                time.sleep(0.02)
            return "Volume decreased."
        except Exception as e:
            return f"Failed to decrease volume: {e}"

    def mute(self) -> str:
        """Mutes or un-mutes system volume."""
        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
            user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
            return "Audio mute toggled."
        except Exception as e:
            return f"Failed to mute audio: {e}"

    def media_play_pause(self) -> str:
        """Toggles media play/pause across all active media players (Spotify, YouTube, VLC)."""
        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
            user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)
            return "Media playback toggled (Play/Pause)."
        except Exception as e:
            return f"Failed to toggle media playback: {e}"

    def media_next(self) -> str:
        """Skips to the next media track."""
        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 0, 0)
            user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 2, 0)
            return "Skipped to next media track."
        except Exception as e:
            return f"Failed to skip track: {e}"

    def media_prev(self) -> str:
        """Goes to the previous media track."""
        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 0, 0)
            user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 2, 0)
            return "Returned to previous media track."
        except Exception as e:
            return f"Failed to go to previous track: {e}"

    def media_stop(self) -> str:
        """Stops active media playback."""
        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(VK_MEDIA_STOP, 0, 0, 0)
            user32.keybd_event(VK_MEDIA_STOP, 0, 2, 0)
            return "Media playback stopped."
        except Exception as e:
            return f"Failed to stop media playback: {e}"

    # ============================================================
    # 2. DISPLAY & BRIGHTNESS CONTROL
    # ============================================================

    def set_brightness(self, percent: int) -> str:
        """Sets internal display brightness percentage (0-100)."""
        percent = max(0, min(100, int(percent)))
        try:
            ps_cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{percent})"
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True, timeout=5)
            return f"Display brightness set to {percent}%."
        except Exception as e:
            return f"Failed to adjust brightness: {e}"

    def brightness_up(self, step: int = 10) -> str:
        """Increases display brightness."""
        return self.set_brightness(min(100, self.get_brightness() + step))

    def brightness_down(self, step: int = 10) -> str:
        """Decreases display brightness."""
        return self.set_brightness(max(0, self.get_brightness() - step))

    def get_brightness(self) -> int:
        """Gets current display brightness percentage."""
        try:
            ps_cmd = "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"
            res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True, text=True, timeout=4)
            if res.stdout.strip().isdigit():
                return int(res.stdout.strip())
        except Exception:
            pass
        return 70

    # ============================================================
    # 3. POWER & SESSION MANAGEMENT
    # ============================================================

    def lock_screen(self) -> str:
        """Locks the Windows workstation."""
        try:
            ctypes.windll.user32.LockWorkStation()
            return "Workstation locked successfully."
        except Exception as e:
            return f"Failed to lock workstation: {e}"

    def sleep_pc(self) -> str:
        """Puts the computer to sleep."""
        try:
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)
            return "System entering sleep mode."
        except Exception as e:
            return f"Failed to sleep PC: {e}"

    def shutdown_pc(self, delay_seconds: int = 30) -> str:
        """Initiates a Windows shutdown."""
        try:
            subprocess.run(["shutdown", "/s", "/t", str(delay_seconds)], check=False)
            return f"System shutdown initiated (in {delay_seconds} seconds). Use 'cancel shutdown' to abort."
        except Exception as e:
            return f"Failed to initiate shutdown: {e}"

    def restart_pc(self, delay_seconds: int = 30) -> str:
        """Initiates a Windows restart."""
        try:
            subprocess.run(["shutdown", "/r", "/t", str(delay_seconds)], check=False)
            return f"System restart initiated (in {delay_seconds} seconds). Use 'cancel shutdown' to abort."
        except Exception as e:
            return f"Failed to initiate restart: {e}"

    def cancel_shutdown(self) -> str:
        """Aborts a pending shutdown or restart."""
        try:
            subprocess.run(["shutdown", "/a"], check=False)
            return "Pending shutdown or restart aborted."
        except Exception as e:
            return f"Failed to cancel shutdown: {e}"

    def set_power_profile(self, profile: str) -> str:
        """Switches Windows power scheme ('saver', 'balanced', 'performance')."""
        guid_map = {
            "saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
            "powersaver": "a1841308-3541-4fab-bc81-f71556f20b4a",
            "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
            "performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
            "high": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
        }
        guid = guid_map.get(profile.lower().strip(), "381b4222-f694-41f0-9685-ff5bb260df2e")
        try:
            subprocess.run(["powercfg", "/setactive", guid], capture_output=True, timeout=5)
            return f"Power scheme set to {profile.upper()}."
        except Exception as e:
            return f"Failed to set power scheme: {e}"

    # ============================================================
    # 4. WINDOW & WORKSPACE CONTROLS
    # ============================================================

    def minimize_all_windows(self) -> str:
        """Minimizes all windows to show the desktop (Win+D)."""
        if pyautogui:
            pyautogui.hotkey("win", "d")
            return "Minimized all open windows to show desktop."
        return "Cannot simulate keystroke."

    def show_task_view(self) -> str:
        """Opens Windows Task View and Virtual Desktops (Win+Tab)."""
        if pyautogui:
            pyautogui.hotkey("win", "tab")
            return "Opened Windows Task View."
        return "Cannot simulate keystroke."

    def open_settings(self) -> str:
        """Opens Windows Settings."""
        try:
            os.system("start ms-settings:")
            return "Opened Windows Settings."
        except Exception as e:
            return f"Failed to open Settings: {e}"

    def open_run_dialog(self) -> str:
        """Opens Windows Run dialog (Win+R)."""
        if pyautogui:
            pyautogui.hotkey("win", "r")
            return "Opened Run dialog."
        return "Cannot simulate keystroke."

    def switch_window(self) -> str:
        """Switches to the next application window (Alt+Tab)."""
        if pyautogui:
            pyautogui.hotkey("alt", "tab")
            return "Switched active application window."
        return "Cannot simulate keystroke."

    def close_active_window(self, user_message: str = "") -> str:
        """Closes the active application window via mouse click or Win32 WM_CLOSE / Alt+F4."""
        import os
        if os.name != "nt":
            if pyautogui:
                pyautogui.hotkey("alt", "f4")
                return "Closed active window."
            return "Cannot simulate keystroke."

        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32

            # 1. Determine target window: cursor window or foreground window
            target_hwnd = None
            pt = wintypes.POINT()
            if user32.GetCursorPos(ctypes.byref(pt)):
                h_under = user32.WindowFromPoint(pt)
                if h_under:
                    root_h = user32.GetAncestor(h_under, 2)  # GA_ROOT
                    target_hwnd = root_h if root_h else h_under

            if not target_hwnd:
                target_hwnd = user32.GetForegroundWindow()

            title = ""
            if target_hwnd:
                l = user32.GetWindowTextLengthW(target_hwnd)
                if l > 0:
                    b = ctypes.create_unicode_buffer(l + 1)
                    user32.GetWindowTextW(target_hwnd, b, l + 1)
                    title = b.value.strip()

            msg_lower = str(user_message or "").lower()
            use_mouse = "mouse" in msg_lower or "click" in msg_lower

            if target_hwnd:
                class RECT(ctypes.Structure):
                    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
                rect = RECT()
                user32.GetWindowRect(target_hwnd, ctypes.byref(rect))

                # Bring target window to foreground
                user32.SetForegroundWindow(target_hwnd)

                if use_mouse and pyautogui:
                    # Close button 'X' is in top right corner of the window
                    close_x = rect.right - 22
                    close_y = rect.top + 15
                    if close_x > 0 and close_y > 0:
                        pyautogui.moveTo(close_x, close_y, duration=0.15)
                        pyautogui.click(close_x, close_y)

                # Send standard Windows WM_CLOSE (0x0010) message
                WM_CLOSE = 0x0010
                user32.PostMessageW(target_hwnd, WM_CLOSE, 0, 0)

                app_label = f" '{title}'" if title and title not in ("Desktop", "Program Manager") else ""
                method_label = " using mouse automation" if use_mouse else ""
                return f"Closed active application{app_label}{method_label}."
        except Exception as e:
            logger.warning(f"Window close error: {e}")

        # Fallback Alt+F4
        if pyautogui:
            pyautogui.hotkey("alt", "f4")
            return "Closed active window."
        return "Cannot simulate keystroke."

    def switch_to_application(self, name: str) -> str:
        """Finds and brings an application window to foreground by name or process."""
        from app.tools.device.windows import switch_to_application as win_switch
        res = win_switch(name)
        if res.get("success"):
            return f"Switched to {res.get('application', name)}."
        return f"Could not switch to application {name}: {res.get('error', 'Window not found')}"

    def get_active_window_info(self) -> Dict[str, Any]:
        """Gets detailed info about the currently focused active window."""
        from app.tools.device.windows import get_active_window_info as win_info
        return win_info()

    def get_open_windows(self) -> List[Dict[str, Any]]:
        """Lists all open application windows currently visible on desktop."""
        from app.tools.device.windows import get_open_windows_list
        res = get_open_windows_list()
        return res.get("windows", []) if res.get("success") else []

    # ============================================================
    # 5. KEYBOARD & MOUSE AUTOMATION
    # ============================================================

    def type_text(self, text: str) -> str:
        """Types text directly into the focused element, with clipboard fallback for unicode."""
        if not pyautogui:
            return "PyAutoGUI is not available."

        try:
            # Check if text contains complex characters or multiline
            if "\n" in text or any(ord(c) > 127 for c in text):
                if pyperclip:
                    old_cb = pyperclip.paste()
                    pyperclip.copy(text)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.05)
                    pyperclip.copy(old_cb)
                    return f"Typed {len(text)} characters into active focus."
            
            pyautogui.write(text, interval=0.01)
            return f"Typed: '{text}'"
        except Exception as e:
            return f"Failed to type text: {e}"

    def press_key(self, key: str) -> str:
        """Presses a single key (e.g. enter, tab, escape, backspace, space, up, down)."""
        if not pyautogui:
            return "PyAutoGUI is not available."
        try:
            clean_key = key.lower().strip()
            pyautogui.press(clean_key)
            return f"Pressed '{clean_key}' key."
        except Exception as e:
            return f"Failed to press key '{key}': {e}"

    def press_hotkey(self, *keys: str) -> str:
        """Presses a key combination (e.g. ('ctrl', 'c'), ('ctrl', 'v'), ('alt', 'f4'))."""
        if not pyautogui:
            return "PyAutoGUI is not available."
        try:
            clean_keys = [str(k).lower().strip() for k in keys if k]
            pyautogui.hotkey(*clean_keys)
            return f"Pressed hotkey: {'+'.join(clean_keys)}"
        except Exception as e:
            return f"Failed to press hotkey: {e}"

    def click_at(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left", double: bool = False) -> str:
        """Clicks at specific screen coordinates or current cursor position."""
        if not pyautogui:
            return "PyAutoGUI is not available."
        try:
            if x is not None and y is not None:
                if double:
                    pyautogui.doubleClick(x=x, y=y, button=button)
                    return f"Double-clicked at ({x}, {y}) with {button} button."
                else:
                    pyautogui.click(x=x, y=y, button=button)
                    return f"Clicked at ({x}, {y}) with {button} button."
            else:
                if double:
                    pyautogui.doubleClick(button=button)
                    return f"Double-clicked at current position with {button} button."
                else:
                    pyautogui.click(button=button)
                    return f"Clicked at current position with {button} button."
        except Exception as e:
            return f"Failed to click: {e}"

    def move_mouse(self, x: int, y: int) -> str:
        """Moves cursor to screen coordinate (x, y)."""
        if not pyautogui:
            return "PyAutoGUI is not available."
        try:
            pyautogui.moveTo(x=x, y=y, duration=0.2)
            return f"Moved cursor to ({x}, {y})."
        except Exception as e:
            return f"Failed to move cursor: {e}"

    def drag_and_drop(self, start_x: int, start_y: int, end_x: int, end_y: int) -> str:
        """Drags from (start_x, start_y) and drops at (end_x, end_y)."""
        if not pyautogui:
            return "PyAutoGUI is not available."
        try:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=0.5, button="left")
            return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})."
        except Exception as e:
            return f"Failed to drag and drop: {e}"

    def scroll_mouse(self, clicks: int = 3, direction: str = "down") -> str:
        """Scrolls mouse wheel up or down."""
        if not pyautogui:
            return "PyAutoGUI is not available."
        try:
            amount = -abs(clicks) if direction.lower() == "down" else abs(clicks)
            pyautogui.scroll(amount * 100)
            return f"Scrolled mouse {direction} by {clicks} units."
        except Exception as e:
            return f"Failed to scroll mouse: {e}"

    # ============================================================
    # 6. CLIPBOARD MANAGEMENT
    # ============================================================

    def get_clipboard(self) -> str:
        """Gets current text on clipboard."""
        if pyperclip:
            return pyperclip.paste()
        return ""

    def set_clipboard(self, text: str) -> str:
        """Sets clipboard contents."""
        if pyperclip:
            pyperclip.copy(text)
            return f"Copied text to clipboard ({len(text)} chars)."
        return "Clipboard library unavailable."

    def clear_clipboard(self) -> str:
        """Clears clipboard contents."""
        if pyperclip:
            pyperclip.copy("")
            return "Clipboard cleared."
        return "Clipboard library unavailable."

    # ============================================================
    # 7. SCREEN PERCEPTION & VISUAL INSPECTION
    # ============================================================

    def capture_screen(self, save_path: Optional[str] = None) -> Dict[str, Any]:
        """Captures a screenshot of the desktop."""
        if not pyautogui:
            return {"success": False, "error": "PyAutoGUI not installed"}
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            target = Path(save_path) if save_path else (self.screenshots_dir / f"Screenshot_{timestamp}.png")
            img = pyautogui.screenshot()
            img.save(str(target))
            return {
                "success": True,
                "path": str(target),
                "width": img.width,
                "height": img.height,
                "timestamp": timestamp
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def inspect_screen_with_ai(self, prompt: str = "What is currently visible on my screen?") -> str:
        """Takes a screenshot and sends it to the vision AI model to analyze and answer queries."""
        try:
            from app.services.vision_service import is_mouse_query, get_mouse_pointer_context, capture_and_describe_screen

            if is_mouse_query(prompt):
                return get_mouse_pointer_context()

            cap = self.capture_screen()
            if cap.get("success"):
                try:
                    from app.services.qwen_vision_service import qwen_vision_service
                    res = await qwen_vision_service.analyze_image(cap["path"], prompt)
                    if res.get("analysis"):
                        return res["analysis"]
                except Exception:
                    pass

            # Fast robust native fallback
            return capture_and_describe_screen()
        except Exception as e:
            return f"Screen inspection: {e}"


# Global Singleton Instance
device_controller = DeviceController()
