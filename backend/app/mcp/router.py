"""
FastAPI REST Router and Management Endpoints for Friday MCP Server.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.mcp.server import mcp_server, get_mcp_tools_list
from app.mcp.client_bridge import mcp_client_bridge, ExternalMCPServerConfig

logger = logging.getLogger("Friday.MCP.Router")

mcp_api_router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (MCP)"])


class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the MCP tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments dictionary")


@mcp_api_router.get("/status")
def get_mcp_status() -> Dict[str, Any]:
    """Returns Friday MCP Server status, capability flags, and endpoint URIs."""
    tools = get_mcp_tools_list()
    return {
        "status": "ONLINE",
        "protocol": "Model Context Protocol (MCP)",
        "server_name": mcp_server.name,
        "tools_count": len(tools),
        "endpoints": {
            "sse": "/mcp/sse",
            "messages": "/mcp/messages",
            "rest_tools": "/api/v1/mcp/tools",
            "rest_call": "/api/v1/mcp/call"
        },
        "description": "Friday AI Assistant MCP Server with full PC telemetry and tool bridging."
    }


@mcp_api_router.get("/tools")
def list_mcp_tools() -> Dict[str, Any]:
    """Lists all registered MCP tools with parameter schemas."""
    tools = get_mcp_tools_list()
    return {
        "count": len(tools),
        "tools": tools
    }


@mcp_api_router.post("/call")
async def call_mcp_tool(req: ToolCallRequest) -> Dict[str, Any]:
    """Directly invokes an MCP tool over REST."""
    tool_name = req.tool_name
    try:
        # Check if tool exists on FastMCP server
        tool_mgr = getattr(mcp_server, "_tool_manager", None)
        tool_obj = getattr(tool_mgr, "_tools", {}).get(tool_name) if tool_mgr else None

        if not tool_obj:
            raise HTTPException(
                status_code=404,
                detail=f"MCP tool '{tool_name}' not found. Available: {[t['name'] for t in get_mcp_tools_list()]}"
            )

        fn = getattr(tool_obj, "fn", None)
        if not fn:
            raise HTTPException(status_code=500, detail=f"Tool '{tool_name}' has no callable function.")

        import inspect
        if inspect.iscoroutinefunction(fn):
            result = await fn(**req.arguments)
        else:
            result = fn(**req.arguments)

        # Parse string result as JSON if possible for cleaner response
        parsed_result = result
        if isinstance(result, str):
            try:
                parsed_result = json.loads(result)
            except Exception:
                pass

        return {
            "success": True,
            "tool_name": tool_name,
            "result": parsed_result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MCP] Tool execution error for {tool_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")


@mcp_api_router.get("/external-servers")
def list_external_mcp_servers() -> Dict[str, Any]:
    """Lists configured external MCP server bridges."""
    return {
        "servers": mcp_client_bridge.list_servers()
    }


@mcp_api_router.post("/external-servers")
def register_external_mcp_server(config: ExternalMCPServerConfig) -> Dict[str, Any]:
    """Registers a new external MCP server connection."""
    mcp_client_bridge.register_server(config)
    return {
        "success": True,
        "message": f"External MCP server '{config.name}' registered successfully."
    }
