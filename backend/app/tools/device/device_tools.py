"""
Friday AI Assistant - Device Monitoring and Control BaseTool Definitions.
Registers schemas, arguments, and permission levels with Friday's ToolRouter.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.tools.device.device_state import is_device_monitoring_enabled, load_device_settings, save_device_settings, device_state_tracker
from app.tools.device.screen import capture_screen_image
from app.tools.device.windows import get_active_window_info, get_open_windows_list, switch_to_application, set_window_state
from app.tools.device.ui_automation import extract_ui_tree, find_ui_element, click_ui_element_by_name
from app.tools.device.mouse import click_at_coordinates, move_mouse_to, drag_and_drop_coordinates, scroll_mouse
from app.tools.device.keyboard import type_text_content, press_single_key, press_hotkey_combination, copy_selection, paste_clipboard
from app.tools.device.file_control import select_file_on_screen, drag_file_to_application_target
from app.tools.device.screen_analyzer import analyze_current_screen, build_structured_screen_state


# --- INPUT SCHEMAS ---

class GetCurrentScreenInput(BaseModel):
    all_monitors: bool = Field(default=False, description="Capture all monitors or primary monitor only")

class GetActiveWindowInput(BaseModel):
    pass

class GetOpenWindowsInput(BaseModel):
    pass

class GetUITreeInput(BaseModel):
    max_depth: int = Field(default=5, description="Depth of UI automation tree search")

class FindUIElementInput(BaseModel):
    name: str = Field(description="Name or text of the UI element to locate")
    control_type: Optional[str] = Field(default=None, description="Optional control type e.g. button, edit, listitem")

class ClickUIElementInput(BaseModel):
    name: str = Field(description="Name or text of the visible UI button/element to click")
    control_type: Optional[str] = Field(default=None, description="Optional control type e.g. button, link")

class ClickCoordinatesInput(BaseModel):
    x: int = Field(description="X screen coordinate in pixels")
    y: int = Field(description="Y screen coordinate in pixels")
    button: str = Field(default="left", description="Mouse button: left, right, or double")

class TypeTextInput(BaseModel):
    text: str = Field(description="Text string to type into the focused input element")

class PressKeyInput(BaseModel):
    key: str = Field(description="Name of the key to press e.g. enter, tab, escape, backspace")

class PressHotkeyInput(BaseModel):
    keys: List[str] = Field(description="List of key combinations e.g. ['ctrl', 'c'], ['alt', 'tab'], ['win', 'd']")

class DragAndDropInput(BaseModel):
    start_x: int = Field(description="Start X coordinate")
    start_y: int = Field(description="Start Y coordinate")
    end_x: int = Field(description="Target end X coordinate")
    end_y: int = Field(description="Target end Y coordinate")

class CopySelectionInput(BaseModel):
    pass

class PasteInput(BaseModel):
    pass

class SwitchApplicationInput(BaseModel):
    name: str = Field(description="Application name or window title to switch to e.g. Chrome, WhatsApp, VS Code, File Explorer")

class CloseApplicationInput(BaseModel):
    name: str = Field(description="Application name or window title to close")

class AnalyzeScreenInput(BaseModel):
    prompt: Optional[str] = Field(default="", description="Optional user prompt or question regarding what is visible on screen")

class SelectFileInput(BaseModel):
    filename: str = Field(description="Name of the file to select on screen or in filesystem e.g. report.pdf")

class DragFileToAppInput(BaseModel):
    source_file: str = Field(description="Filename to drag e.g. report.pdf")
    target_app: str = Field(description="Target application name e.g. WhatsApp, Telegram, Explorer")
    target_recipient: Optional[str] = Field(default=None, description="Optional chat contact or recipient name e.g. John")

class GetDeviceStatusInput(BaseModel):
    pass

class ToggleDeviceMonitoringInput(BaseModel):
    enabled: bool = Field(description="True to enable Device Monitoring & Control, False to disable")


# --- TOOL IMPLEMENTATIONS ---

class GetCurrentScreenTool(BaseTool):
    name: str = "get_current_screen"
    description: str = "Captures a screenshot of the current Windows desktop screen when Device Monitoring is enabled."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = GetCurrentScreenInput

    def run(self, all_monitors: bool = False) -> ToolResult:
        res = capture_screen_image(all_monitors=all_monitors)
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res if res.get("success") else None, error=res.get("error"), error_code=res.get("error_code"))


class GetActiveWindowTool(BaseTool):
    name: str = "get_active_window"
    description: str = "Retrieves information about the currently active window and application on the desktop."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = GetActiveWindowInput

    def run(self) -> ToolResult:
        res = get_active_window_info()
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res.get("active_window"), error=res.get("error"), error_code=res.get("error_code"))


class GetOpenWindowsTool(BaseTool):
    name: str = "get_open_windows"
    description: str = "Lists all running and visible desktop windows and applications."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = GetOpenWindowsInput

    def run(self) -> ToolResult:
        res = get_open_windows_list()
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class GetUITreeTool(BaseTool):
    name: str = "get_ui_tree"
    description: str = "Extracts the visible Windows UI Automation tree of interactive elements, buttons, and text fields."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = GetUITreeInput

    def run(self, max_depth: int = 5) -> ToolResult:
        res = extract_ui_tree(max_depth=max_depth)
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class FindUIElementTool(BaseTool):
    name: str = "find_ui_element"
    description: str = "Locates a visible UI element or button on screen by name or control type."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = FindUIElementInput

    def run(self, name: str, control_type: Optional[str] = None) -> ToolResult:
        res = find_ui_element(name=name, control_type=control_type)
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class ClickUIElementTool(BaseTool):
    name: str = "click_ui_element"
    description: str = "Clicks a visible UI button or element on screen specified by name or text."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = ClickUIElementInput

    def run(self, name: str, control_type: Optional[str] = None) -> ToolResult:
        res = click_ui_element_by_name(name=name, control_type=control_type)
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class ClickCoordinatesTool(BaseTool):
    name: str = "click_coordinates"
    description: str = "Clicks at exact pixel coordinates (x, y) on the screen."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = ClickCoordinatesInput

    def run(self, x: int, y: int, button: str = "left") -> ToolResult:
        clicks = 2 if button.lower() == "double" else 1
        btn = "left" if button.lower() == "double" else button
        res = click_at_coordinates(x=x, y=y, button=btn, clicks=clicks)
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class TypeTextTool(BaseTool):
    name: str = "type_text"
    description: str = "Types text into the currently focused input box or application window."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = TypeTextInput

    def run(self, text: str) -> ToolResult:
        res = type_text_content(text=text)
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class PressKeyTool(BaseTool):
    name: str = "press_key"
    description: str = "Presses a single keyboard key (e.g. enter, tab, escape, backspace, down, up)."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = PressKeyInput

    def run(self, key: str) -> ToolResult:
        res = press_single_key(key_name=key)
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class PressHotkeyTool(BaseTool):
    name: str = "press_hotkey"
    description: str = "Executes key combination hotkeys (e.g. ['ctrl', 'c'], ['ctrl', 'v'], ['alt', 'tab'], ['win', 'd'])."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = PressHotkeyInput

    def run(self, keys: List[str]) -> ToolResult:
        res = press_hotkey_combination(keys=keys)
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class DragAndDropTool(BaseTool):
    name: str = "drag_and_drop"
    description: str = "Drags an item or file from starting screen coordinates to ending target coordinates."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = DragAndDropInput

    def run(self, start_x: int, start_y: int, end_x: int, end_y: int) -> ToolResult:
        res = drag_and_drop_coordinates(start_x=start_x, start_y=start_y, end_x=end_x, end_y=end_y)
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class CopySelectionTool(BaseTool):
    name: str = "copy_selection"
    description: str = "Copies current selection to clipboard (ctrl+c)."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = CopySelectionInput

    def run(self) -> ToolResult:
        res = copy_selection()
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class PasteTool(BaseTool):
    name: str = "paste"
    description: str = "Pastes clipboard content into active focused input (ctrl+v)."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = PasteInput

    def run(self) -> ToolResult:
        res = paste_clipboard()
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class SwitchApplicationTool(BaseTool):
    name: str = "switch_application"
    description: str = "Switches to or activates an open application or window by name (e.g. WhatsApp, Chrome, Notepad)."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = SwitchApplicationInput

    def run(self, name: str) -> ToolResult:
        res = switch_to_application(name_or_title=name)
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class CloseApplicationTool(BaseTool):
    name: str = "close_application"
    description: str = "Closes a running application window by name."
    permission_level: PermissionLevel = PermissionLevel.CONFIRM
    args_schema = CloseApplicationInput

    def run(self, name: str) -> ToolResult:
        res = set_window_state(name_or_title=name, state="close")
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class AnalyzeScreenTool(BaseTool):
    name: str = "analyze_screen"
    description: str = "Inspects the current screen, active window, and visible UI elements to describe what the user is seeing."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = AnalyzeScreenInput

    def run(self, prompt: Optional[str] = "") -> ToolResult:
        res = analyze_current_screen(user_prompt=prompt or "")
        return ToolResult(
            tool_name=self.name,
            success=res.get("success", False),
            data=res,
            error=res.get("error"),
            error_code=res.get("error_code")
        )


class SelectFileOnScreenTool(BaseTool):
    name: str = "select_file_on_screen"
    description: str = "Locates and selects a file on the desktop, screen, or File Explorer."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = SelectFileInput

    def run(self, filename: str) -> ToolResult:
        res = select_file_on_screen(filename=filename)
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class DragFileToAppTool(BaseTool):
    name: str = "drag_file_to_app"
    description: str = "Selects a file and drags it into a target application or recipient chat (e.g. drag report.pdf to WhatsApp)."
    permission_level: PermissionLevel = PermissionLevel.CONFIRM
    args_schema = DragFileToAppInput

    def run(self, source_file: str, target_app: str, target_recipient: Optional[str] = None) -> ToolResult:
        res = drag_file_to_application_target(source_file_name=source_file, target_app_name=target_app, target_contact_or_ui=target_recipient)
        return ToolResult(tool_name=self.name, success=res.get("success", False), data=res, error=res.get("error"), error_code=res.get("error_code"))


class GetDeviceStatusTool(BaseTool):
    name: str = "get_device_status"
    description: str = "Retrieves Device Monitoring status, settings, and desktop telemetry summary."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = GetDeviceStatusInput

    def run(self) -> ToolResult:
        settings = load_device_settings()
        summary = device_state_tracker.get_summary()
        return ToolResult(tool_name=self.name, success=True, data={"settings": settings, "summary": summary})


class ToggleDeviceMonitoringTool(BaseTool):
    name: str = "toggle_device_monitoring"
    description: str = "Enables or disables the Device Monitoring & Control system."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = ToggleDeviceMonitoringInput

    def run(self, enabled: bool) -> ToolResult:
        res = save_device_settings({"device_monitoring_enabled": enabled})
        return ToolResult(tool_name=self.name, success=True, data=res)
