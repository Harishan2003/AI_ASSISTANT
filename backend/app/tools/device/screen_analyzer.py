"""
Screen Understanding & Natural Language Screen Analysis Engine.
Synthesizes screenshot, active window, visible UI tree, and application context
to answer "Friday, what am I seeing?" without hallucinating data.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any, Dict, List, Optional

from app.tools.device.device_state import is_device_monitoring_enabled, device_state_tracker
from app.tools.device.screen import capture_screen_image, get_screen_dimensions, get_cursor_position
from app.tools.device.windows import get_active_window_info, get_open_windows_list
from app.tools.device.ui_automation import extract_ui_tree

logger = logging.getLogger(__name__)


def build_structured_screen_state() -> Dict[str, Any]:
    """
    Builds structured screen state representation combining active window,
    display dimensions, visible UI elements, open applications, and cursor position.
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to allow Friday to access desktop state.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    width, height = get_screen_dimensions()
    cursor_x, cursor_y = get_cursor_position()

    active_res = get_active_window_info()
    active_win = active_res.get("active_window", {}) if active_res.get("success") else {}

    open_res = get_open_windows_list()
    open_wins = open_res.get("windows", []) if open_res.get("success") else []

    ui_res = extract_ui_tree(max_depth=4, max_elements=50)
    elements = ui_res.get("elements", []) if ui_res.get("success") else []

    state = {
        "device_monitoring_enabled": True,
        "screen": {
            "width": width,
            "height": height,
            "cursor_position": {"x": cursor_x, "y": cursor_y}
        },
        "active_window": {
            "title": active_win.get("title", "Unknown Window"),
            "application": active_win.get("application", "Unknown Application"),
            "pid": active_win.get("pid"),
            "bounds": active_win.get("bounds")
        },
        "open_applications": [
            {"title": w["title"], "application": w["application"]} for w in open_wins[:10]
        ],
        "visible_elements": elements[:30]
    }

    return {
        "success": True,
        "structured_state": state
    }


def analyze_current_screen(user_prompt: str = "") -> Dict[str, Any]:
    """
    Captures and analyzes the current desktop screen.
    Returns structured data and a natural-language description for "Friday, what am I seeing?".
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to allow Friday to inspect the desktop.",
            "error_code": "DEVICE_MONITORING_DISABLED",
            "natural_language_description": "Device Monitoring is currently disabled. Enable it in Settings to allow Friday to access the desktop."
        }

    # Capture screen
    cap_res = capture_screen_image()
    if not cap_res.get("success"):
        return {
            "success": False,
            "error": cap_res.get("error", "Screen capture failed"),
            "natural_language_description": "Sorry, I can't access the current screen."
        }

    state_res = build_structured_screen_state()
    if not state_res.get("success"):
        return {
            "success": False,
            "error": state_res.get("error"),
            "natural_language_description": "Sorry, I can't analyze the current screen state."
        }

    sdata = state_res.get("structured_state", {})
    active_win = sdata.get("active_window", {})
    app_name = active_win.get("application", "Desktop")
    win_title = active_win.get("title", "Desktop")
    elements = sdata.get("visible_elements", [])
    open_apps = sdata.get("open_applications", [])

    win_under_cursor = sdata.get("active_window", {}).get("window_under_cursor")

    # Synthesize concise, accurate natural language summary
    summary_parts = [
        f"You're currently focusing **{app_name}** ({win_title})."
    ]

    if win_under_cursor and win_under_cursor.get("application", "").lower() != app_name.lower():
        c_app = win_under_cursor.get("application")
        c_title = win_under_cursor.get("title")
        summary_parts.append(f"Your mouse cursor is currently positioned over **{c_app}** ({c_title}).")

    important_elements = [e for e in elements if e.get("name") and e["name"] not in (app_name, win_title)]
    if important_elements:
        names = [f"'{e['name']}'" for e in important_elements[:6]]
        summary_parts.append(f"I can see visible UI elements including: {', '.join(names)}.")

    other_apps = [a["application"] for a in open_apps if a["application"].lower() != app_name.lower()]
    if other_apps:
        unique_other = list(dict.fromkeys(other_apps))[:4]
        summary_parts.append(f"Other open applications on your desktop include: {', '.join(unique_other)}.")

    natural_desc = " ".join(summary_parts)

    device_state_tracker.update_snapshot(
        active_app=app_name,
        active_window=win_title,
        analysis_summary=natural_desc
    )

    return {
        "success": True,
        "screenshot_path": cap_res.get("saved_path"),
        "active_application": app_name,
        "active_window": win_title,
        "natural_language_description": natural_desc,
        "structured_state": sdata
    }


def verify_action_result(
    action_type: str,
    target_name: str,
    pre_window: Optional[str] = None
) -> Dict[str, Any]:
    """
    Inspects screen state after an action to verify whether the action succeeded.
    """
    time.sleep(0.3)
    post_info = get_active_window_info()
    post_win = post_info.get("active_window", {}) if post_info.get("success") else {}

    cur_title = post_win.get("title", "").lower()
    cur_app = post_win.get("application", "").lower()
    target_lower = target_name.lower()

    if action_type in ("switch_application", "open_application"):
        verified = target_lower in cur_app or target_lower in cur_title
        return {
            "verified": verified,
            "current_application": post_win.get("application"),
            "current_window": post_win.get("title")
        }

    return {"verified": True, "current_window": post_win.get("title")}
