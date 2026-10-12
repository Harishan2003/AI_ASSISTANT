"""
Friday Model Context Protocol (MCP) Server Implementation.
Exposes Friday AI Assistant capabilities, hardware telemetry, file operations,
and system tools to MCP-compatible clients (Claude Desktop, Cursor, external LLMs).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mcp.server.fastmcp import FastMCP
    HAVE_MCP = True
except (ImportError, ModuleNotFoundError):
    HAVE_MCP = False

    class FastMCP:  # type: ignore
        """Fallback lightweight FastMCP shim if official mcp package is missing."""
        def __init__(self, name: str = "Friday-AI-Assistant", instructions: str = "", **kwargs):
            self.name = name
            self.instructions = instructions
            self._tools: Dict[str, Any] = {}
            self._resources: Dict[str, Any] = {}
            self._prompts: Dict[str, Any] = {}
            self._tool_manager = type("ToolMgr", (), {"_tools": self._tools})()

        def tool(self, name: Optional[str] = None, description: str = ""):
            def decorator(fn):
                tool_name = name or fn.__name__
                self._tools[tool_name] = type("ToolObj", (), {
                    "name": tool_name,
                    "description": description or (fn.__doc__ or ""),
                    "fn": fn,
                    "parameters": {}
                })()
                return fn
            return decorator

        def resource(self, uri: str, name: str = "", description: str = ""):
            def decorator(fn):
                self._resources[uri] = {"name": name, "description": description, "fn": fn}
                return fn
            return decorator

        def prompt(self, name: str, description: str = ""):
            def decorator(fn):
                self._prompts[name] = {"description": description, "fn": fn}
                return fn
            return decorator

        def sse_app(self):
            """Returns a lightweight Starlette/ASGI dummy app when mcp is in fallback mode."""
            try:
                from starlette.applications import Starlette
                from starlette.responses import JSONResponse
                from starlette.routing import Route

                async def fallback_status(request):
                    return JSONResponse({"status": "ONLINE", "mode": "fallback_rest_only"})

                return Starlette(routes=[Route("/status", fallback_status)])
            except Exception:
                return None

from app.core.tool_router import tool_router
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger("Friday.MCP")

# Initialize Friday FastMCP Server
mcp_server = FastMCP(
    name="Friday-AI-Assistant",
    instructions=(
        "Friday AI Assistant MCP Server. Provides comprehensive access to local PC telemetry, "
        "hardware metrics (AMD Ryzen CPU, NVIDIA RTX 3050 & AMD Radeon GPUs), file system tools, "
        "Windows task management, and assistant capabilities."
    )
)


# ---------------------------------------------------------------------------
# 1. HARDWARE & SYSTEM TELEMETRY MCP TOOLS
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="friday_get_system_overview",
    description="Get real-time hardware telemetry snapshot: AMD Ryzen CPU %, DDR5 RAM %, dual GPUs (NVIDIA RTX 3050 + AMD Radeon), storage disks, and battery status."
)
def get_system_overview() -> str:
    """Returns a full live system hardware snapshot as JSON."""
    try:
        snapshot = monitoring_service.get_quick_snapshot()
        return json.dumps(snapshot, indent=2)
    except Exception as e:
        logger.error(f"[MCP] get_system_overview error: {e}", exc_info=True)
        return json.dumps({"error": str(e), "success": False})


@mcp_server.tool(
    name="friday_get_cpu_metrics",
    description="Get detailed CPU processor telemetry including 6 physical / 12 logical cores load %, clock frequency in GHz, and thermal status."
)
def get_cpu_metrics(include_per_core: bool = True) -> str:
    """Returns live CPU load and per-core breakdown."""
    try:
        from app.tools.system.cpu import CPUStatusTool
        tool = CPUStatusTool()
        res = tool.run(include_per_core=include_per_core, include_top_processes=True)
        return json.dumps(res.data if res.success else {"error": res.error}, indent=2)
    except Exception as e:
        logger.error(f"[MCP] get_cpu_metrics error: {e}")
        return json.dumps({"error": str(e), "success": False})


@mcp_server.tool(
    name="friday_get_gpu_metrics",
    description="Get real-time dual GPU telemetry: NVIDIA GeForce RTX 3050 Laptop GPU (temperature, VRAM, power) and AMD Radeon Graphics."
)
def get_gpu_metrics() -> str:
    """Returns live metrics for all detected GPUs."""
    try:
        from app.tools.system.gpu import GPUStatusTool
        tool = GPUStatusTool()
        res = tool.run()
        return json.dumps(res.data if res.success else {"error": res.error}, indent=2)
    except Exception as e:
        logger.error(f"[MCP] get_gpu_metrics error: {e}")
        return json.dumps({"error": str(e), "success": False})


@mcp_server.tool(
    name="friday_get_running_processes",
    description="Query live Windows Task Manager processes sorted by CPU % or Memory MB with real PIDs, users, and CPU utilization."
)
def get_running_processes(sort_by: str = "cpu", limit: int = 30) -> str:
    """Returns list of active Windows processes."""
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info', 'username']):
            try:
                info = p.info
                mem_mb = round((info.get('memory_info').rss if info.get('memory_info') else 0) / (1024 * 1024), 2)
                procs.append({
                    "pid": info.get("pid"),
                    "name": info.get("name"),
                    "cpu_percent": info.get("cpu_percent") or 0.0,
                    "memory_percent": round(info.get("memory_percent") or 0.0, 2),
                    "memory_mb": mem_mb,
                    "username": info.get("username") or ""
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if sort_by.lower() == "memory":
            procs.sort(key=lambda x: x["memory_mb"], reverse=True)
        else:
            procs.sort(key=lambda x: x["cpu_percent"], reverse=True)

        return json.dumps({
            "success": True,
            "count": len(procs[:limit]),
            "processes": procs[:limit]
        }, indent=2)
    except Exception as e:
        logger.error(f"[MCP] get_running_processes error: {e}")
        return json.dumps({"error": str(e), "success": False})


@mcp_server.tool(
    name="friday_get_network_status",
    description="Get live network interfaces (Wi-Fi 6, Ethernet, Loopback), IP addresses, download/upload speeds in MB/s, and active listening ports."
)
def get_network_status(include_ports: bool = True) -> str:
    """Returns live network throughput, active adapters, and listening ports."""
    try:
        from app.tools.system.network import NetworkStatusTool
        tool = NetworkStatusTool()
        res = tool.run(include_ports=include_ports)
        return json.dumps(res.data if res.success else {"error": res.error}, indent=2)
    except Exception as e:
        logger.error(f"[MCP] get_network_status error: {e}")
        return json.dumps({"error": str(e), "success": False})


# ---------------------------------------------------------------------------
# 2. FILE OPERATIONS & WORKSPACE MCP TOOLS
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="friday_read_file",
    description="Read text contents of a file on the local file system safely."
)
def read_file(file_path: str, max_lines: int = 1000) -> str:
    """Reads a file and returns its content."""
    try:
        path = Path(file_path)
        if not path.exists():
            return json.dumps({"error": f"File not found: {file_path}", "success": False})
        if not path.is_file():
            return json.dumps({"error": f"Path is not a file: {file_path}", "success": False})

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = [f.readline() for _ in range(max_lines)]
            content = "".join(lines)
        return json.dumps({
            "success": True,
            "file_path": str(path.resolve()),
            "total_lines_read": len(lines),
            "content": content
        }, indent=2)
    except Exception as e:
        logger.error(f"[MCP] read_file error: {e}")
        return json.dumps({"error": str(e), "success": False})


@mcp_server.tool(
    name="friday_write_file",
    description="Write text content to a file on the local file system (creates parent directories if needed)."
)
def write_file(file_path: str, content: str, overwrite: bool = True) -> str:
    """Writes content to a file."""
    try:
        path = Path(file_path)
        if path.exists() and not overwrite:
            return json.dumps({"error": f"File already exists and overwrite is False: {file_path}", "success": False})

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return json.dumps({
            "success": True,
            "file_path": str(path.resolve()),
            "bytes_written": len(content.encode("utf-8")),
            "message": f"File written successfully to {path.name}"
        }, indent=2)
    except Exception as e:
        logger.error(f"[MCP] write_file error: {e}")
        return json.dumps({"error": str(e), "success": False})


@mcp_server.tool(
    name="friday_list_directory",
    description="List files and subdirectories inside a directory on the local PC."
)
def list_directory(directory_path: str = ".") -> str:
    """Lists files and folders inside a given directory."""
    try:
        path = Path(directory_path)
        if not path.exists() or not path.is_dir():
            return json.dumps({"error": f"Directory not found: {directory_path}", "success": False})

        items = []
        for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            items.append({
                "name": child.name,
                "is_dir": child.is_dir(),
                "size_bytes": child.stat().st_size if child.is_file() else None
            })
        return json.dumps({
            "success": True,
            "directory": str(path.resolve()),
            "total_items": len(items),
            "items": items[:150]
        }, indent=2)
    except Exception as e:
        logger.error(f"[MCP] list_directory error: {e}")
        return json.dumps({"error": str(e), "success": False})


# ---------------------------------------------------------------------------
# 3. WEB SEARCH & ASSISTANT CAPABILITIES
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="friday_web_search",
    description="Perform a live web search to retrieve real-time facts, news, documentation, or technical information."
)
def web_search(query: str, max_results: int = 5) -> str:
    """Executes a web search query."""
    try:
        tool = tool_router.get_tool("web_search")
        if tool:
            res = tool.run(query=query, max_results=max_results)
            return json.dumps(res.data if res.success else {"error": res.error}, indent=2)
        return json.dumps({"error": "web_search tool is not registered", "success": False})
    except Exception as e:
        logger.error(f"[MCP] web_search error: {e}")
        return json.dumps({"error": str(e), "success": False})


@mcp_server.tool(
    name="friday_execute_registered_tool",
    description="Universal gateway to invoke any of Friday's 25+ internal assistant tools by name with custom arguments."
)
def execute_registered_tool(tool_name: str, arguments_json: str = "{}") -> str:
    """Invokes any tool registered in Friday's ToolRouter."""
    try:
        args = json.loads(arguments_json) if arguments_json else {}
        tool = tool_router.get_tool(tool_name)
        if not tool:
            available = [t.name for t in tool_router.list_tools()]
            return json.dumps({
                "error": f"Tool '{tool_name}' not found.",
                "available_tools": available,
                "success": False
            })

        res = tool_router.execute_tool(tool_name, args, session_id="mcp_client")
        return json.dumps({
            "success": res.success,
            "tool_name": tool_name,
            "data": res.data,
            "error": res.error,
            "metadata": res.metadata
        }, indent=2)
    except Exception as e:
        logger.error(f"[MCP] execute_registered_tool error: {e}")
        return json.dumps({"error": str(e), "success": False})


