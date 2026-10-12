"""
Friday Model Context Protocol (MCP) Integration Module.
Provides modular MCP Server & Client bridging for the Friday AI Assistant ecosystem.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.mcp.server import mcp_server, get_mcp_tools_list
from app.mcp.router import mcp_api_router
from app.mcp.client_bridge import mcp_client_bridge, ExternalMCPServerConfig

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger("Friday.MCP")


def mount_mcp_to_app(app: FastAPI) -> None:
    """
    Mounts MCP SSE transport and REST management router to the FastAPI application.
    Purely additive and modular - does not disrupt existing routes or WebSockets.
    """
    try:
        if hasattr(mcp_server, "sse_app") and callable(mcp_server.sse_app):
            sse_subapp = mcp_server.sse_app()
            if sse_subapp is not None:
                app.mount("/mcp", sse_subapp)
                logger.info("[MCP] FastMCP SSE sub-application successfully mounted at /mcp")
            else:
                logger.info("[MCP] FastMCP SSE transport skipped (using REST endpoints).")
        else:
            logger.info("[MCP] FastMCP SSE transport not available on current instance.")
    except Exception as e:
        logger.warning(f"[MCP] Notice while mounting FastMCP SSE transport: {e}")


__all__ = [
    "mcp_server",
    "mcp_api_router",
    "mcp_client_bridge",
    "ExternalMCPServerConfig",
    "get_mcp_tools_list",
    "mount_mcp_to_app",
]
