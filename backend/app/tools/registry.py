# Module: backend.app.tools.registry
"""
AI Assistant Tool Registry
"""

from typing import Callable, Dict


class ToolRegistry:

    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str, function: Callable):
        self._tools[name] = function

    def get(self, name: str):
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self):
        return list(self._tools.keys())


# Global registry
tool_registry = ToolRegistry()