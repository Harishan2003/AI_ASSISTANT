"""
Windows native toast notification tools.
"""

import subprocess
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult


class ShowNotificationInput(BaseModel):
    title: str = Field(..., description="Title of the desktop notification")
    message: str = Field(..., description="Main body message of the notification")


class ShowNotificationTool(BaseTool):
    name: str = "show_notification"
    description: str = "Displays a native Windows toast notification on the desktop."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = ShowNotificationInput

    def run(self, title: str, message: str) -> ToolResult:
        try:
            # Escape single and double quotes for PowerShell
            safe_title = title.replace("'", "''").replace('"', '`"')
            safe_message = message.replace("'", "''").replace('"', '`"')

            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
            $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
            $textNodes = $xml.GetElementsByTagName("text")
            $textNodes.Item(0).AppendChild($xml.CreateTextNode("{safe_title}")) > $null
            $textNodes.Item(1).AppendChild($xml.CreateTextNode("{safe_message}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Friday AI Assistant")
            $notifier.Show($toast)
            """

            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "title": title,
                    "message": message,
                    "status": "Notification sent successfully"
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Failed to display notification: {str(e)}",
                error_code="NOTIFICATION_FAILED"
            )
