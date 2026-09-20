"""
Windows UI Automation Inspector and Element Interaction Engine.
Extracts structured UI trees (accessible name, control type, coordinates, state)
and enables reliable target element location and interaction.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from app.tools.device.device_state import is_device_monitoring_enabled
from app.tools.device.windows import get_active_window_info

logger = logging.getLogger(__name__)

# Import uiautomation with safety flag
try:
    import uiautomation as auto
    _UIA_AVAILABLE = True
except ImportError:
    _UIA_AVAILABLE = False


def extract_ui_tree(
    max_depth: int = 5,
    max_elements: int = 60,
    target_hwnd: Optional[int] = None
) -> Dict[str, Any]:
    """
    Traverses Windows UI Automation tree for active window or specified HWND.
    Returns structured list of detectable UI elements (buttons, inputs, labels, lists).
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to access UI element tree.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    active_info = get_active_window_info()
    if not active_info.get("success"):
        return active_info

    active_win = active_info.get("active_window", {})
    hwnd = target_hwnd or active_win.get("hwnd")

    elements: List[Dict[str, Any]] = []

    if _UIA_AVAILABLE:
        try:
            import time
            t_start = time.time()
            auto.SetGlobalSearchTimeout(0.2)
            root_ctrl = None
            if hwnd:
                root_ctrl = auto.ControlFromHandle(hwnd)
            if not root_ctrl:
                root_ctrl = auto.GetForegroundControl()

            if root_ctrl:
                count = 0

                def _walk(ctrl, depth=0):
                    nonlocal count
                    if depth > min(max_depth, 4) or count >= max_elements or (time.time() - t_start > 0.4):
                        return

                    try:
                        name = (ctrl.Name or "").strip()
                        ctype = (ctrl.ControlTypeName or "").replace("Control", "").lower()
                        rect = ctrl.BoundingRectangle

                        # Only collect elements with bounding rects
                        if rect and (rect.right > rect.left) and (rect.bottom > rect.top):
                            x = rect.left
                            y = rect.top
                            w = rect.right - rect.left
                            h = rect.bottom - rect.top

                            center_x = x + w // 2
                            center_y = y + h // 2

                            is_clickable = ctype in ("button", "edit", "hyperlink", "menuitem", "listitem", "checkbox", "tabitem", "combobox")

                            # Add element if it has a name or is an interactive input control
                            if name or is_clickable:
                                elements.append({
                                    "id": count + 1,
                                    "type": ctype or "element",
                                    "text": name or f"[{ctype}]",
                                    "name": name,
                                    "control_type": ctype,
                                    "x": center_x,
                                    "y": center_y,
                                    "bounds": {"x": x, "y": y, "width": w, "height": h},
                                    "is_clickable": is_clickable,
                                    "automation_id": getattr(ctrl, "AutomationId", "") or ""
                                })
                                count += 1

                        for child in ctrl.GetChildren():
                            if count >= max_elements or (time.time() - t_start > 0.4):
                                break
                            _walk(child, depth + 1)
                    except Exception:
                        pass

                _walk(root_ctrl)
        except Exception as e:
            logger.error(f"UI Automation tree extraction error: {e}")

    return {
        "success": True,
        "active_window": active_win,
        "element_count": len(elements),
        "elements": elements
    }


def find_ui_element(
    name: str,
    control_type: Optional[str] = None,
    max_depth: int = 6
) -> Dict[str, Any]:
    """
    Searches visible UI tree for an element matching the given name/text and optional control_type.
    Returns the element's metadata and visual center coordinates (x, y).
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to search UI elements.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    tree_res = extract_ui_tree(max_depth=max_depth, max_elements=100)
    if not tree_res.get("success"):
        return tree_res

    target_name = name.lower().strip()
    target_type = control_type.lower().strip() if control_type else None

    elements = tree_res.get("elements", [])
    matched_element = None

    # Priority 1: Exact name & type match
    for el in elements:
        el_name = el["name"].lower()
        el_type = el["control_type"].lower()

        if target_name == el_name and (not target_type or target_type in el_type):
            matched_element = el
            break

    # Priority 2: Substring name match
    if not matched_element:
        for el in elements:
            el_name = el["name"].lower()
            el_type = el["control_type"].lower()

            if target_name in el_name and (not target_type or target_type in el_type):
                matched_element = el
                break

    # Priority 3: Regex boundary match
    if not matched_element:
        try:
            pattern = re.compile(re.escape(target_name), re.IGNORECASE)
            for el in elements:
                if pattern.search(el["name"]) and (not target_type or target_type in el["control_type"]):
                    matched_element = el
                    break
        except Exception:
            pass

    if matched_element:
        return {
            "success": True,
            "element": matched_element,
            "active_window": tree_res.get("active_window")
        }

    return {
        "success": False,
        "error": f"UI element '{name}'" + (f" (type: {control_type})" if control_type else "") + " was not found on screen.",
        "error_code": "ELEMENT_NOT_FOUND",
        "visible_elements_sample": [e["name"] for e in elements[:10] if e["name"]]
    }


def click_ui_element_by_name(name: str, control_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Locates a UI element by name/type and triggers a click action via UI Automation or coordinate fallback.
    """
    if not is_device_monitoring_enabled():
        return {
            "success": False,
            "error": "Device Monitoring is currently disabled. Enable it in Settings to allow UI interaction.",
            "error_code": "DEVICE_MONITORING_DISABLED"
        }

    find_res = find_ui_element(name=name, control_type=control_type)
    if not find_res.get("success"):
        return find_res

    element = find_res.get("element", {})
    x, y = element.get("x", 0), element.get("y", 0)

    # Trigger click using mouse tool
    from app.tools.device.mouse import click_at_coordinates
    click_res = click_at_coordinates(x=x, y=y)

    return {
        "success": click_res.get("success", False),
        "target_element": element,
        "clicked_coordinates": {"x": x, "y": y},
        "error": click_res.get("error")
    }
