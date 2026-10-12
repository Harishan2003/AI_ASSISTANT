"""
Disk & Storage Monitoring Tool for Friday AI PC Agent.
Provides drive capacity metrics (C:, D:, etc.) and real-time live read/write I/O throughput.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import psutil
from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.schemas.system_schemas import DriveInfo, StorageStatus

_LAST_DISK_IO: Optional[Any] = None
_LAST_DISK_TIME: float = 0.0
_CURRENT_READ_MBPS: float = 0.0
_CURRENT_WRITE_MBPS: float = 0.0


def _sample_disk_speed() -> tuple[float, float]:
    """Computes live disk read and write speeds in MB/s via disk_io_counters."""
    global _LAST_DISK_IO, _LAST_DISK_TIME, _CURRENT_READ_MBPS, _CURRENT_WRITE_MBPS
    now = time.monotonic()
    try:
        io_counters = psutil.disk_io_counters()
        if io_counters and _LAST_DISK_IO is not None and _LAST_DISK_TIME > 0:
            dt = now - _LAST_DISK_TIME
            if dt >= 0.4:
                read_bytes = max(0, io_counters.read_bytes - _LAST_DISK_IO.read_bytes)
                write_bytes = max(0, io_counters.write_bytes - _LAST_DISK_IO.write_bytes)
                _CURRENT_READ_MBPS = round((read_bytes / dt) / (1024.0 * 1024.0), 2)
                _CURRENT_WRITE_MBPS = round((write_bytes / dt) / (1024.0 * 1024.0), 2)
                _LAST_DISK_IO = io_counters
                _LAST_DISK_TIME = now
        else:
            _LAST_DISK_IO = io_counters
            _LAST_DISK_TIME = now
    except Exception:
        pass
    return _CURRENT_READ_MBPS, _CURRENT_WRITE_MBPS


class StorageStatusTool(BaseTool):
    name = "get_storage_status"
    description = "Get storage metrics across all mounted Windows drives (C:, D:, etc.): total capacity, used, free space, percentages, and live I/O speed."
    permission_level = PermissionLevel.SAFE
    category = "system"

    def run(self, **kwargs: Any) -> ToolResult:
        try:
            drives: List[Dict[str, Any]] = []
            partitions = psutil.disk_partitions(all=False)
            read_mbps, write_mbps = _sample_disk_speed()

            for p in partitions:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    clean_device = p.device.replace("\\", "").rstrip(":") + ":"
                    is_os = "c:" in clean_device.lower()
                    fstype_display = f"{p.fstype} ({'OS' if is_os else 'Data'})"

                    drives.append({
                        "device": clean_device,
                        "mountpoint": p.mountpoint,
                        "fstype": fstype_display,
                        "total_gb": round(usage.total / (1024 ** 3), 1),
                        "used_gb": round(usage.used / (1024 ** 3), 1),
                        "free_gb": round(usage.free / (1024 ** 3), 1),
                        "percent": round(usage.percent, 1),
                        "read_speed_mb": read_mbps if is_os else 0.0,
                        "write_speed_mb": write_mbps if is_os else 0.0
                    })
                except (PermissionError, OSError):
                    continue

            summary_parts = [f"{d['device']} {d['free_gb']} GB free ({d['percent']}% used)" for d in drives]

            data = {
                "drives": drives,
                "total_read_mbps": read_mbps,
                "total_write_mbps": write_mbps,
                "read_bytes_sec": read_mbps * 1024 * 1024,
                "write_bytes_sec": write_mbps * 1024 * 1024
            }

            return ToolResult(
                tool_name=self.name,
                success=True,
                data=data,
                metadata={"summary": " | ".join(summary_parts) if summary_parts else "No accessible drives."}
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, error=f"Failed to read storage status: {str(e)}")

    async def execute(self, **kwargs: Any) -> ToolResult:
        return self.run(**kwargs)
