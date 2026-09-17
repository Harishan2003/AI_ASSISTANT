"""
Battery Status Monitoring Tool for Friday AI PC Agent.
"""
from __future__ import annotations

from typing import Any
import psutil
from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.schemas.system_schemas import BatteryStatus


class BatteryStatusTool(BaseTool):
    name = "get_battery_status"
    description = "Get battery metrics: percentage, charging state, and remaining power time (for laptops and battery-backed PCs)."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    category: str = "system"

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            batt = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
            if not batt:
                status = BatteryStatus(
                    has_battery=False,
                    power_plugged=True,
                    status_text="Desktop / No Battery Installed (AC Power)"
                )
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    data=status.model_dump(),
                    metadata={"summary": "Desktop PC (No Battery / AC Power)"}
                )

            status_text = "Charging" if batt.power_plugged else "Discharging"
            secs_left = batt.secsleft if (batt.secsleft is not None and batt.secsleft > 0) else None

            status = BatteryStatus(
                has_battery=True,
                percent=round(batt.percent, 1),
                power_plugged=batt.power_plugged,
                secs_left=secs_left,
                status_text=status_text
            )

            mins_left = f", ~{round(secs_left / 60)} mins remaining" if secs_left else ""
            summary = f"Battery: {batt.percent}% ({status_text}{mins_left})"

            return ToolResult(
                tool_name=self.name,
                success=True,
                data=status.model_dump(),
                metadata={"summary": summary}
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Failed to read battery status: {str(e)}"
            )
