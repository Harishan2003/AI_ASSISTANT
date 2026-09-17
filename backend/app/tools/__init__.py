"""
Friday AI Assistant - Central Tool Registry.
Registers all system, file, process, application, browser, terminal, screenshot, clipboard, notification, scheduler, web, and memory tools with the ToolRouter.
"""

from app.core.tool_router import tool_router

# System tools
from app.tools.system.cpu import CPUStatusTool
from app.tools.system.gpu import GPUStatusTool
from app.tools.system.memory import MemoryStatusTool
from app.tools.system.disk import StorageStatusTool
from app.tools.system.network import NetworkStatusTool
from app.tools.system.battery import BatteryStatusTool
from app.tools.system.system_info import SystemInfoTool
from app.tools.system.services import ListServicesTool, ManageServiceTool

# Filesystem tools
from app.tools.filesystem.file_ops import (
    ListFilesTool,
    SearchFilesTool,
    SearchContentTool,
    ReadTextFileTool,
    WriteTextFileTool,
    CreateFolderTool,
    MoveFileTool,
    DeleteFileTool,
    FindDuplicateFilesTool
)

# Process tools
from app.tools.processes.process_ops import (
    ListProcessesTool,
    FindProcessByPortTool,
    TerminateProcessTool
)

# Application tools
from app.tools.applications.app_ops import (
    ListInstalledAppsTool,
    LaunchAppTool,
    CloseAppTool
)

# Terminal tools
from app.tools.terminal.terminal_ops import ExecuteCommandTool

# Browser tools
from app.tools.browser.playwright_browser import BrowserNavigateTool

# Screen & Display tools
from app.tools.screenshot.screen_ops import (
    TakeScreenshotTool,
    GetDisplayInfoTool
)

# Clipboard tools
from app.tools.clipboard.clipboard_ops import (
    GetClipboardTool,
    SetClipboardTool,
    ClearClipboardTool
)

# Notification tools
from app.tools.notifications.notification_ops import ShowNotificationTool

# Task Scheduler tools
from app.tools.scheduler.scheduler_ops import (
    CreateScheduledTaskTool,
    ListScheduledTasksTool,
    CancelScheduledTaskTool
)

# Web Search tools
from app.tools.web.tavily_search import TavilyWebSearchTool

# Environment, Calculator & Time tools
from app.tools.weather import GetWeatherTool
from app.tools.calculator import CalculatorTool
from app.tools.time_tool import CurrentTimeTool

# WhatsApp Communication tools
from app.tools.whatsapp import (
    SendWhatsAppMessageTool,
    StartWhatsAppCallTool,
    ToggleWhatsAppMonitorTool,
    GetWhatsAppStatusTool
)

# Memory tools
from app.tools.memory.memory_tool import (
    SaveUserFactTool,
    RecallUserFactsTool
)


def register_all_tools():
    """Initializes and registers all tools with the global ToolRouter."""
    tools = [
        # System
        CPUStatusTool(),
        GPUStatusTool(),
        MemoryStatusTool(),
        StorageStatusTool(),
        NetworkStatusTool(),
        BatteryStatusTool(),
        SystemInfoTool(),
        ListServicesTool(),
        ManageServiceTool(),

        # Filesystem
        ListFilesTool(),
        SearchFilesTool(),
        SearchContentTool(),
        ReadTextFileTool(),
        WriteTextFileTool(),
        CreateFolderTool(),
        MoveFileTool(),
        DeleteFileTool(),
        FindDuplicateFilesTool(),

        # Processes
        ListProcessesTool(),
        FindProcessByPortTool(),
        TerminateProcessTool(),

        # Applications
        ListInstalledAppsTool(),
        LaunchAppTool(),
        CloseAppTool(),

        # Terminal
        ExecuteCommandTool(),

        # Browser
        BrowserNavigateTool(),

        # Screen
        TakeScreenshotTool(),
        GetDisplayInfoTool(),

        # Clipboard
        GetClipboardTool(),
        SetClipboardTool(),
        ClearClipboardTool(),

        # Notifications
        ShowNotificationTool(),

        # Scheduler
        CreateScheduledTaskTool(),
        ListScheduledTasksTool(),
        CancelScheduledTaskTool(),

        # Web & External Information
        TavilyWebSearchTool(),
        GetWeatherTool(),
        CalculatorTool(),
        CurrentTimeTool(),

        # WhatsApp Integration
        SendWhatsAppMessageTool(),
        StartWhatsAppCallTool(),
        ToggleWhatsAppMonitorTool(),
        GetWhatsAppStatusTool(),

        # Memory
        SaveUserFactTool(),
        RecallUserFactsTool(),
    ]

    for t in tools:
        tool_router.register_tool(t)

    return len(tools)


# Auto-register all tools on load
register_all_tools()