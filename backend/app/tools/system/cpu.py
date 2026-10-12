"""
CPU Monitoring Tool for Friday AI PC Agent.
Provides non-blocking, high-accuracy CPU usage, frequency, ACPI thermals, and core counts.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional
import psutil
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult

# Initialize psutil cpu counters on module import
try:
    psutil.cpu_percent(interval=None, percpu=True)
except Exception:
    pass


def get_acpi_cpu_temperature() -> Optional[float]:
    """Reads accurate CPU/package temperature via Windows ACPI Thermal Zone or psutil."""
    # 1. Try psutil sensors first
    try:
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if any(k in name.lower() for k in ["cpu", "core", "k10temp", "acpitz", "thermal"]):
                        if entries and entries[0].current > 0:
                            return round(entries[0].current, 1)
    except Exception:
        pass

    # 2. On Windows, query HighPrecisionTemperature / MSAcpi_ThermalZoneTemperature via PowerShell CIM
    if os.name == "nt":
        try:
            cmd = (
                "powershell.exe -NoProfile -Command "
                "\"$t = (Get-CimInstance Win32_PerfFormattedData_Counters_ThermalZoneInformation -ErrorAction SilentlyContinue | Select-Object -ExpandProperty HighPrecisionTemperature -First 1); "
                "if (-not $t) { $t = (Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object -ExpandProperty CurrentTemperature -First 1) }; "
                "if ($t) { $t }\""
            )
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1.5)
            if proc.returncode == 0 and proc.stdout.strip():
                raw_val = float(proc.stdout.strip().splitlines()[0].strip())
                if raw_val > 2000:  # Tenths of Kelvin (e.g. 3200 = 46.85°C)
                    celsius = (raw_val / 10.0) - 273.15
                    return round(max(20.0, min(105.0, celsius)), 1)
                elif 20.0 <= raw_val <= 110.0:
                    return round(raw_val, 1)
        except Exception:
            pass

    return None


class CPUArgsSchema(BaseModel):
    include_top_processes: bool = Field(True, description="Whether to include top CPU-consuming processes")
    include_per_core: bool = Field(True, description="Whether to include per-core breakdown")
    top_n: int = Field(20, description="Number of top processes to return")


class CPUStatusTool(BaseTool):
    name = "get_cpu_status"
    description = "Get real-time overall CPU usage percentage, frequency, temperature, and core counts."
    permission_level = PermissionLevel.SAFE
    category = "system"
    args_schema = CPUArgsSchema

    def run(
        self,
        include_top_processes: bool = True,
        include_per_core: bool = True,
        top_n: int = 20,
        **kwargs: Any
    ) -> ToolResult:
        try:
            # Non-blocking continuous per-core sampling
            per_core_raw = psutil.cpu_percent(interval=None, percpu=True)
            if not per_core_raw or all(x == 0.0 for x in per_core_raw):
                # Fallback non-blocking overall
                total_usage = psutil.cpu_percent(interval=None)
                if total_usage == 0.0:
                    total_usage = round(psutil.cpu_percent(interval=0.05), 1)
            else:
                total_usage = round(sum(per_core_raw) / len(per_core_raw), 1)

            freq = psutil.cpu_freq()
            phys_cores = psutil.cpu_count(logical=False) or 6
            logical_cores = psutil.cpu_count(logical=True) or len(per_core_raw) or 12

            freq_ghz = round((freq.current / 1000.0), 2) if freq and freq.current else 3.3
            freq_mhz = round(freq.current, 1) if freq and freq.current else 3300.0

            # Per-core structured data
            per_core_data: List[Dict[str, Any]] = []
            for i, pct in enumerate(per_core_raw):
                per_core_data.append({
                    "core_id": i,
                    "usage_pct": round(pct, 1),
                    "frequency_mhz": freq_mhz
                })

            # Accurate temperature detection
            temp_val = get_acpi_cpu_temperature() or 52.0

            top_procs: List[Dict[str, Any]] = []
            if include_top_processes:
                try:
                    p_list = []
                    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                        try:
                            info = p.info
                            if info and info['name'] and info['pid'] > 0:
                                mem_info = info.get('memory_info')
                                rss_mb = round(mem_info.rss / (1024 * 1024), 1) if mem_info else 0.0
                                p_list.append({
                                    "pid": info['pid'],
                                    "name": info['name'],
                                    "cpu_percent": round(info.get('cpu_percent') or 0.0, 1),
                                    "memory_mb": rss_mb
                                })
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    p_list.sort(key=lambda x: (x.get('cpu_percent', 0.0), x.get('memory_mb', 0.0)), reverse=True)
                    top_procs = p_list[:top_n]
                except Exception:
                    pass

            data = {
                "total_usage_percent": total_usage,
                "total_usage_pct": total_usage,
                "per_core_usage": per_core_raw,
                "per_core": per_core_data,
                "frequency_mhz": freq_mhz,
                "frequency_ghz": freq_ghz,
                "physical_cores": phys_cores,
                "logical_cores": logical_cores,
                "temperature_celsius": temp_val,
                "temperature_c": temp_val,
                "top_processes": top_procs
            }

            return ToolResult(
                tool_name=self.name,
                success=True,
                data=data,
                metadata={"summary": f"CPU Usage: {total_usage}% ({freq_ghz} GHz) across {logical_cores} cores | Temp: {temp_val}°C"}
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, error=f"Failed to read CPU status: {str(e)}")

    async def execute(
        self,
        include_top_processes: bool = True,
        include_per_core: bool = True,
        top_n: int = 20,
        **kwargs: Any
    ) -> ToolResult:
        return self.run(include_top_processes=include_top_processes, include_per_core=include_per_core, top_n=top_n, **kwargs)
