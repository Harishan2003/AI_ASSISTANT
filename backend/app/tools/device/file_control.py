"""
File Desktop Selection, Drag-and-Drop, and File System Interaction.
Integrates existing filesystem tools with UI automation and drag-and-drop actions.
"""

from __future__ import annotations

import os
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.tools.device.device_state import is_device_monitoring_enabled
from app.tools.device.ui_automation import find_ui_element
from app.tools.device.mouse import drag_and_drop_coordinates, click_at_coordinates
from app.tools.device.windows import switch_to_application, get_active_window_info

logger = logging.getLogger(__name__)


def locate_file_on_system(filename: str, search_dir: Optional[str] = None) -> Optional[Path]:
    """Searches common user folders (Desktop, Downloads, Documents, Projects) for a given filename."""
    name_clean = filename.lower().strip()

    # If full path provided and exists
    if os.path.exists(filename):
        return Path(filename)

    base_dirs = []
    if search_dir and os.path.exists(search_dir):
        base_dirs.append(Path(search_dir))

    user_home = Path.home()
    common_folders = ["Desktop", "Downloads", "Documents", "Projects", "Pictures"]
    for folder in common_folders:
        p = user_home / folder
        if p.exists():
            base_dirs.append(p)

    for bdir in base_dirs:
        try:
            for item in bdir.iterdir():
                if item.is_file():
                    if item.name.lower() == name_clean or item.stem.lower() == name_clean:
                        return item
        except Exception:
            pass

    # Recursive fallback search in Desktop/Downloads
    for bdir in base_dirs[:2]:
        try:
            for item in bdir.glob(f"*{name_clean}*"):
                if item.is_file():
                    return item
        except Exception:
            pass

    return None


def select_file_on_screen(filename: str) -> Dict[str, Any]:
    """
    Attempts to locate and click/select a file visible on screen or in File Explorer.
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to allow file selection.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    # First, try finding visible UI element with the filename
    el_res = find_ui_element(name=filename)
    if el_res.get("success"):
        el = el_res.get("element", {})
        click_res = click_at_coordinates(x=el["x"], y=el["y"])
        return {
            "success": True,
            "selected_method": "on_screen_ui_element",
            "element": el,
            "file_name": filename
        }

    # Second, check local filesystem
    path_found = locate_file_on_system(filename)
    if path_found:
        return {
            "success": True,
            "selected_method": "filesystem_path",
            "file_name": path_found.name,
            "absolute_path": str(path_found.resolve()),
            "size_bytes": path_found.stat().st_size
        }

    return {
        "success": False,
        "error": f"Could not find file '{filename}' on screen or in common user directories.",
        "error_code": "FILE_NOT_FOUND"
    }


def drag_file_to_application_target(
    source_file_name: str,
    target_app_name: str,
    target_contact_or_ui: Optional[str] = None
) -> Dict[str, Any]:
    """
    Automates multi-step file drag-and-drop:
    1. Locates source file.
    2. Switches/activates target application (e.g. WhatsApp, Telegram, Explorer, Browser).
    3. Locates target recipient chat/element if specified.
    4. Performs drag-and-drop operation.
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to allow drag and drop file operations.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    # Step 1: Locate source file
    file_info = select_file_on_screen(source_file_name)
    if not file_info.get("success"):
        return file_info

    # Step 2: Switch to target application
    app_res = switch_to_application(target_app_name)
    if not app_res.get("success"):
        return app_res

    time.sleep(0.3)

    # Step 3: Find target UI element in application if specified
    target_x, target_y = None, None
    if target_contact_or_ui:
        ui_res = find_ui_element(name=target_contact_or_ui)
        if ui_res.get("success"):
            el = ui_res.get("element", {})
            target_x, target_y = el["x"], el["y"]

    # Fallback target: center of active application window
    if not target_x or not target_y:
        active_info = get_active_window_info()
        bounds = active_info.get("active_window", {}).get("bounds")
        if bounds:
            target_x = bounds["x"] + bounds["width"] // 2
            target_y = bounds["y"] + bounds["height"] // 2
        else:
            target_x, target_y = 960, 540

    # Step 4: Perform drag & drop from file UI element or default start position
    start_x = file_info.get("element", {}).get("x", 400)
    start_y = file_info.get("element", {}).get("y", 300)

    drag_res = drag_and_drop_coordinates(start_x, start_y, target_x, target_y)

    return {
        "success": drag_res.get("success", False),
        "source_file": file_info.get("file_name", source_file_name),
        "target_application": target_app_name,
        "target_recipient": target_contact_or_ui,
        "drag_coordinates": {"start": {"x": start_x, "y": start_y}, "end": {"x": target_x, "y": target_y}}
    }