# ---------------------------------------------------------------------------
# 3.1 CODING AGENT MCP TOOLS (FABLE5 HERETIC CODING AGENT)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="friday_generate_code",
    description="Generate complete, bug-free, production-ready code with syntax verification using the Fable5 Heretic Coding Agent (saidutta69/lfm2.5-2.6b-fable5-coding-agent-heretic)."
)
async def mcp_generate_code(prompt: str, language: str = "python", context: str = "") -> str:
    """Generates complete, working code in the requested language."""
    from app.services.coding_agent_service import coding_agent_service
    res = await coding_agent_service.generate_code(prompt=prompt, language=language, context=context)
    return json.dumps(res, indent=2)


@mcp_server.tool(
    name="friday_debug_code",
    description="Analyze code for bugs, syntax errors, or logical flaws and output the 100% fixed code."
)
async def mcp_debug_code(code: str, error_message: str = "", language: str = "python") -> str:
    """Debugs code and returns complete fixed code."""
    from app.services.coding_agent_service import coding_agent_service
    res = await coding_agent_service.debug_code(code=code, error_message=error_message, language=language)
    return json.dumps(res, indent=2)


@mcp_server.tool(
    name="friday_refactor_code",
    description="Refactor code for performance, modularity, and clean architecture."
)
async def mcp_refactor_code(code: str, instructions: str, language: str = "python") -> str:
    """Refactors code based on instructions."""
    from app.services.coding_agent_service import coding_agent_service
    res = await coding_agent_service.refactor_code(code=code, instructions=instructions, language=language)
    return json.dumps(res, indent=2)


