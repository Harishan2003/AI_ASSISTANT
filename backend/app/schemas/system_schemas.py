"""
Pydantic schemas for Windows PC Hardware & System Monitoring
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CPUCoreInfo(BaseModel):
    core_id: int
    usage_percent: float


class CPUStatus(BaseModel):
    total_usage_percent: float
    per_core_usage: List[float] = Field(default_factory=list)
    frequency_mhz: Optional[float] = None
    min_frequency_mhz: Optional[float] = None
    max_frequency_mhz: Optional[float] = None
    physical_cores: int
    logical_cores: int
    temperature_celsius: Optional[float] = None
    top_processes: List[Dict[str, Any]] = Field(default_factory=list)


class GPUStatus(BaseModel):
    available: bool = False
    name: Optional[str] = None
    utilization_percent: Optional[float] = None
    memory_total_mb: Optional[float] = None
    memory_used_mb: Optional[float] = None
    memory_free_mb: Optional[float] = None
    memory_percent: Optional[float] = None
    temperature_celsius: Optional[float] = None
    driver_version: Optional[str] = None
    power_draw_watts: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class MemoryStatus(BaseModel):
    total_gb: float
    used_gb: float
    available_gb: float
    free_gb: float
    percent: float
    swap_total_gb: Optional[float] = None
    swap_used_gb: Optional[float] = None
    swap_percent: Optional[float] = None
    top_processes: List[Dict[str, Any]] = Field(default_factory=list)


class DriveInfo(BaseModel):
    device: str
    mountpoint: str
    fstype: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


class StorageStatus(BaseModel):
    drives: List[DriveInfo] = Field(default_factory=list)
    read_bytes_sec: Optional[float] = None
    write_bytes_sec: Optional[float] = None


class NetworkInterfaceInfo(BaseModel):
    name: str
    is_up: bool
    speed_mbps: Optional[int] = None
    addresses: List[Dict[str, str]] = Field(default_factory=list)


class ListeningPortInfo(BaseModel):
    port: int
    protocol: str
    pid: Optional[int] = None
    process_name: Optional[str] = None
    status: str = "LISTEN"


class NetworkStatus(BaseModel):
    interfaces: List[NetworkInterfaceInfo] = Field(default_factory=list)
    bytes_sent: int
    bytes_recv: int
    bytes_sent_per_sec: float = 0.0
    bytes_recv_per_sec: float = 0.0
    listening_ports: List[ListeningPortInfo] = Field(default_factory=list)
    hostname: str
    ip_address: Optional[str] = None


class BatteryStatus(BaseModel):
    has_battery: bool
    percent: Optional[float] = None
    power_plugged: Optional[bool] = None
    secs_left: Optional[int] = None
    status_text: str = "Unknown"


class SystemOverview(BaseModel):
    os_name: str
    os_version: str
    os_release: str
    architecture: str
    hostname: str
    cpu_model: str
    physical_cores: int
    logical_cores: int
    total_ram_gb: float
    boot_time: str
    uptime: str
    python_version: str
    drives: List[str] = Field(default_factory=list)


class ProcessItem(BaseModel):
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    status: str
    num_threads: int
    exe_path: Optional[str] = None
    create_time: Optional[str] = None
    username: Optional[str] = None


class SystemFullStatus(BaseModel):
    timestamp: str
    cpu: CPUStatus
    gpu: GPUStatus
    memory: MemoryStatus
    storage: StorageStatus
    network: NetworkStatus
    battery: BatteryStatus
    overview: SystemOverview
