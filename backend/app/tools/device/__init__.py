"""
Device Monitoring and Control System Package.
Exports all device monitoring tools, telemetry trackers, and control utilities.
"""

from app.tools.device.device_state import (
    load_device_settings,
    save_device_settings,
    is_device_monitoring_enabled,
    device_state_tracker
)
from app.tools.device.screen import (
    capture_screen_image,
    get_cursor_position,
    get_screen_dimensions,
    cleanup_temporary_screenshot
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
    CopySelectionTool,
    PasteTool,
    SwitchApplicationTool,
    CloseApplicationTool,
    AnalyzeScreenTool,
    SelectFileOnScreenTool,
    DragFileToAppTool,
    GetDeviceStatusTool,
    ToggleDeviceMonitoringTool
)

__all__ = [
    "load_device_settings",
    "save_device_settings",
    "is_device_monitoring_enabled",
    "device_state_tracker",
    "capture_screen_image",
    "get_cursor_position",
    "get_screen_dimensions",
    "cleanup_temporary_screenshot",
    "get_active_window_info",
    "get_open_windows_list",
    "switch_to_application",
    "set_window_state",
    "extract_ui_tree",
    "find_ui_element",
    "click_ui_element_by_name",
    "move_mouse_to",
    "click_at_coordinates",
    "drag_and_drop_coordinates",
    "scroll_mouse",
    "type_text_content",
    "press_single_key",
    "press_hotkey_combination",
    "copy_selection",
    "paste_clipboard",
    "select_file_on_screen",
    "drag_file_to_application_target",
    "analyze_current_screen",
    "build_structured_screen_state",
    "verify_action_result",
    "GetCurrentScreenTool",
    "GetActiveWindowTool",
    "GetOpenWindowsTool",
    "GetUITreeTool",
    "FindUIElementTool",
    "ClickUIElementTool",
    "ClickCoordinatesTool",
    "TypeTextTool",
    "PressKeyTool",
    "PressHotkeyTool",
    "DragAndDropTool",
    "CopySelectionTool",
    "PasteTool",
    "SwitchApplicationTool",
    "CloseApplicationTool",
    "AnalyzeScreenTool",
    "SelectFileOnScreenTool",
    "DragFileToAppTool",
    "GetDeviceStatusTool",
    "ToggleDeviceMonitoringTool"
]
