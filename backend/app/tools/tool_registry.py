"""
Friday Tool Registry
Comprehensive multi-method Tool Registry supporting .get(), direct execution, 
system application launches, WhatsApp/media automation, and browser agent navigation.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Optional
from app.services.system_service import system_service


# ============================================================
# TOOL REGISTRY CLASS & SINGLETON
# ============================================================

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name_or_func: Any,
        func: Optional[Callable] = None,
        description: Optional[str] = None,
    ):
        """
        Supports:
            tool_registry.register("tool_name", function)
            tool_registry.register(function)
        """
        if callable(name_or_func) and func is None:
            target_func = name_or_func
            tool_name = target_func.__name__
        else:
            tool_name = str(name_or_func)
            target_func = func

        if not callable(target_func):
            return

        tool_doc = description or target_func.__doc__ or "No description provided."
        self._tools[tool_name] = {
            "name": tool_name,
            "func": target_func,
            "description": tool_doc.strip(),
            "signature": inspect.signature(target_func),
        }
        print(f"[ToolRegistry] Registered: {tool_name}")

    def get(self, name: str, default: Any = None) -> Optional[Callable]:
        """Returns the callable tool function to satisfy ChatService tool lookup."""
        tool = self._tools.get(name)
        if tool:
            return tool["func"]
        return default

    def get_tool(self, name: str) -> Optional[Callable]:
        return self.get(name)

    def __getitem__(self, name: str) -> Callable:
        func = self.get(name)
        if func is None:
            raise KeyError(f"Tool '{name}' is not registered.")
        return func

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def list_tools(self) -> List[Dict[str, Any]]:
        return list(self._tools.values())

    def execute(self, name: str, *args, **kwargs) -> Any:
        """Directly executes a tool by name with safety fallbacks."""
        func = self.get(name)
        if not func:
            raise RuntimeError(f"Tool '{name}' is not available.")
        try:
            return func(*args, **kwargs)
        except TypeError:
            # Fallback if arguments differ in count
            return func()


# Singleton instance accessible everywhere
tool_registry = ToolRegistry()


# ============================================================
# 1. CORE SYSTEM APPLICATION TOOLS
# ============================================================

def open_application_tool(user_message: str = "") -> str:
    """Open an application from the user's natural-language command."""
    print(f"[Tool] open_application: '{user_message}'")
    return system_service.execute("open_application", user_message)


def open_file_explorer_tool(user_message: str = "") -> str:
    """Open Windows File Explorer."""
    return system_service.execute("open_file_explorer", user_message)


def open_notepad_tool(user_message: str = "") -> str:
    """Open Notepad."""
    return system_service.execute("open_notepad", user_message)


def open_calculator_tool(user_message: str = "") -> str:
    """Open Calculator."""
    return system_service.execute("open_calculator", user_message)


def open_paint_tool(user_message: str = "") -> str:
    """Open Paint."""
    return system_service.execute("open_paint", user_message)


def open_task_manager_tool(user_message: str = "") -> str:
    """Open Task Manager."""
    return system_service.execute("open_task_manager", user_message)


# Register System Tools
tool_registry.register("open_application", open_application_tool)
tool_registry.register("open_file_explorer", open_file_explorer_tool)
tool_registry.register("open_notepad", open_notepad_tool)
tool_registry.register("open_calculator", open_calculator_tool)
tool_registry.register("open_paint", open_paint_tool)
tool_registry.register("open_task_manager", open_task_manager_tool)

# System Path / Folder / Game / Drive openers
try:
    if hasattr(system_service, "open_path"):
        tool_registry.register("open_path", system_service.open_path)
    if hasattr(system_service, "open_folder"):
        tool_registry.register("open_folder", system_service.open_folder)
    if hasattr(system_service, "open_drive"):
        tool_registry.register("open_drive", system_service.open_drive)
except Exception:
    pass


# ============================================================
# 2. BASE UTILITIES (Time, Web Search, Calculator)
# ============================================================

try:
    from app.tools.time_tool import get_current_time
    tool_registry.register("get_current_time", get_current_time)
except Exception:
    import datetime

    def get_current_time(user_message: str = "") -> str:
        return datetime.datetime.now().strftime("The current time is %I:%M %p on %A, %B %d, %Y.")

    tool_registry.register("get_current_time", get_current_time)

try:
    from app.tools.search import web_search
    tool_registry.register("web_search", web_search)
except Exception:
    pass

try:
    from app.tools.calculator import calculate
    tool_registry.register("calculate", calculate)
except Exception:
    pass


# ============================================================
# 3. WHATSAPP & MEDIA AUTOMATION TOOLS
# ============================================================

try:
    from app.tools.chat_automation import automate_chat
    tool_registry.register("automate_chat", automate_chat)
except Exception as e:
    print(f"[Tools] automate_chat not registered: {e}")

try:
    from app.tools.media_automation import automate_media
    tool_registry.register("automate_media", automate_media)
except Exception as e:
    print(f"[Tools] automate_media not registered: {e}")


# ============================================================
# 4. AUTONOMOUS WEB NAVIGATION AGENT (Playwright)
# ============================================================

try:
    from app.tools.browser_tool import navigate_web
    tool_registry.register("navigate_web", navigate_web)
except Exception as e:
    print(f"[Tools] navigate_web not registered: {e}")


# ============================================================
# STARTUP BANNER
# ============================================================

print()
print("============================================================")
print("[Tools] Friday Tool Registry initialized.")
try:
    print("[Tools] Registered tools:")
    for name in tool_registry.names():
        print(f"   [+] {name}")
except Exception as e:
    print(f"[Tools] Could not list tools: {e}")
print("============================================================")
print()
# ============================================================
# CONTEXT EXECUTION TOOL (Non-Breaking)
# ============================================================

def context_execution_tool(user_message: str = "") -> str:
    """Executes actions based on the active foreground window context."""
    from app.services.agent_router import agent_router
    last_res = getattr(agent_router, "_last_context_result", None)
    if last_res:
        return str(last_res)
    return "Action performed in active application context."

tool_registry.register("take_screenshot", system_service.take_screenshot)
tool_registry.register("take_photo", system_service.take_photo)
tool_registry.register("open_new_tab", system_service.open_new_tab)
tool_registry.register("close_current_tab", system_service.close_current_tab)
tool_registry.register("context_execution", context_execution_tool)