@mcp_server.tool(
    name="friday_explain_code",
    description="Provides structured step-by-step breakdown, architecture overview, and complexity analysis."
)
async def mcp_explain_code(code: str) -> str:
    """Explains code structure and functionality."""
    from app.services.coding_agent_service import coding_agent_service
    res = await coding_agent_service.explain_code(code=code)
    return json.dumps(res, indent=2)


# ---------------------------------------------------------------------------
# 4. MCP RESOURCES & PROMPTS
# ---------------------------------------------------------------------------

@mcp_server.resource(
    uri="friday://system/info",
    name="Friday System Specifications",
    description="Detailed hardware specifications and ground truth for this host machine (ASUS TUF Gaming A15)."
)
def get_system_spec_resource() -> str:
    """Returns static hardware specification document."""
    spec = {
        "model": "ASUS TUF Gaming A15 (FA506NC)",
        "cpu": "AMD Ryzen 5 7535HS (6 Cores / 12 Threads @ 3.30 GHz)",
        "ram": "16 GB DDR5 4800 MT/s",
        "gpus": [
            {"vendor": "NVIDIA", "name": "GeForce RTX 3050 Laptop GPU", "vram": "4096 MB GDDR6"},
            {"vendor": "AMD", "name": "Radeon(TM) Graphics", "vram": "512 MB Dedicated"}
        ],
        "os": "Windows 11 Home (64-bit)",
        "network": "Realtek 8852BE WiFi 6"
    }
    return json.dumps(spec, indent=2)


@mcp_server.prompt(
    name="friday_system_diagnostic",
    description="Generate a system diagnostic analysis prompt for the AI assistant."
)
def generate_diagnostic_prompt() -> str:
    return (
        "Please analyze the current Friday PC telemetry snapshot, verify CPU load, "
        "thermals for both RTX 3050 and AMD Radeon GPUs, and identify any active processes "
        "consuming abnormal resources."
    )


def get_mcp_tools_list() -> List[Dict[str, Any]]:
    """Helper to inspect all MCP tools registered on the server."""
    tools = []
    # Query tool manager in fastmcp
    tool_mgr = getattr(mcp_server, "_tool_manager", None)
    if tool_mgr:
        for name, t in getattr(tool_mgr, "_tools", {}).items():
            tools.append({
                "name": name,
                "description": getattr(t, "description", "") or "",
                "parameters": getattr(t, "parameters", {}) or {}
            })
    return tools
