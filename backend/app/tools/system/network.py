"""
Network Monitoring Tool for Friday AI PC Agent.
Reports interfaces, IP addresses, I/O rates, listening ports, and socket details.
"""
from __future__ import annotations

import socket
from typing import Any, Dict, List, Optional
import psutil
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.schemas.system_schemas import ListeningPortInfo, NetworkInterfaceInfo, NetworkStatus


class NetworkArgsSchema(BaseModel):
    include_ports: bool = Field(True, description="Whether to include listening ports")


class NetworkStatusTool(BaseTool):
    name = "get_network_status"
    description = "Get network information: active network interfaces, IP addresses, total bytes sent/received, and listening ports."
    permission_level = PermissionLevel.SAFE
    category = "system"
    args_schema = NetworkArgsSchema

    async def execute(self, include_ports: bool = True, **kwargs: Any) -> ToolResult:
        try:
            hostname = socket.gethostname()
            primary_ip: Optional[str] = None
            try:
                primary_ip = socket.gethostbyname(hostname)
            except Exception:
                pass

            net_io = psutil.net_io_counters()
            net_addrs = psutil.net_if_addrs()
            net_stats = psutil.net_if_stats()

            interfaces: List[NetworkInterfaceInfo] = []
            for iface_name, addrs in net_addrs.items():
                stats = net_stats.get(iface_name)
                is_up = stats.isup if stats else True
                speed = stats.speed if stats else None

                addr_list = []
                for a in addrs:
                    family_str = "IPv4" if a.family == socket.AF_INET else "IPv6" if a.family == socket.AF_INET6 else "MAC"
                    addr_list.append({"family": family_str, "address": a.address})

                interfaces.append(NetworkInterfaceInfo(
                    name=iface_name,
                    is_up=is_up,
                    speed_mbps=speed,
                    addresses=addr_list
                ))

            listening_ports: List[ListeningPortInfo] = []
            if include_ports:
                try:
                    connections = psutil.net_connections(kind="inet")
                    for c in connections:
                        if c.status == "LISTEN":
                            proc_name = None
                            if c.pid:
                                try:
                                    proc_name = psutil.Process(c.pid).name()
                                except Exception:
                                    pass
                            listening_ports.append(ListeningPortInfo(
                                port=c.laddr.port,
                                protocol="TCP" if c.type == socket.SOCK_STREAM else "UDP",
                                pid=c.pid,
                                process_name=proc_name,
                                status=c.status
                            ))
                except (psutil.AccessDenied, PermissionError):
                    pass

            status = NetworkStatus(
                interfaces=interfaces,
                bytes_sent=net_io.bytes_sent,
                bytes_recv=net_io.bytes_recv,
                listening_ports=listening_ports,
                hostname=hostname,
                ip_address=primary_ip
            )

            sent_mb = round(net_io.bytes_sent / (1024 * 1024), 1)
            recv_mb = round(net_io.bytes_recv / (1024 * 1024), 1)

            return ToolResult(
                success=True,
                data=status.model_dump(),
                metadata={"summary": f"Host: {hostname} ({primary_ip}) | Sent: {sent_mb} MB, Recv: {recv_mb} MB | {len(listening_ports)} listening ports"}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to read network status: {str(e)}")
