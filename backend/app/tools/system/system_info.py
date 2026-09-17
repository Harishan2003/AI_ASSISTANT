"""
System Information & Overview Tool for Friday AI PC Agent.
"""
from __future__ import annotations

import datetime
import platform
import socket
import sys
from typing import Any, List
import psutil

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.schemas.system_schemas import SystemOverview


class SystemInfoTool(BaseTool):
    name = "get_system_info"
    description = "Get comprehensive Windows system overview: OS version, hostname, CPU model, RAM total, boot time, uptime, and available drives."
    permission_level = PermissionLevel.SAFE
    category = "system"

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            boot_time_ts = psutil.boot_time()
            boot_dt = datetime.datetime.fromtimestamp(boot_time_ts)
            uptime_seconds = datetime.datetime.now().timestamp() - boot_time_ts

            hours, remainder = divmod(int(uptime_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            days, hours = divmod(hours, 24)

            uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

            drives: List[str] = []
            try:
                for p in psutil.disk_partitions(all=False):
                    drives.append(p.mountpoint)
            except Exception:
                pass

            cpu_model = platform.processor() or "x86_64 Compatible Processor"
            ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)

            overview = SystemOverview(
                os_name=platform.system(),
                os_version=platform.version(),
                os_release=platform.release(),
                architecture=platform.architecture()[0],
                hostname=socket.gethostname(),
                cpu_model=cpu_model,
                physical_cores=psutil.cpu_count(logical=False) or 1,
                logical_cores=psutil.cpu_count(logical=True) or 1,
                total_ram_gb=ram_gb,
                boot_time=boot_dt.strftime("%Y-%m-%d %H:%M:%S"),
                uptime=uptime_str,
                python_version=sys.version.split()[0],
                drives=drives
            )

            return ToolResult(
                success=True,
                data=overview.model_dump(),
                metadata={"summary": f"Windows {overview.os_release} ({overview.architecture}) on {overview.hostname} | Uptime: {uptime_str} | RAM: {ram_gb} GB"}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to read system info: {str(e)}")
