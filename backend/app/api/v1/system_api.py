import asyncio
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.tools.system.cpu import CPUStatusTool
from app.tools.system.memory import MemoryStatusTool
from app.tools.system.disk import StorageStatusTool
from app.tools.system.network import NetworkStatusTool
from app.tools.system.gpu import GPUStatusTool
from app.tools.system.battery import BatteryStatusTool
from app.tools.system.system_info import SystemInfoTool
from app.tools.system.services import ListServicesTool, ManageServiceTool
from app.services.monitoring_service import monitoring_service
from app.services.power_service import (
    load_power_settings,
    save_power_settings,
    set_windows_power_profile,
    optimize_battery_for_unplugged,
)

router = APIRouter(prefix="/system", tags=["System & Hardware"])

cpu_tool = CPUStatusTool()
mem_tool = MemoryStatusTool()
disk_tool = StorageStatusTool()
net_tool = NetworkStatusTool()
gpu_tool = GPUStatusTool()
battery_tool = BatteryStatusTool()
sys_info_tool = SystemInfoTool()
services_tool = ListServicesTool()
manage_service_tool = ManageServiceTool()


class PowerProfileRequest(BaseModel):
    profile: str  # "saver", "balanced", "performance"


class ServiceActionRequest(BaseModel):
    action: str  # "start", "stop", "restart", "status"


@router.get("/overview")
async def get_system_overview() -> Dict[str, Any]:
    """Retrieves an aggregated hardware snapshot of the computer."""
    return await asyncio.to_thread(monitoring_service.get_quick_snapshot)


@router.get("/cpu")
def get_cpu_status(
    per_core: bool = Query(default=True, description="Include per-core usage"),
    top_processes: bool = Query(default=True, description="Include top CPU-consuming processes")
) -> Dict[str, Any]:
    res = cpu_tool.run(include_per_core=per_core, include_top_processes=top_processes)
    if not res.success:
        raise HTTPException(status_code=500, detail=res.error)
    return res.data


@router.get("/memory")
def get_memory_status(
    top_processes: bool = Query(default=True, description="Include top memory-consuming processes")
) -> Dict[str, Any]:
    res = mem_tool.run(include_top_processes=top_processes)
    if not res.success:
        raise HTTPException(status_code=500, detail=res.error)
    return res.data


@router.get("/storage")
def get_storage_status() -> Dict[str, Any]:
    res = disk_tool.run()
    if not res.success:
        raise HTTPException(status_code=500, detail=res.error)
    return res.data


@router.get("/network")
def get_network_status(
    connections: bool = Query(default=True, description="Include listening ports and connections")
) -> Dict[str, Any]:
    res = net_tool.run(include_connections=connections)
    if not res.success:
        raise HTTPException(status_code=500, detail=res.error)
    return res.data


@router.get("/gpu")
def get_gpu_status() -> Dict[str, Any]:
    res = gpu_tool.run()
    return res.data


@router.get("/battery")
def get_battery_status() -> Dict[str, Any]:
    res = battery_tool.run()
    return res.data


@router.get("/info")
def get_system_info() -> Dict[str, Any]:
    res = sys_info_tool.run()
    if not res.success:
        raise HTTPException(status_code=500, detail=res.error)
    return res.data


# ==========================================
# PROCESS MONITORING & MANAGEMENT
# ==========================================

_PROC_CPU_CACHE: Dict[int, tuple[float, float]] = {}


