"""
Current Time & Date Tool for Friday AI Assistant.
Returns real-time formatted local and world clocks and dates.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult


class TimeInput(BaseModel):
    timezone: str = Field(default="Asia/Kolkata", description="IANA Timezone name (e.g. 'Asia/Kolkata', 'UTC', 'America/New_York', 'Europe/London'). Defaults to user's local timezone.")


class CurrentTimeTool(BaseTool):
    name: str = "get_current_time"
    description: str = "Get the exact real-time current date, time, day of the week, and timezone information."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    category: str = "general"
    args_schema = TimeInput

    def run(self, timezone: str = "Asia/Kolkata", **kwargs: Any) -> ToolResult:
        if not timezone or "?" in timezone or "what" in timezone.lower():
            timezone = "Asia/Kolkata"

        try:
            now = datetime.now(ZoneInfo(timezone.strip()))
        except Exception:
            timezone = "Asia/Kolkata"
            now = datetime.now(ZoneInfo("Asia/Kolkata"))

        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %d %B %Y")
        iso_str = now.isoformat()

        return ToolResult(
            tool_name=self.name,
            success=True,
            data={
                "time": time_str,
                "date": date_str,
                "timezone": timezone,
                "iso": iso_str,
                "formatted": f"{time_str} on {date_str} ({timezone})"
            },
            metadata={"summary": f"{time_str} on {date_str} ({timezone})"}
        )


def get_current_time(timezone: str = "Asia/Kolkata") -> str:
    """Legacy helper."""
    tool = CurrentTimeTool()
    res = tool.run(timezone=timezone)
    if res.success and res.data:
        return str(res.data.get("formatted"))
    return datetime.now().strftime("%I:%M %p on %A, %d %B %Y")