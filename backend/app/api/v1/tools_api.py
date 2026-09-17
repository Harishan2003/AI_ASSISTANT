"""
Tools Discovery & Direct Execution REST Endpoints.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from app.schemas.agent_schemas import ToolDefinition, ToolResult, PermissionLevel
from app.core.tool_router import tool_router

router = APIRouter(prefix="/tools", tags=["Tools Registry"])


class DirectToolExecuteRequest(BaseModel):
    tool_name: str = Field(..., description="Name of registered tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments dictionary matching the tool's schema")


@router.get("", response_model=List[ToolDefinition])
def list_available_tools() -> List[ToolDefinition]:
    """Lists all available agent tools, parameters, and permission levels."""
    return tool_router.list_tools()


@router.post("/execute", response_model=ToolResult)
def execute_tool_directly(request: DirectToolExecuteRequest) -> ToolResult:
    """Executes a registered tool directly with given arguments."""
    tool = tool_router.get_tool(request.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{request.tool_name}' not found.")

    if tool.permission_level == PermissionLevel.RESTRICTED:
        raise HTTPException(status_code=403, detail=f"Tool '{request.tool_name}' is restricted.")

    return tool_router.execute_tool(request.tool_name, request.arguments)
