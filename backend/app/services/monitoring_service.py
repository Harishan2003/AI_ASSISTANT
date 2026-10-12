"""
Live System Telemetry and Hardware Monitoring Service for Windows.
Periodically samples CPU, Memory, Disk, Network, GPU, and Power metrics and broadcasts over EventBus/WebSockets.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional
import psutil

from app.core.event_bus import event_bus
from app.tools.system.cpu import CPUStatusTool
from app.tools.system.memory import MemoryStatusTool
from app.tools.system.disk import StorageStatusTool
from app.tools.system.network import NetworkStatusTool
from app.tools.system.gpu import GPUStatusTool
from app.tools.system.battery import BatteryStatusTool
from app.tools.system.system_info import SystemInfoTool

logger = logging.getLogger(__name__)


class MonitoringService:
    """Collects, caches, and broadcasts real-time system metrics."""

    def __init__(self, interval_seconds: float = 2.0):
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._cached_snapshot: Optional[Dict[str, Any]] = None
        self._last_snapshot_time: float = 0.0

        # Reusable tools for snapshot sampling
        self.cpu_tool = CPUStatusTool()
        self.mem_tool = MemoryStatusTool()
        self.disk_tool = StorageStatusTool()
        self.net_tool = NetworkStatusTool()
        self.gpu_tool = GPUStatusTool()
        self.battery_tool = BatteryStatusTool()
        self.sys_tool = SystemInfoTool()

    def get_quick_snapshot(self) -> Dict[str, Any]:
        """Collects a synchronous, fast hardware metric dictionary with TTL caching."""
        now = time.monotonic()
        if self._cached_snapshot is not None and (now - self._last_snapshot_time < 0.6):
            return self._cached_snapshot

        try:
            cpu_res = self.cpu_tool.run(include_per_core=True, include_top_processes=False)
            mem_res = self.mem_tool.run(include_top_processes=False)
            disk_res = self.disk_tool.run()
            net_res = self.net_tool.run(include_connections=False)
            gpu_res = self.gpu_tool.run()
            battery_res = self.battery_tool.run()

            snapshot = {
                "timestamp": time.strftime("%H:%M:%S"),
                "cpu": cpu_res.data if cpu_res.success else None,
                "memory": mem_res.data if mem_res.success else None,
                "storage": disk_res.data if disk_res.success else None,
                "network": net_res.data if net_res.success else None,
                "gpu": gpu_res.data if gpu_res.success else None,
                "battery": battery_res.data if battery_res.success else None,
            }
            self._cached_snapshot = snapshot
            self._last_snapshot_time = now
            return snapshot
        except Exception as e:
            logger.error(f"Error collecting telemetry snapshot: {e}")
            return {"error": str(e)}

    async def _monitor_loop(self):
        logger.info("Starting background hardware telemetry loop...")
        while self._running:
            try:
                snapshot = await asyncio.to_thread(self.get_quick_snapshot)
                await event_bus.publish("system.telemetry", snapshot)
            except Exception as e:
                logger.error(f"Telemetry loop iteration error: {e}")
            await asyncio.sleep(self.interval_seconds)

    def start(self):
        if not self._running:
            self._running = True
            try:
                loop = asyncio.get_running_loop()
                self._task = loop.create_task(self._monitor_loop())
            except RuntimeError:
                pass

    def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()


monitoring_service = MonitoringService()
