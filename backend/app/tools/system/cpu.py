"""
CPU Monitoring Tool for Friday AI PC Agent.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import psutil
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.schemas.system_schemas import CPUStatus


class CPUArgsSchema(BaseModel):
    include_top_processes: bool = Field(False, description="Whether to include top CPU-consuming processes")
    include_per_core: bool = Field(False, description="Whether to include per-core breakdown (default False)")
    top_n: int = Field(5, description="Number of top processes to return")


class CPUStatusTool(BaseTool):
    name = "get_cpu_status"
    description = "Get real-time overall CPU usage percentage, frequency, temperature, and core counts."
    permission_level = PermissionLevel.SAFE
    category = "system"
    args_schema = CPUArgsSchema

    async def execute(
        self,
        include_top_processes: bool = False,
        include_per_core: bool = False,
        top_n: int = 5,
        **kwargs: Any
    ) -> ToolResult:
        try:
            total_usage = psutil.cpu_percent(interval=0.1)
            per_core = psutil.cpu_percent(interval=0.1, percpu=True) if include_per_core else []
            freq = psutil.cpu_freq()
            phys_cores = psutil.cpu_count(logical=False) or 1
            logical_cores = psutil.cpu_count(logical=True) or 1

            # Temperature detection if available on hardware
            temp_val: Optional[float] = None
            try:
                temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
                if temps:
                    for name, entries in temps.items():
                        if "cpu" in name.lower() or "core" in name.lower():
                            if entries:
                                temp_val = entries[0].current
                                break
            except Exception:
                pass

            top_procs: List[Dict[str, Any]] = []
            if include_top_processes:
                procs = []
                for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        info = p.info
                        if info['cpu_percent'] is not None:
                            procs.append(info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                procs.sort(key=lambda x: x.get('cpu_percent', 0.0) or 0.0, reverse=True)
                top_procs = procs[:top_n]

            status = CPUStatus(
                total_usage_percent=total_usage,
                per_core_usage=per_core,
                frequency_mhz=freq.current if freq else None,
                min_frequency_mhz=freq.min if freq else None,
                max_frequency_mhz=freq.max if freq else None,
                physical_cores=phys_cores,
                logical_cores=logical_cores,
                temperature_celsius=temp_val,
                top_processes=top_procs
            )

            return ToolResult(
                tool_name=self.name,
                success=True,
                data=status.model_dump(),
                metadata={"summary": f"CPU Usage: {total_usage}% across {logical_cores} logical cores"}
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, error=f"Failed to read CPU status: {str(e)}")
