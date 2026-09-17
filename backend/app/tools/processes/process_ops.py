"""
Windows Process Management Tools for Friday AI PC Agent.
Supports process listing, port lookup, resource usage analysis, and guarded process termination.
"""
from __future__ import annotations

import socket
from typing import Any, Dict, List, Optional
import psutil
from pydantic import BaseModel, Field

from app.core.permission_manager import PROTECTED_SYSTEM_PROCESSES
from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult


class ListProcessesArgs(BaseModel):
    sort_by: str = Field("memory", description="Sort criteria: 'memory', 'cpu', or 'name'")
    limit: int = Field(25, description="Number of processes to return")


class ListProcessesTool(BaseTool):
    name = "list_processes"
    description = "List active running processes sorted by memory, CPU, or name with PID, status, and executable paths."
    permission_level = PermissionLevel.SAFE
    category = "processes"
    args_schema = ListProcessesArgs

    async def execute(self, sort_by: str = "memory", limit: int = 25, **kwargs: Any) -> ToolResult:
        try:
            procs: List[Dict[str, Any]] = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'exe', 'num_threads']):
                try:
                    info = p.info
                    mem_pct = round(info.get('memory_percent') or 0.0, 1)
                    cpu_pct = round(info.get('cpu_percent') or 0.0, 1)
                    procs.append({
                        "pid": info['pid'],
                        "name": info['name'],
                        "cpu_percent": cpu_pct,
                        "memory_percent": mem_pct,
                        "status": info.get('status', 'running'),
                        "exe": info.get('exe'),
                        "threads": info.get('num_threads')
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if sort_by == "cpu":
                procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
            elif sort_by == "name":
                procs.sort(key=lambda x: x["name"].lower())
            else:
                procs.sort(key=lambda x: x["memory_percent"], reverse=True)

            selected = procs[:limit]
            return ToolResult(
                success=True,
                data={"total_running": len(procs), "processes": selected},
                metadata={"summary": f"Retrieved top {len(selected)} processes sorted by {sort_by}."}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to list processes: {str(e)}")


class FindProcessByPortArgs(BaseModel):
    port: int = Field(..., description="TCP/UDP port number to inspect (e.g. 8000, 3000, 5432)")


class FindProcessByPortTool(BaseTool):
    name = "find_process_by_port"
    description = "Find which running process / application is listening on or using a specific port (e.g. port 8000, 5432)."
    permission_level = PermissionLevel.SAFE
    category = "processes"
    args_schema = FindProcessByPortArgs

    async def execute(self, port: int, **kwargs: Any) -> ToolResult:
        try:
            matched_processes: List[Dict[str, Any]] = []
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr and conn.laddr.port == port:
                    pid = conn.pid
                    proc_info = {"port": port, "pid": pid, "status": conn.status, "protocol": "TCP" if conn.type == socket.SOCK_STREAM else "UDP"}
                    if pid:
                        try:
                            p = psutil.Process(pid)
                            proc_info.update({
                                "name": p.name(),
                                "exe": p.exe(),
                                "cmdline": " ".join(p.cmdline()[:5]),
                                "memory_mb": round(p.memory_info().rss / (1024 * 1024), 1)
                            })
                        except Exception:
                            pass
                    matched_processes.append(proc_info)

            if matched_processes:
                main_match = matched_processes[0]
                summary = f"Port {port} is used by '{main_match.get('name', 'Unknown')}' (PID: {main_match.get('pid')})."
                return ToolResult(
                    success=True,
                    data={"port": port, "matches": matched_processes},
                    metadata={"summary": summary}
                )
            else:
                return ToolResult(
                    success=True,
                    data={"port": port, "matches": []},
                    metadata={"summary": f"No active process is using port {port}."}
                )
        except Exception as e:
            return ToolResult(success=False, error=f"Port lookup error: {str(e)}")


class TerminateProcessArgs(BaseModel):
    pid: Optional[int] = Field(None, description="PID of the process to terminate")
    process_name: Optional[str] = Field(None, description="Name of process (e.g. 'chrome.exe', 'node.exe')")
    force: bool = Field(False, description="Force termination (SIGKILL / terminate vs kill)")


class TerminateProcessTool(BaseTool):
    name = "terminate_process"
    description = "Terminate or stop a running process by PID or name. Protected system processes cannot be terminated. Requires confirmation."
    permission_level = PermissionLevel.CONFIRM
    category = "processes"
    args_schema = TerminateProcessArgs

    async def execute(self, pid: Optional[int] = None, process_name: Optional[str] = None, force: bool = False, **kwargs: Any) -> ToolResult:
        try:
            if pid is None and not process_name:
                return ToolResult(success=False, error="Must specify either pid or process_name.")

            killed_pids: List[int] = []
            targets: List[psutil.Process] = []

            if pid is not None:
                if pid in (0, 4):
                    return ToolResult(tool_name=self.name, success=False, error=f"Cannot terminate kernel process PID {pid}.", error_code="PROTECTED_PROCESS", code="PROTECTED_PROCESS")
                try:
                    targets.append(psutil.Process(pid))
                except psutil.NoSuchProcess:
                    return ToolResult(tool_name=self.name, success=False, error=f"Process with PID {pid} not found.", error_code="PROCESS_NOT_FOUND", code="PROCESS_NOT_FOUND")

            elif process_name:
                clean_name = process_name.lower().strip()
                if clean_name in PROTECTED_SYSTEM_PROCESSES:
                    return ToolResult(tool_name=self.name, success=False, error=f"Process '{process_name}' is a protected Windows system process.", error_code="PROTECTED_PROCESS", code="PROTECTED_PROCESS")
                for p in psutil.process_iter(['pid', 'name']):
                    try:
                        if p.info['name'] and p.info['name'].lower() == clean_name:
                            targets.append(p)
                    except Exception:
                        continue

            if not targets:
                return ToolResult(success=False, error=f"No matching running processes found.")

            for t in targets:
                try:
                    p_name = t.name()
                    if p_name.lower() in PROTECTED_SYSTEM_PROCESSES:
                        continue
                    if force:
                        t.kill()
                    else:
                        t.terminate()
                    killed_pids.append(t.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied) as ex:
                    print(f"[Terminate Notice]: {ex}")

            return ToolResult(
                success=True,
                data={"terminated_pids": killed_pids, "count": len(killed_pids)},
                metadata={"summary": f"Terminated {len(killed_pids)} process(es) with PID(s): {killed_pids}."}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to terminate process: {str(e)}")
