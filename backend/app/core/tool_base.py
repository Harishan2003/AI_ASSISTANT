"""
BaseTool abstract class and standard result wrappers for Friday AI PC Agent.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
from typing import Any, Dict, Optional, Type, List
from pydantic import BaseModel

from app.schemas.agent_schemas import PermissionLevel, ToolDefinition, ToolResult


class BaseTool:
    """
    Base Tool for all PC Agent tools.
    Provides standardized metadata, schema extraction, permission checking,
    timeout handling, and both sync (run) and async (execute) execution interfaces.
    """

    name: str = ""
    description: str = ""
    permission_level: PermissionLevel = PermissionLevel.SAFE
    timeout_seconds: float = 30.0
    category: str = "general"
    args_schema: Optional[Type[BaseModel]] = None

    def __init__(self):
        if not self.name:
            self.name = self.__class__.__name__

    def run(self, **kwargs: Any) -> ToolResult:
        """Synchronous execution implementation. Automatically executes async execute() if needed."""
        # Check if execute method is overridden on child class
        execute_fn = getattr(self.__class__, "execute", None)
        if execute_fn is not None and execute_fn is not BaseTool.execute:
            if asyncio.iscoroutinefunction(execute_fn):
                try:
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = None

                    if loop is not None and loop.is_running():
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(lambda: asyncio.run(self.execute(**kwargs)))
                            return future.result()
                    else:
                        return asyncio.run(self.execute(**kwargs))
                except Exception as e:
                    return ToolResult(tool_name=self.name, success=False, error=str(e), error_code="EXECUTION_ERROR")
            else:
                return self.execute(**kwargs)

        raise NotImplementedError(f"Tool '{self.name}' must implement run() or execute().")

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Executes the tool asynchronously, delegating to run() by default."""
        run_fn = getattr(self.__class__, "run", None)
        if run_fn is not None and run_fn is not BaseTool.run:
            if asyncio.iscoroutinefunction(run_fn):
                return await self.run(**kwargs)
            return self.run(**kwargs)
        
        raise NotImplementedError(f"Tool '{self.name}' must implement run() or execute().")

    def get_parameters_schema(self) -> Dict[str, Any]:
        """Generates JSON schema for tool parameters."""
        if self.args_schema:
            schema = self.args_schema.model_json_schema()
            return {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
            }
        
        # Infer from run or execute method signature
        target_fn = self.execute if hasattr(self, "execute") and self.execute.__func__ is not BaseTool.execute else self.run
        sig = inspect.signature(target_fn)
        properties: Dict[str, Any] = {}
        required: list[str] = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "kwargs"):
                continue
            
            p_type = "string"
            if param.annotation is int:
                p_type = "integer"
            elif param.annotation is float:
                p_type = "number"
            elif param.annotation is bool:
                p_type = "boolean"
            elif param.annotation in (list, List):
                p_type = "array"
            elif param.annotation in (dict, Dict):
                p_type = "object"

            properties[param_name] = {
                "type": p_type,
                "description": f"Parameter {param_name}",
            }
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def to_tool_definition(self) -> ToolDefinition:
        """Converts to ToolDefinition schema."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            permission_level=self.permission_level,
            parameters=self.get_parameters_schema(),
            timeout_seconds=self.timeout_seconds,
            category=self.category,
        )

    def to_openai_schema(self) -> Dict[str, Any]:
        """Converts to OpenAI/Groq/Ollama function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters_schema(),
            }
        }
