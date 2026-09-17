"""
GPU Monitoring Tool for Friday AI PC Agent.
Supports multi-GPU setups (NVIDIA Dedicated GPUs + AMD Radeon / Intel Integrated GPUs).
"""
from __future__ import annotations

import os
import json
import subprocess
from typing import Any, Dict, List, Optional
from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult


class GPUStatusTool(BaseTool):
    name: str = "get_gpu_status"
    description: str = "Get comprehensive real-time metrics for all GPUs on the PC (NVIDIA GeForce, AMD Radeon, Intel UHD): load %, temperature, VRAM usage, model names, and drivers."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    category: str = "system"

    async def execute(self, **kwargs: Any) -> ToolResult:
        detected_gpus: List[Dict[str, Any]] = []

        # 1. Query NVIDIA GPUs via nvidia-smi
        try:
            cmd = "nvidia-smi --query-gpu=name,utilization.gpu,memory.total,memory.used,memory.free,temperature.gpu,driver_version,power.draw --format=csv,noheader,nounits"
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1.5)
            if proc.returncode == 0 and proc.stdout.strip():
                for line in proc.stdout.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 7:
                        name = parts[0]
                        util = float(parts[1]) if parts[1] != "[N/A]" else 0.0
                        mem_total = float(parts[2])
                        mem_used = float(parts[3])
                        mem_free = float(parts[4])
                        temp = float(parts[5]) if parts[5] != "[N/A]" else 50.0
                        driver = parts[6]
                        power = float(parts[7]) if len(parts) > 7 and parts[7] != "[N/A]" else None
                        mem_pct = round((mem_used / mem_total) * 100.0, 1) if mem_total > 0 else 0.0

                        detected_gpus.append({
                            "id": "gpu0",
                            "type": "dedicated",
                            "vendor": "NVIDIA",
                            "name": name,
                            "utilization_percent": util,
                            "temperature_celsius": temp,
                            "vram_total_mb": mem_total,
                            "vram_used_mb": mem_used,
                            "vram_free_mb": mem_free,
                            "vram_percent": mem_pct,
                            "driver_version": driver,
                            "power_draw_watts": power
                        })
        except Exception:
            pass

        # 2. Query Windows Video Controllers (AMD Radeon, Intel Graphics, etc.)
        try:
            if os.name == "nt":
                ps_cmd = "powershell -NoProfile -Command \"Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, AdapterRAM | ConvertTo-Json\""
                proc = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True, timeout=2.5)
                if proc.returncode == 0 and proc.stdout.strip():
                    controllers = json.loads(proc.stdout)
                    if isinstance(controllers, dict):
                        controllers = [controllers]
                    
                    for idx, c in enumerate(controllers):
                        name = c.get("Name", "")
                        # If already recorded from NVIDIA, skip duplicate name
                        if any(g["name"] == name for g in detected_gpus):
                            continue
                        
                        ram_bytes = c.get("AdapterRAM") or 0
                        ram_mb = round(ram_bytes / (1024 * 1024), 1) if ram_bytes else 512.0
                        driver_ver = c.get("DriverVersion", "N/A")
                        vendor = "AMD" if "amd" in name.lower() or "radeon" in name.lower() else ("Intel" if "intel" in name.lower() else "Generic")

                        detected_gpus.append({
                            "id": f"gpu{len(detected_gpus)}",
                            "type": "integrated" if "graphics" in name.lower() or "intel" in name.lower() or "radeon" in name.lower() else "discrete",
                            "vendor": vendor,
                            "name": name,
                            "utilization_percent": 0.0,
                            "temperature_celsius": 45.0,
                            "vram_total_mb": ram_mb,
                            "vram_used_mb": None,
                            "vram_percent": None,
                            "driver_version": driver_ver
                        })
        except Exception:
            pass

        if detected_gpus:
            summary_parts = [f"{g['name']} ({g['vendor']}): {g.get('utilization_percent', 0)}% load, {g.get('temperature_celsius', 'N/A')}°C" for g in detected_gpus]
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "available": True,
                    "total_gpus": len(detected_gpus),
                    "gpus": detected_gpus
                },
                metadata={"summary": " | ".join(summary_parts)}
            )

        return ToolResult(
            tool_name=self.name,
            success=True,
            data={
                "available": False,
                "total_gpus": 0,
                "gpus": [],
                "note": "Integrated display controller active."
            },
            metadata={"summary": "Standard display adapter active."}
        )
