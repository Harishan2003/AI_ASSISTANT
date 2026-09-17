"""
Disk & Storage Monitoring Tool for Friday AI PC Agent.
"""
from __future__ import annotations

from typing import Any, List
import psutil
from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.schemas.system_schemas import DriveInfo, StorageStatus


class StorageStatusTool(BaseTool):
    name = "get_storage_status"
    description = "Get storage metrics across all mounted Windows drives (C:, D:, etc.): total capacity, used, free space, and percentages."
    permission_level = PermissionLevel.SAFE
    category = "system"

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            drives: List[DriveInfo] = []
            partitions = psutil.disk_partitions(all=False)

            for p in partitions:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    drives.append(DriveInfo(
                        device=p.device,
                        mountpoint=p.mountpoint,
                        fstype=p.fstype,
                        total_gb=round(usage.total / (1024 ** 3), 2),
                        used_gb=round(usage.used / (1024 ** 3), 2),
                        free_gb=round(usage.free / (1024 ** 3), 2),
                        percent=usage.percent
                    ))
                except (PermissionError, OSError):
                    continue

            status = StorageStatus(drives=drives)
            summary_parts = [f"{d.mountpoint} {d.free_gb} GB free ({d.percent}% used)" for d in drives]

            return ToolResult(
                success=True,
                data=status.model_dump(),
                metadata={"summary": " | ".join(summary_parts) if summary_parts else "No accessible drives."}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to read storage status: {str(e)}")
