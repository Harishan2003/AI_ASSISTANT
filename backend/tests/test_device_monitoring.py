"""
Comprehensive Unit & Integration Test Suite for Friday AI Assistant's
Device Monitoring and Control System.
"""

import pytest
import os
import json
from pathlib import Path

from app.tools.device.device_state import (
    load_device_settings,
    save_device_settings,
    is_device_monitoring_enabled,
    device_state_tracker
)
from app.tools.device.screen import (
    capture_screen_image,
    get_cursor_position,
    get_screen_dimensions
)
from app.tools.device.windows import (
    get_active_window_info,
    get_open_windows_list,
    switch_to_application,
    set_window_state
)
from app.tools.device.ui_automation import (
    extract_ui_tree,
    find_ui_element,
    click_ui_element_by_name
)
from app.tools.device.mouse import (
    move_mouse_to,
    click_at_coordinates,
    drag_and_drop_coordinates,
    scroll_mouse
)
from app.tools.device.keyboard import (
    type_text_content,
    press_single_key,
    press_hotkey_combination,
    copy_selection,
    paste_clipboard
)
from app.tools.device.file_control import (
    select_file_on_screen,
    drag_file_to_application_target
)
from app.tools.device.screen_analyzer import (
    analyze_current_screen,
    build_structured_screen_state,
    verify_action_result
)
from app.tools.device.device_tools import (
    GetCurrentScreenTool,
    GetActiveWindowTool,
    GetOpenWindowsTool,
    GetUITreeTool,
    FindUIElementTool,
    ClickUIElementTool,
    ClickCoordinatesTool,
    TypeTextTool,
    PressKeyTool,
    PressHotkeyTool,
    DragAndDropTool,
    SwitchApplicationTool,
    CloseApplicationTool,
    AnalyzeScreenTool,
    SelectFileOnScreenTool,
    DragFileToAppTool,
    GetDeviceStatusTool,
    ToggleDeviceMonitoringTool
)
from app.core.tool_router import tool_router
from app.core.permission_manager import permission_manager
from app.schemas.agent_schemas import PermissionLevel


@pytest.fixture(autouse=True)
def reset_device_settings():
    """Ensure device monitoring is reset to safe initial state before and after each test."""
    save_device_settings({"device_monitoring_enabled": False})
    yield
    save_device_settings({"device_monitoring_enabled": False})


def test_device_monitoring_disabled_by_default():
    """Verify Device Monitoring defaults to OFF and prevents desktop access."""
    save_device_settings({"device_monitoring_enabled": False})
    assert is_device_monitoring_enabled() is False

    # 1. Screen capture blocked
    cap_res = capture_screen_image()
    assert cap_res["success"] is False
    assert "disabled" in cap_res["error"].lower()

    # 2. Active window info blocked
    win_res = get_active_window_info()
    assert win_res["success"] is False
    assert "disabled" in win_res["error"].lower()

    # 3. Open windows list blocked
    open_res = get_open_windows_list()
    assert open_res["success"] is False

    # 4. UI Tree blocked
    ui_res = extract_ui_tree()
    assert ui_res["success"] is False

    # 5. Screen analysis blocked
    analysis_res = analyze_current_screen()
    assert analysis_res["success"] is False
    assert "disabled" in analysis_res["natural_language_description"].lower()

    # 6. Mouse & Keyboard blocked
    move_res = move_mouse_to(100, 100)
    assert move_res["success"] is False

    click_res = click_at_coordinates(100, 100)
    assert click_res["success"] is False

    type_res = type_text_content("hello")
    assert type_res["success"] is False

    key_res = press_single_key("enter")
    assert key_res["success"] is False

    drag_res = drag_and_drop_coordinates(10, 10, 50, 50)
    assert drag_res["success"] is False


def test_device_monitoring_enabled_operations():
    """Verify that enabling Device Monitoring allows desktop inspection and interaction."""
    save_device_settings({"device_monitoring_enabled": True})
    assert is_device_monitoring_enabled() is True

    # 1. Screen dimensions and cursor position
    w, h = get_screen_dimensions()
    assert isinstance(w, int) and w > 0
    assert isinstance(h, int) and h > 0

    cx, cy = get_cursor_position()
    assert isinstance(cx, int)
    assert isinstance(cy, int)

    # 2. Screen capture when ON
    cap_res = capture_screen_image()
    assert cap_res["success"] is True
    assert "saved_path" in cap_res
    assert os.path.exists(cap_res["saved_path"])

    # 3. Active window context when ON
    win_res = get_active_window_info()
    assert win_res["success"] is True
    assert "active_window" in win_res

    # 4. Open windows list when ON
    open_res = get_open_windows_list()
    assert open_res["success"] is True
    assert "windows" in open_res
    assert isinstance(open_res["windows"], list)

    # 5. Screen analyzer ("What am I seeing?")
    analysis_res = analyze_current_screen()
    assert analysis_res["success"] is True
    assert len(analysis_res["natural_language_description"]) > 10
    assert "viewing" in analysis_res["natural_language_description"].lower() or "desktop" in analysis_res["natural_language_description"].lower()

    # 6. Mouse movement and click
    move_res = move_mouse_to(500, 500)
    assert move_res["success"] is True

    click_res = click_at_coordinates(500, 500)
    assert click_res["success"] is True

    # 7. Hotkey & Keyboard typing
    hotkey_res = press_hotkey_combination(["ctrl", "shift", "alt"])
    assert hotkey_res["success"] is True



