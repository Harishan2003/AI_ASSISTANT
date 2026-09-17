"""
Clipboard management tools for Windows.
"""

import subprocess
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult


class GetClipboardInput(BaseModel):
    pass


class GetClipboardTool(BaseTool):
    name: str = "get_clipboard"
    description: str = "Reads and returns the current text content from the Windows clipboard."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = GetClipboardInput

    def run(self) -> ToolResult:
        try:
            try:
                import pyperclip
                text = pyperclip.paste()
            except ImportError:
                # Fallback to PowerShell Get-Clipboard
                proc = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-Command", "Get-Clipboard"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                text = proc.stdout.strip()

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"clipboard_text": text, "length": len(text)}
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Failed to read clipboard: {str(e)}",
                error_code="CLIPBOARD_READ_FAILED"
            )


class SetClipboardInput(BaseModel):
    text: str = Field(..., description="Text content to copy into the Windows clipboard")


class SetClipboardTool(BaseTool):
    name: str = "set_clipboard"
    description: str = "Writes text content into the Windows clipboard."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = SetClipboardInput

    def run(self, text: str) -> ToolResult:
        try:
            try:
                import pyperclip
                pyperclip.copy(text)
            except ImportError:
                # Fallback to PowerShell Set-Clipboard
                proc = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-Command", "$input | Set-Clipboard"],
                    input=text,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if proc.returncode != 0:
                    raise RuntimeError(proc.stderr)

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"message": "Successfully copied to clipboard", "length": len(text)}
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Failed to set clipboard: {str(e)}",
                error_code="CLIPBOARD_SET_FAILED"
            )


class ClearClipboardInput(BaseModel):
    pass


class ClearClipboardTool(BaseTool):
    name: str = "clear_clipboard"
    description: str = "Empties the Windows clipboard."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = ClearClipboardInput

    def run(self) -> ToolResult:
        try:
            try:
                import pyperclip
                pyperclip.copy("")
            except ImportError:
                subprocess.run(
                    ["powershell.exe", "-NoProfile", "-Command", "Set-Clipboard -Value $null"],
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"message": "Clipboard cleared successfully"}
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Failed to clear clipboard: {str(e)}",
                error_code="CLIPBOARD_CLEAR_FAILED"
            )