@router.get("/processes")
def get_running_processes(
    limit: int = 100,
    sort_by: str = "cpu",
    search: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieves live running Windows processes with accurate real CPU% and memory usage."""
    import psutil
    import time

    global _PROC_CPU_CACHE
    now = time.monotonic()
    num_cpus = psutil.cpu_count() or 1
    new_cache: Dict[int, tuple[float, float]] = {}
    procs: List[Dict[str, Any]] = []

    search_query = search.strip().lower() if isinstance(search, str) and search.strip() else None

    for p in psutil.process_iter(['pid', 'name', 'memory_info', 'status', 'username', 'num_threads']):
        try:
            pid = p.info['pid']
            name = p.info['name']
            if not name or pid == 0:
                continue

            if search_query:
                if search_query not in name.lower() and search_query not in str(pid):
                    continue

            # Calculate live CPU% from process cpu_times delta
            cpu_pct = 0.0
            try:
                cpu_times = p.cpu_times()
                total_time = cpu_times.user + cpu_times.system
                new_cache[pid] = (total_time, now)

                if pid in _PROC_CPU_CACHE:
                    prev_time, prev_t = _PROC_CPU_CACHE[pid]
                    dt = now - prev_t
                    if dt > 0.01:
                        time_delta = total_time - prev_time
                        cpu_pct = round(max(0.0, min(100.0, (time_delta / (dt * num_cpus)) * 100.0)), 1)
            except Exception:
                pass

            mem_info = p.info.get('memory_info')
            rss_mb = round(mem_info.rss / (1024 * 1024), 1) if mem_info else 0.0
            raw_user = p.info.get('username') or "SYSTEM"
            user_clean = raw_user.split("\\")[-1] if "\\" in raw_user else raw_user

            # Flag system critical processes to warn before termination
            is_critical = pid <= 4 or name.lower() in [
                "system", "registry", "smss.exe", "csrss.exe", "wininit.exe",
                "services.exe", "lsass.exe", "winlogon.exe", "fontdrvhost.exe"
            ]

            procs.append({
                "pid": pid,
                "name": name,
                "cpu_percent": cpu_pct,
                "memory_percent": round(p.info.get('memory_percent') or 0.0, 1),
                "memory_mb": rss_mb,
                "status": str(p.info.get('status') or "running").upper(),
                "user": user_clean,
                "threads": p.info.get('num_threads') or 1,
                "is_critical": is_critical
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    _PROC_CPU_CACHE = new_cache

    if sort_by == "cpu":
        procs.sort(key=lambda x: (x.get('cpu_percent', 0.0), x.get('memory_mb', 0.0)), reverse=True)
    elif sort_by == "name":
        procs.sort(key=lambda x: x.get('name', '').lower())
    else:
        procs.sort(key=lambda x: (x.get('memory_mb', 0.0), x.get('cpu_percent', 0.0)), reverse=True)

    return {
        "total_processes": len(procs),
        "processes": procs[:limit]
    }


@router.post("/processes/{pid}/kill")
def terminate_process(pid: int, force: bool = Query(default=False)) -> Dict[str, Any]:
    """Terminates or kills a process by PID with protection for system-critical processes."""
    import psutil

    if pid <= 4:
        raise HTTPException(status_code=400, detail="Cannot terminate core Windows System process.")

    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
        
        # Guard against critical windows processes
        if proc_name.lower() in ["csrss.exe", "smss.exe", "wininit.exe", "services.exe", "lsass.exe"]:
            raise HTTPException(status_code=403, detail=f"Terminating critical process '{proc_name}' is forbidden to prevent system crash.")

        if force:
            proc.kill()
        else:
            proc.terminate()

        return {
            "success": True,
            "pid": pid,
            "name": proc_name,
            "message": f"Process {proc_name} (PID: {pid}) terminated successfully."
        }
    except psutil.NoSuchProcess:
        raise HTTPException(status_code=404, detail=f"Process with PID {pid} does not exist.")
    except psutil.AccessDenied:
        raise HTTPException(status_code=403, detail=f"Access denied terminating PID {pid}. Elevated administrator permissions required.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to terminate process: {str(e)}")


# ==========================================
# WINDOWS SERVICES MANAGEMENT
# ==========================================

@router.get("/services")
def list_windows_services(
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 150
) -> Dict[str, Any]:
    res = services_tool.run(search_query=search, status_filter=status, limit=limit)
    if not res.success:
        raise HTTPException(status_code=500, detail=res.error)
    return res.data


@router.post("/services/{service_name}/action")
async def execute_service_action(service_name: str, payload: ServiceActionRequest) -> Dict[str, Any]:
    """Controls a Windows service (start, stop, restart, or status)."""
    res = await manage_service_tool.execute(service_name=service_name, action=payload.action)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error)
    return res.data


# ==========================================
# POWER & BATTERY PROFILES
# ==========================================

@router.get("/power")
def get_power_status() -> Dict[str, Any]:
    """Gets power settings, active scheme, and battery optimization state."""
    settings = load_power_settings()
    return {
        "success": True,
        "settings": settings
    }


@router.post("/power/profile")
def set_power_profile(payload: PowerProfileRequest) -> Dict[str, Any]:
    """Switches the Windows OS power profile: 'saver', 'balanced', or 'performance'."""
    success = set_windows_power_profile(payload.profile)
    settings = load_power_settings()
    settings["active_profile"] = payload.profile
    if payload.profile == "saver":
        settings["eco_mode"] = True
    elif payload.profile == "performance":
        settings["eco_mode"] = False
    save_power_settings(settings)

    return {
        "success": success,
        "profile": payload.profile,
        "message": f"Power profile switched to {payload.profile.upper()}." if success else "Failed to switch power profile via powercfg."
    }
