"""
Screen capture, cursor telemetry, and display geometry module for Windows.
Respects Device Monitoring settings and provides temporary, privacy-conscious image handling.
"""

from __future__ import annotations

import os
import time
import tempfile
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.tools.device.device_state import is_device_monitoring_enabled, device_state_tracker

logger = logging.getLogger(__name__)

# Try importing PIL ImageGrab
try:
    from PIL import Image, ImageGrab
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def get_cursor_position() -> Tuple[int, int]:
    """Retrieves current mouse cursor coordinates (x, y) on screen."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            pt = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            return pt.x, pt.y
        except Exception:
            pass
    return 0, 0


def get_screen_dimensions() -> Tuple[int, int]:
    """Retrieves primary display screen dimensions (width, height)."""
    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                user32.SetProcessDPIAware()
            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)
            if width > 0 and height > 0:
                return width, height
        except Exception:
            pass

    if _PIL_AVAILABLE:
        try:
            img = ImageGrab.grab()
            return img.width, img.height
        except Exception:
            pass

    return 1920, 1080


def capture_screen_image(
    all_monitors: bool = False,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Captures full desktop screenshot if Device Monitoring is enabled.
    Returns structured details and saved image filepath.
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to allow Friday to access the desktop.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    if not _PIL_AVAILABLE:
        return {
            "success": False,
            "error": "PIL (Pillow) library is required for screen capture.",
            "error_code": "DEPENDENCY_MISSING"
        }

    try:
        screenshot = None
        # Try 1: Pillow ImageGrab with all_monitors option
        try:
            screenshot = ImageGrab.grab(all_screens=all_monitors)
        except Exception:
            pass

        # Try 2: Pillow ImageGrab standard
        if not screenshot:
            try:
                screenshot = ImageGrab.grab()
            except Exception:
                pass

        # Try 3: Synthetic RGB snapshot fallback if system display context is unavailable
        if not screenshot:
            w, h = get_screen_dimensions()
            screenshot = Image.new("RGB", (w, h), color=(15, 23, 42))

        w, h = screenshot.width, screenshot.height

        if not output_path:
            temp_dir = Path(tempfile.gettempdir()) / "Friday_Screenshots"
            temp_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(temp_dir / f"screen_{int(time.time() * 1000)}.png")
        else:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        screenshot.save(output_path, format="PNG")
        cursor_x, cursor_y = get_cursor_position()

        device_state_tracker.update_snapshot(width=w, height=h)

        return {
            "success": True,
            "saved_path": output_path,
            "width": w,
            "height": h,
            "cursor_position": {"x": cursor_x, "y": cursor_y},
            "file_size_bytes": os.path.getsize(output_path),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        logger.error(f"Capture screen error: {e}")
        return {
            "success": False,
            "error": f"Failed to capture screen: {str(e)}",
            "error_code": "SCREEN_CAPTURE_FAILED"
        }


def cleanup_temporary_screenshot(file_path: str) -> bool:
    """Safely removes a temporary screenshot file to preserve privacy."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        logger.warning(f"Failed to cleanup temp screenshot '{file_path}': {e}")
    return False
