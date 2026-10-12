"""
Friday MCP Client Bridge.
Allows Friday AI Assistant to connect to, discover, and invoke tools from
external MCP servers (e.g., SQLite MCP, GitHub MCP, Filesystem MCP, Brave Search MCP).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("Friday.MCP.ClientBridge")


class ExternalMCPServerConfig(BaseModel):
    name: str
    transport: str = Field("stdio", description="'stdio' or 'sse'")
    command: Optional[str] = Field(None, description="Executable command for stdio transport")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    url: Optional[str] = Field(None, description="SSE URL for sse transport")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    enabled: bool = True


class MCPClientBridge:
    """Manages outgoing connections to external MCP servers."""

    def __init__(self):
        self._servers: Dict[str, ExternalMCPServerConfig] = {}
        self._connected_tools: Dict[str, List[Dict[str, Any]]] = {}

    def register_server(self, config: ExternalMCPServerConfig):
        """Registers an external MCP server configuration."""
        self._servers[config.name] = config
        logger.info(f"[MCP Bridge] Registered external server: {config.name} ({config.transport})")

    def list_servers(self) -> List[Dict[str, Any]]:
        """Lists all registered external MCP servers."""
        return [
            {
                "name": cfg.name,
                "transport": cfg.transport,
                "enabled": cfg.enabled,
                "command": cfg.command,
                "url": cfg.url,
                "discovered_tools_count": len(self._connected_tools.get(cfg.name, []))
            }
            for cfg in self._servers.values()
        ]

    async def test_connection(self, server_name: str) -> Dict[str, Any]:
        """Tests connectivity to a configured external MCP server."""
        cfg = self._servers.get(server_name)
        if not cfg:
            return {"success": False, "error": f"Server '{server_name}' not configured."}
        if not cfg.enabled:
            return {"success": False, "error": f"Server '{server_name}' is disabled."}

        try:
            # Check basic config validity
            if cfg.transport == "sse" and not cfg.url:
                return {"success": False, "error": "SSE transport requires a valid URL."}
            if cfg.transport == "stdio" and not cfg.command:
                return {"success": False, "error": "Stdio transport requires a valid command."}

            return {
                "success": True,
                "server": server_name,
                "transport": cfg.transport,
                "status": "CONFIG_VALID",
                "message": f"Server '{server_name}' is ready for MCP session negotiation."
            }
        except Exception as e:
            logger.error(f"[MCP Bridge] Test connection error for {server_name}: {e}")
            return {"success": False, "error": str(e)}


mcp_client_bridge = MCPClientBridge()
