"""
Tests for System & Hardware Monitoring Tools.
"""

import pytest
from app.tools.system.cpu import CPUStatusTool
from app.tools.system.memory import MemoryStatusTool
from app.tools.system.disk import StorageStatusTool
from app.tools.system.network import NetworkStatusTool
from app.tools.system.gpu import GPUStatusTool
from app.tools.system.battery import BatteryStatusTool
from app.tools.system.system_info import SystemInfoTool
from app.tools.system.services import ListServicesTool


def test_cpu_status_tool():
    tool = CPUStatusTool()
    res = tool.run(include_top_processes=True)
    assert res.success is True
    assert "total_usage_percent" in res.data
    assert isinstance(res.data["total_usage_percent"], (int, float))
    assert "logical_cores" in res.data
    assert res.data["logical_cores"] >= 1


def test_memory_status_tool():
    tool = MemoryStatusTool()
    res = tool.run(include_top_processes=True)
    assert res.success is True
    assert "total_gb" in res.data
    assert "percent" in res.data
    assert res.data["total_gb"] > 0
    assert 0 <= res.data["percent"] <= 100


def test_storage_status_tool():
    tool = StorageStatusTool()
    res = tool.run()
    assert res.success is True
    assert "drives" in res.data
    assert len(res.data["drives"]) >= 1
    c_drive = res.data["drives"][0]
    assert "mountpoint" in c_drive
    assert "free_gb" in c_drive


def test_network_status_tool():
    tool = NetworkStatusTool()
    res = tool.run(include_connections=False)
    assert res.success is True
    assert "interfaces" in res.data
    assert "bytes_sent" in res.data
    assert "bytes_recv" in res.data


def test_gpu_status_tool_graceful():
    tool = GPUStatusTool()
    res = tool.run()
    assert res.success is True
    assert "available" in res.data


def test_battery_status_tool_graceful():
    tool = BatteryStatusTool()
    res = tool.run()
    assert res.success is True
    assert "has_battery" in res.data
    if res.data["has_battery"]:
        assert "percent" in res.data
    else:
        assert res.data["power_plugged"] is True


def test_system_info_tool():
    tool = SystemInfoTool()
    res = tool.run()
    assert res.success is True
    assert res.data["os_name"] == "Windows"
    assert "cpu_model" in res.data
    assert "hostname" in res.data


def test_list_services_tool():
    tool = ListServicesTool()
    res = tool.run(limit=10)
    assert res.success is True
    assert "services" in res.data
    assert len(res.data["services"]) <= 10
