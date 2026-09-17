"""
Screen capture and display management tools for Windows.
"""

import os
import time
import tempfile
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult


class TakeScreenshotInput(BaseModel):
    output_path: Optional[str] = Field(default=None, description="Optional custom path to save the screenshot PNG file. If omitted, saves to temp folder.")
    all_monitors: bool = Field(default=False, description="Whether to capture all monitors or primary monitor only")


class TakeScreenshotTool(BaseTool):
    name: str = "take_screenshot"
    description: str = "Captures a screenshot of the current Windows desktop and saves it as an image file."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = TakeScreenshotInput

    def run(self, output_path: Optional[str] = None, all_monitors: bool = False) -> ToolResult:
        try:
            from PIL import ImageGrab

            screenshot = ImageGrab.grab(all_screens=all_monitors)

            if not output_path:
                temp_dir = tempfile.gettempdir()
                filename = f"screenshot_{int(time.time())}.png"
                output_path = os.path.join(temp_dir, filename)

            # Ensure parent dir exists
            parent = os.path.dirname(os.path.abspath(output_path))
            os.makedirs(parent, exist_ok=True)

            screenshot.save(output_path, format="PNG")

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "saved_path": output_path,
                    "width": screenshot.width,
                    "height": screenshot.height,
                    "mode": screenshot.mode,
                    "file_size_bytes": os.path.getsize(output_path)
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Failed to capture screenshot: {str(e)}",
                error_code="SCREENSHOT_FAILED"
            )


class GetDisplayInfoInput(BaseModel):
    pass


class GetDisplayInfoTool(BaseTool):
    name: str = "get_display_info"
    description: str = "Retrieves information about connected monitors and screen resolution."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = GetDisplayInfoInput

    def run(self) -> ToolResult:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)
            num_monitors = user32.GetSystemMetrics(80) # SM_CMONITORS

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "primary_resolution": f"{width}x{height}",
                    "width": width,
                    "height": height,
                    "monitor_count": num_monitors if num_monitors > 0 else 1
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Failed to retrieve display info: {str(e)}",
                error_code="DISPLAY_INFO_FAILED"
            )
