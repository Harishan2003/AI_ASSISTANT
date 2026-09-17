"""
Windows Services Tool for Friday AI PC Agent.
"""
from __future__ import annotations

import subprocess
from typing import Any, Dict, List, Optional
import psutil
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult


class ListServicesSchema(BaseModel):
    search_query: Optional[str] = Field(None, description="Filter service names or display names")
    status_filter: Optional[str] = Field(None, description="'running', 'stopped', or None for all")
    limit: int = Field(100, description="Max services to return")


class ManageServiceSchema(BaseModel):
    service_name: str = Field(..., description="The name of the Windows service (e.g. postgresql, wuauserv)")
    action: str = Field(..., description="Action to perform: 'status', 'start', 'stop', 'restart'")


class ListServicesTool(BaseTool):
    name = "list_services"
    description = "List installed Windows services with status (running/stopped), display name, and start type."
    permission_level = PermissionLevel.SAFE
    category = "system"
    args_schema = ListServicesSchema

    async def execute(self, search_query: Optional[str] = None, status_filter: Optional[str] = None, limit: int = 100, **kwargs: Any) -> ToolResult:
        try:
            services_list: List[Dict[str, Any]] = []
            for s in psutil.win_service_iter():
                try:
                    info = s.as_dict()
                    name = info.get("name", "")
                    disp = info.get("display_name", "")
                    stat = info.get("status", "")

                    if search_query:
                        q = search_query.lower()
                        if q not in name.lower() and q not in disp.lower():
                            continue

                    if status_filter:
                        if status_filter.lower() != stat.lower():
                            continue

                    services_list.append({
                        "name": name,
                        "display_name": disp,
                        "status": stat,
                        "start_type": info.get("start_type", ""),
                        "pid": info.get("pid")
                    })
                    if len(services_list) >= limit:
                        break
                except Exception:
                    continue

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"total": len(services_list), "services": services_list[:limit]},
                metadata={"summary": f"Found {len(services_list)} Windows services."}
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, error=f"Failed to list services: {str(e)}")


class ManageServiceTool(BaseTool):
    name = "manage_service"
    description = "Check status, start, stop, or restart a Windows service. Stopping or restarting services requires human confirmation."
    permission_level = PermissionLevel.CONFIRM
    category = "system"
    args_schema = ManageServiceSchema

    async def execute(self, service_name: str, action: str, **kwargs: Any) -> ToolResult:
        act = action.lower().strip()
        try:
            # Check existence first
            try:
                srv = psutil.win_service_get(service_name)
                info = srv.as_dict()
            except Exception:
                return ToolResult(success=False, error=f"Service '{service_name}' not found.", code="SERVICE_NOT_FOUND")

            if act == "status":
                return ToolResult(
                    success=True,
                    data=info,
                    metadata={"summary": f"Service '{service_name}' is currently {info.get('status')}."}
                )

            if act in ("start", "stop", "restart"):
                cmd = f"powershell -NoProfile -Command \"{act.capitalize()}-Service -Name '{service_name}' -Force\""
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10.0)
                if proc.returncode == 0:
                    # re-check status
                    new_stat = psutil.win_service_get(service_name).status()
                    return ToolResult(
                        success=True,
                        data={"service_name": service_name, "status": new_stat, "action_performed": act},
                        metadata={"summary": f"Service '{service_name}' successfully {act}ed. New status: {new_stat}"}
                    )
                else:
                    err = proc.stderr.strip() or f"Failed to {act} service."
                    return ToolResult(success=False, error=err, code="SERVICE_ACTION_FAILED")

            return ToolResult(success=False, error=f"Invalid action '{action}'. Use status, start, stop, or restart.")
        except Exception as e:
            return ToolResult(success=False, error=f"Service operation error: {str(e)}")
