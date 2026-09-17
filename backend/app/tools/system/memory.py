"""
Memory (RAM & Swap) Monitoring Tool for Friday AI PC Agent.
"""
from __future__ import annotations

from typing import Any, Dict, List
import psutil
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.schemas.system_schemas import MemoryStatus


class MemoryArgsSchema(BaseModel):
    include_top_processes: bool = Field(True, description="Whether to include top RAM-consuming processes")
    top_n: int = Field(5, description="Number of top processes to return")


class MemoryStatusTool(BaseTool):
    name = "get_memory_status"
    description = "Get real-time RAM and Swap/Pagefile statistics: total, used, available, percentage, and top memory-consuming processes."
    permission_level = PermissionLevel.SAFE
    category = "system"
    args_schema = MemoryArgsSchema

    async def execute(self, include_top_processes: bool = True, top_n: int = 5, **kwargs: Any) -> ToolResult:
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()

            total_gb = round(mem.total / (1024 ** 3), 2)
            used_gb = round(mem.used / (1024 ** 3), 2)
            available_gb = round(mem.available / (1024 ** 3), 2)
            free_gb = round(mem.free / (1024 ** 3), 2)
            pct = mem.percent

            swap_total_gb = round(swap.total / (1024 ** 3), 2) if swap else None
            swap_used_gb = round(swap.used / (1024 ** 3), 2) if swap else None
            swap_pct = swap.percent if swap else None

            top_procs: List[Dict[str, Any]] = []
            if include_top_processes:
                procs = []
                for p in psutil.process_iter(['pid', 'name', 'memory_percent', 'memory_info']):
                    try:
                        info = p.info
                        mem_info = info.get('memory_info')
                        rss_mb = round(mem_info.rss / (1024 * 1024), 1) if mem_info else 0.0
                        procs.append({
                            "pid": info['pid'],
                            "name": info['name'],
                            "memory_percent": round(info.get('memory_percent') or 0.0, 1),
                            "memory_mb": rss_mb
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                procs.sort(key=lambda x: x.get('memory_mb', 0.0), reverse=True)
                top_procs = procs[:top_n]

            status = MemoryStatus(
                total_gb=total_gb,
                used_gb=used_gb,
                available_gb=available_gb,
                free_gb=free_gb,
                percent=pct,
                swap_total_gb=swap_total_gb,
                swap_used_gb=swap_used_gb,
                swap_percent=swap_pct,
                top_processes=top_procs
            )

            return ToolResult(
                success=True,
                data=status.model_dump(),
                metadata={"summary": f"RAM: {used_gb} GB / {total_gb} GB ({pct}% used, {available_gb} GB available)"}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to read memory status: {str(e)}")
