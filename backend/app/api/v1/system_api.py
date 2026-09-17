"""
System and Hardware Telemetry REST Endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional

from app.tools.system.cpu import CPUStatusTool
from app.tools.system.memory import MemoryStatusTool
from app.tools.system.disk import StorageStatusTool
from app.tools.system.network import NetworkStatusTool
from app.tools.system.gpu import GPUStatusTool
from app.tools.system.battery import BatteryStatusTool
from app.tools.system.system_info import SystemInfoTool
from app.tools.system.services import ListServicesTool, ManageServiceTool
from app.services.monitoring_service import monitoring_service

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


@router.get("/overview")
def get_system_overview() -> Dict[str, Any]:
    """Retrieves an aggregated hardware snapshot of the computer."""
    return monitoring_service.get_quick_snapshot()


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


@router.get("/services")
def list_windows_services(
    status: Optional[str] = Query(default=None, description="Filter: 'running' or 'stopped'")
) -> Dict[str, Any]:
    res = services_tool.run(status_filter=status)
    if not res.success:
        raise HTTPException(status_code=500, detail=res.error)
    return res.data