def test_device_tools_registration_and_schemas():
    """Verify all 20 Device Monitoring tools are registered with ToolRouter."""
    expected_tools = [
        "get_current_screen", "get_active_window", "get_open_windows",
        "get_ui_tree", "find_ui_element", "click_ui_element",
        "click_coordinates", "type_text", "press_key", "press_hotkey",
        "drag_and_drop", "copy_selection", "paste", "switch_application",
        "close_application", "analyze_screen", "select_file_on_screen",
        "drag_file_to_app", "get_device_status", "toggle_device_monitoring"
    ]

    for tool_name in expected_tools:
        tool_inst = tool_router.get_tool(tool_name)
        assert tool_inst is not None, f"Tool '{tool_name}' should be registered."
        assert hasattr(tool_inst, "name")
        assert hasattr(tool_inst, "description")


def test_permission_levels_and_confirmations():
    """Verify safety and human-in-the-loop confirmation policies for device actions."""
    # 1. Inspect/Read tools are SAFE
    screen_tool = GetCurrentScreenTool()
    assert screen_tool.permission_level == PermissionLevel.SAFE

    active_win_tool = GetActiveWindowTool()
    assert active_win_tool.permission_level == PermissionLevel.SAFE

    # 2. Sensitive / destructive actions require CONFIRM
    close_app_tool = CloseApplicationTool()
    assert close_app_tool.permission_level == PermissionLevel.CONFIRM

    drag_file_tool = DragFileToAppTool()
    assert drag_file_tool.permission_level == PermissionLevel.CONFIRM

    # Test permission manager evaluation
    lvl, reason = permission_manager.evaluate_action_permission(
        tool_name="drag_file_to_app",
        declared_level=PermissionLevel.CONFIRM,
        arguments={"source_file": "report.pdf", "target_app": "WhatsApp"}
    )
    assert lvl == PermissionLevel.CONFIRM
    assert reason is not None


@pytest.mark.anyio
async def test_natural_language_command_executor_routing():
    """Verify command_executor routing for Device Monitoring queries."""
    from main import execute_in_backend

    # 1. Query when Device Monitoring is OFF
    save_device_settings({"device_monitoring_enabled": False})
    off_reply = await execute_in_backend("Friday, what am I seeing?", session_id="test_device")
    assert "device monitoring is currently disabled" in off_reply.lower()

    # 2. Enable via tool toggle
    toggle_tool = ToggleDeviceMonitoringTool()
    t_res = toggle_tool.run(enabled=True)
    assert t_res.success is True
    assert is_device_monitoring_enabled() is True

    # 3. Query when Device Monitoring is ON
    on_reply = await execute_in_backend("Friday, what am I seeing?", session_id="test_device")
    assert "viewing" in on_reply.lower() or "desktop" in on_reply.lower() or "currently" in on_reply.lower()


def test_file_selection_and_drag_drop_planning():
    """Verify file selection on disk/screen and drag-and-drop planning."""
    save_device_settings({"device_monitoring_enabled": True})

    # Create temporary dummy file for testing
    temp_dir = Path.home() / "Documents"
    temp_dir.mkdir(parents=True, exist_ok=True)
    test_file = temp_dir / "test_invoice_sample.pdf"
    test_file.write_text("Dummy Invoice Content", encoding="utf-8")

    try:
        # Select file
        sel_res = select_file_on_screen("test_invoice_sample.pdf")
        assert sel_res["success"] is True
        assert sel_res["file_name"] == "test_invoice_sample.pdf"

        # File drag targeting non-existent app gracefully fails or switch app
        drag_res = drag_file_to_application_target(
            source_file_name="test_invoice_sample.pdf",
            target_app_name="NonExistentDummyAppWindow"
        )
        assert drag_res["success"] is False
        assert drag_res["error_code"] == "WINDOW_NOT_FOUND"
    finally:
        if test_file.exists():
            test_file.unlink()
