"""
Device Monitoring and Control System State & Settings Manager.
Manages persistent configuration (device_monitoring_enabled flag) and
ephemeral runtime desktop telemetry state for Friday AI Assistant.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Base project paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATABASE_DIR = ROOT_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
DEVICE_SETTINGS_FILE = DATABASE_DIR / "device_settings.json"

DEFAULT_DEVICE_SETTINGS: Dict[str, Any] = {
    "device_monitoring_enabled": False,
    "ocr_enabled": True,
    "action_delay_ms": 100,
    "verification_enabled": True,
    "privacy_blur_sensitive": True
}


def load_device_settings() -> Dict[str, Any]:
    """Loads device monitoring settings from database/device_settings.json."""
    if DEVICE_SETTINGS_FILE.exists():
        try:
            with open(DEVICE_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_DEVICE_SETTINGS, **data}
        except Exception as e:
            logger.error(f"Error loading device_settings.json: {e}")
    return DEFAULT_DEVICE_SETTINGS.copy()


def save_device_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Persists updated device monitoring settings to database/device_settings.json."""
    current = load_device_settings()
    current.update(settings)
    try:
        with open(DEVICE_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        logger.info("[DeviceState] Device monitoring settings saved.")
    except Exception as e:
        logger.error(f"Error writing device_settings.json: {e}")
    return current


def is_device_monitoring_enabled() -> bool:
    """Returns True if Device Monitoring feature is enabled by the user."""
    return load_device_settings().get("device_monitoring_enabled", False)


class DeviceStateTracker:
    """
    In-memory temporary snapshot tracker for active desktop telemetry.
    Does not persist screenshots or sensitive data permanently.
    """

    def __init__(self):
        self.last_active_app: str = "Unknown"
        self.last_active_window: str = "Unknown"
        self.screen_width: int = 1920
        self.screen_height: int = 1080
        self.last_analysis_time: float = 0.0
        self.last_analysis_summary: str = ""
        self.selected_element: Optional[Dict[str, Any]] = None

    def update_snapshot(
        self,
        active_app: Optional[str] = None,
        active_window: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        analysis_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """Updates the transient desktop state snapshot."""
        if active_app is not None:
            self.last_active_app = active_app
        if active_window is not None:
            self.last_active_window = active_window
        if width is not None:
            self.screen_width = width
        if height is not None:
            self.screen_height = height
        if analysis_summary is not None:
            self.last_analysis_summary = analysis_summary
            self.last_analysis_time = time.time()

        return self.get_summary()

    def get_summary(self) -> Dict[str, Any]:
        """Returns structured representation of current temporary device state."""
        return {
            "device_monitoring_enabled": is_device_monitoring_enabled(),
            "active_application": self.last_active_app,
            "active_window": self.last_active_window,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "last_screen_analysis": self.last_analysis_summary,
            "last_analysis_age_seconds": round(time.time() - self.last_analysis_time, 1) if self.last_analysis_time > 0 else None,
            "selected_element": self.selected_element
        }


device_state_tracker = DeviceStateTracker()
