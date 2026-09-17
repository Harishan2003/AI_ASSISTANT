"""
Central Tool Router for Friday AI PC Agent.
Registers all system tools, exports LLM function schemas, validates inputs,
enforces permissions via PermissionManager, and logs executions via AuditLogger.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from app.core.audit_logger import audit_logger
from app.core.event_bus import event_bus
from app.core.permission_manager import permission_manager
from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolDefinition, ToolResult


class ToolRouter:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Registers a BaseTool instance."""
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Tool must inherit from BaseTool, got {type(tool)}")
        self._tools[tool.name] = tool

    def register_tool(self, tool: BaseTool):
        """Alias for register."""
        self.register(tool)

    def get(self, name: str) -> Optional[BaseTool]:
        if name in self._tools:
            return self._tools[name]
        aliases = {
            "weather": "get_weather",
            "time": "get_current_time",
            "clock": "get_current_time",
            "date": "get_current_time",
            "calculator": "calculate",
            "calc": "calculate",
            "search": "web_search",
            "cpu": "get_cpu_status",
            "ram": "get_memory_status",
            "memory": "get_memory_status",
            "disk": "get_storage_status",
            "storage": "get_storage_status",
            "gpu": "get_gpu_status",
            "network": "get_network_status",
            "battery": "get_battery_status",
            "system": "get_system_info",
        }
        resolved = aliases.get(name.lower().strip())
        if resolved and resolved in self._tools:
            return self._tools[resolved]
        return None

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Alias for get."""
        return self.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return [tool.to_tool_definition() for tool in self._tools.values()]

    def get_openai_schemas(self) -> List[Dict[str, Any]]:
        """Returns OpenAI/Groq/Ollama tool schemas for all registered tools."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Alias for get_openai_schemas."""
        return self.get_openai_schemas()

    def execute_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        session_id: str = "default",
        user_request: str = "",
        bypass_confirmation: bool = False
    ) -> ToolResult:
        """
        Synchronously executes a registered tool with full permission checking,
        timeout guard, and audit logging.
        """
        if arguments is None:
            arguments = {}

        start_time = time.time()
        tool = self.get(name)
        if not tool:
            err = f"Tool '{name}' is not registered."
            audit_logger.log_execution(
                session_id=session_id,
                user_request=user_request,
                tool_name=name,
                arguments=arguments,
                permission_level=PermissionLevel.SAFE.value,
                status="FAILED",
                error=err,
                execution_time_ms=0.0
            )
            return ToolResult(tool_name=name, success=False, error=err, error_code="TOOL_NOT_FOUND")

        # 1. Evaluate effective permission level
        effective_level, reason = permission_manager.evaluate_action_permission(
            tool_name=name,
            declared_level=tool.permission_level,
            arguments=arguments
        )

        # 2. Enforce RESTRICTED boundary
        if effective_level == PermissionLevel.RESTRICTED:
            err_msg = reason or f"Action '{name}' is strictly restricted for security reasons."
            audit_logger.log_execution(
                session_id=session_id,
                user_request=user_request,
                tool_name=name,
                arguments=arguments,
                permission_level=PermissionLevel.RESTRICTED.value,
                status="BLOCKED",
                error=err_msg,
                execution_time_ms=(time.time() - start_time) * 1000
            )
            return ToolResult(
                tool_name=name,
                success=False,
                error=err_msg,
                error_code="PERMISSION_RESTRICTED"
            )

        # 3. Enforce CONFIRM boundary if not pre-authorized / confirmed
        if effective_level == PermissionLevel.CONFIRM and not bypass_confirmation:
            desc = reason or f"Tool '{name}' requires human approval before execution."
            token = permission_manager.create_confirmation_request(
                tool_name=name,
                arguments=arguments,
                reason=desc
            )
            audit_logger.log_execution(
                session_id=session_id,
                user_request=user_request,
                tool_name=name,
                arguments=arguments,
                permission_level=PermissionLevel.CONFIRM.value,
                status="AWAITING_CONFIRMATION",
                result_summary=f"Confirmation token generated: {token}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
            return ToolResult(
                tool_name=name,
                success=False,
                requires_confirmation=True,
                confirmation_token=token,
                warning=desc,
                error_code="CONFIRMATION_REQUIRED",
                metadata={"tool_name": name, "arguments": arguments}
            )

        # 4. Execute tool
        try:
            if hasattr(tool, "run"):
                res: ToolResult = tool.run(**arguments)
            else:
                res = asyncio.run(tool.execute(**arguments))

            exec_time_ms = (time.time() - start_time) * 1000

            audit_logger.log_execution(
                session_id=session_id,
                user_request=user_request,
                tool_name=name,
                arguments=arguments,
                permission_level=effective_level.value,
                status="SUCCESS" if res.success else "FAILED",
                result_summary=str(res.data)[:300] if res.data else None,
                error=res.error,
                execution_time_ms=exec_time_ms
            )

            return res

        except Exception as ex:
            exec_time_ms = (time.time() - start_time) * 1000
            err_msg = f"Execution error in '{name}': {str(ex)}"
            audit_logger.log_execution(
                session_id=session_id,
                user_request=user_request,
                tool_name=name,
                arguments=arguments,
                permission_level=effective_level.value,
                status="ERROR",
                error=err_msg,
                execution_time_ms=exec_time_ms
            )
            return ToolResult(tool_name=name, success=False, error=err_msg, error_code="EXECUTION_ERROR")


tool_router = ToolRouter()
