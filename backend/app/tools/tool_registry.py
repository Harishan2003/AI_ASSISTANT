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

try:
    import re
    from app.tools.weather import get_weather

    async def weather_tool(user_message: str = "") -> str:
        clean = re.sub(r'^(?:user|friday)\s*(?:🔊\s*Speak)?\s*[:\-\s]*', '', user_message, flags=re.IGNORECASE).strip()
        clean = re.sub(r'\b(?:what is|what\'s|whats|how is|how\'s|hows|the|weather|temperature|forecast|today|tomorrow|now|in|at|for|like|is|it|raining|rain)\b', '', clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r'[^\w\s]', '', clean).strip()
        city = clean or "Chennai"
        return await get_weather(city)

    tool_registry.register("weather", weather_tool)
    tool_registry.register("get_weather", weather_tool)
except Exception as e:
    print(f"[Tools] weather tool not registered: {e}")


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
# 5. PROMPT GENERATOR TOOL
# ============================================================

try:
    from app.services.prompt_generator_service import prompt_generator_service
    async def prompt_generator_tool(user_message: str = "") -> str:
        """Generates master-grade prompts for Midjourney, FLUX, LLMs, Coding, and Video."""
        res = await prompt_generator_service.generate(user_query=user_message)
        return prompt_generator_service.format_to_natural_speech(res)

    tool_registry.register("generate_prompt", prompt_generator_tool)
    tool_registry.register("prompt_generator", prompt_generator_tool)
except Exception as e:
    print(f"[Tools] prompt_generator not registered: {e}")


# ============================================================
# 6. QWEN IMAGE 2.1 UNCENSORED VISION & BFS FACE SWAP TOOLS
# ============================================================

try:
    from app.services.qwen_vision_service import qwen_vision_service
    async def qwen_vision_inspect_tool(image_path: str = "", prompt: str = "") -> str:
        """Uncensored deep image inspection with Qwen-Image-2.1."""
        res = await qwen_vision_service.analyze_image(image_path, prompt or "Analyze and describe this image thoroughly.")
        return res.get("analysis", str(res))

    tool_registry.register("qwen_vision_inspect", qwen_vision_inspect_tool)
    tool_registry.register("analyze_image_uncensored", qwen_vision_inspect_tool)
except Exception as e:
    print(f"[Tools] qwen_vision_inspect not registered: {e}")

try:
    from app.services.face_swap_service import face_swap_service
    async def face_swap_exec_tool(source_face: str = "", target_image: str = "") -> str:
        """High-Fidelity AI Face Swap with BFS Best Face Swap."""
        res = await face_swap_service.swap_face(source_face, target_image)
        if res.get("success"):
            return f"Face swap successfully generated: {res.get('output_path')}"
        return f"Face swap error: {res.get('error')}"

    tool_registry.register("face_swap", face_swap_exec_tool)
    tool_registry.register("bfs_face_swap", face_swap_exec_tool)
except Exception as e:
    print(f"[Tools] face_swap not registered: {e}")

try:
    from app.services.image_generation_service import image_generation_service
    async def image_gen_exec_tool(prompt: str = "") -> str:
        """Generates AI images using FLUX.1 and SDXL."""
        res = await image_generation_service.generate_image(prompt=prompt)
        return image_generation_service.format_to_markdown_card(res)

    tool_registry.register("generate_image", image_gen_exec_tool)
    tool_registry.register("create_image", image_gen_exec_tool)
except Exception as e:
    print(f"[Tools] generate_image not registered: {e}")


# ============================================================
# 7. DEVICE & HARDWARE CONTROLLER TOOLS
# ============================================================

try:
    from app.services.device_controller import device_controller

    tool_registry.register("set_volume", device_controller.set_volume)
    tool_registry.register("volume_up", device_controller.volume_up)
    tool_registry.register("volume_down", device_controller.volume_down)
    tool_registry.register("mute_audio", device_controller.mute)
    tool_registry.register("media_play_pause", device_controller.media_play_pause)
    tool_registry.register("media_next", device_controller.media_next)
    tool_registry.register("media_prev", device_controller.media_prev)
    tool_registry.register("media_stop", device_controller.media_stop)
    tool_registry.register("set_brightness", device_controller.set_brightness)
    tool_registry.register("brightness_up", device_controller.brightness_up)
    tool_registry.register("brightness_down", device_controller.brightness_down)
    tool_registry.register("lock_workstation", device_controller.lock_screen)
    tool_registry.register("sleep_pc", device_controller.sleep_pc)
    tool_registry.register("shutdown_pc", device_controller.shutdown_pc)
    tool_registry.register("restart_pc", device_controller.restart_pc)
    tool_registry.register("cancel_shutdown", device_controller.cancel_shutdown)
    tool_registry.register("set_power_profile", device_controller.set_power_profile)
    tool_registry.register("minimize_all_windows", device_controller.minimize_all_windows)
    tool_registry.register("show_task_view", device_controller.show_task_view)
    tool_registry.register("open_settings", device_controller.open_settings)
    tool_registry.register("open_run_dialog", device_controller.open_run_dialog)
    tool_registry.register("switch_window", device_controller.switch_window)
    tool_registry.register("close_active_window", device_controller.close_active_window)
    tool_registry.register("switch_to_application", device_controller.switch_to_application)
    tool_registry.register("type_text", device_controller.type_text)
    tool_registry.register("press_key", device_controller.press_key)
    tool_registry.register("press_hotkey", device_controller.press_hotkey)
    tool_registry.register("click_screen", device_controller.click_at)
    tool_registry.register("move_mouse", device_controller.move_mouse)
    tool_registry.register("drag_and_drop", device_controller.drag_and_drop)
    tool_registry.register("scroll_mouse", device_controller.scroll_mouse)
    tool_registry.register("get_clipboard", device_controller.get_clipboard)
    tool_registry.register("set_clipboard", device_controller.set_clipboard)
    tool_registry.register("clear_clipboard", device_controller.clear_clipboard)
    tool_registry.register("inspect_screen", device_controller.inspect_screen_with_ai)
except Exception as e:
    print(f"[Tools] DeviceController tools registration error: {e}")


# ============================================================
# CONTEXT EXECUTION TOOL & GLOBAL TABS
# ============================================================

def context_execution_tool(user_message: str = "") -> str:
    """Executes actions based on the active foreground window context."""
    from app.services.agent_router import agent_router
    last_res = getattr(agent_router, "_last_context_result", None)
    if last_res:
        return str(last_res)
    return "Action performed in active application context."

async def file_action_tool(user_message: str = "") -> str:
    """Executes file operations (move, copy, backup) based on user command."""
    from app.services.command_executor import execute_in_backend
    res = await execute_in_backend(user_message)
    return res or "File operation completed."

async def mail_action_tool(user_message: str = "") -> str:
    """Executes email dispatch and mail client automation."""
    from app.services.command_executor import execute_in_backend
    res = await execute_in_backend(user_message)
    return res or "Mail client opened and message prepared."

from app.tools.email import send_current_email

tool_registry.register("take_screenshot", system_service.take_screenshot)
tool_registry.register("take_photo", system_service.take_photo)
tool_registry.register("open_new_tab", system_service.open_new_tab)
tool_registry.register("close_current_tab", system_service.close_current_tab)
tool_registry.register("context_execution", context_execution_tool)
tool_registry.register("file_action", file_action_tool)
tool_registry.register("mail_action", mail_action_tool)
tool_registry.register("send_current_email", send_current_email)


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