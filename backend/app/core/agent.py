"""
Autonomous Local Windows AI Agent Engine.
Coordinates natural language understanding, persistent memory recall, tool routing, human-in-the-loop confirmation, and error recovery.
"""

import json
import logging
import os
import platform
from typing import Dict, Any, List, Optional

from app.core.tool_router import tool_router
import app.tools
from app.core.permission_manager import permission_manager
from app.database.agent_db import agent_db
from app.services.llm_service import llm_service
from app.schemas.agent_schemas import (
    PermissionLevel,
    ToolResult,
    AgentResponse,
    AgentExecuteRequest,
    AgentConfirmRequest
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_TEMPLATE = """You are Friday, an advanced, intelligent Windows 10/11 AI Command Agent and Automation Assistant built specifically for Harishan.
You run locally and have complete self-awareness of your identity, hardware environment, memory, and full tooling capabilities.

IDENTITY & PERSONA:
- Name: Friday (Female/Male AI companion, sharp, helpful, adaptive, and proactive).
- User: Harishan (Treat him as your creator/primary user with utmost respect and efficiency).
- Environment: Windows 10/11 Command Center HUD with local FastAPI backend and React frontend.

YOUR CAPABILITIES & TOOLING ARSENAL:
1. Real-Time Hardware & PC Monitoring:
   - CPU Status (`get_cpu_status`): CPU utilization, frequency, and core load.
   - RAM & Memory (`get_memory_status`): Real-time RAM used/free GB, utilization percentage, and clock speed (e.g. 4800 MT/s).
   - Storage & Drives (`get_storage_status`): Disk drive space (C:, D:, etc.), used/free GB, and health.
   - Dual GPU Telemetry (`get_gpu_status`): Dedicated NVIDIA GeForce RTX 3050 + Integrated AMD Radeon Graphics load %, core temps, VRAM usage, and drivers.
   - Network & Ports (`get_network_status`): Active adapters, Wi-Fi speed, upload/download rates, and open listening ports.
   - Battery & Power (`get_battery_status`): Battery percentage, charging state, and power profile.
   - System Info (`get_system_info`): Operating system build, architecture, hostname, and hardware specs.
   - Windows Services (`list_services`, `manage_service`): Inspect and control background Windows services.

2. Live Environment, Mathematics & Time:
   - Live Weather (`get_weather`): Real-time weather, temperature in Celsius, feels-like, humidity, wind, and sky conditions for any city worldwide via Open-Meteo.
   - Real-Time Clock & Dates (`get_current_time`): Exact current time, date, day of week, and timezone calculations for any region (default: Asia/Kolkata).
   - Calculator (`calculate`): High-precision mathematical expressions, arithmetic, formulas, and conversions.

3. Filesystem & Storage Operations:
   - File Search (`search_files`): Search files across directories by filename or wildcard pattern.
   - Content Search (`search_content`): Deep text/regex search within documents and code files.
   - File Reading & Writing (`read_text_file`, `write_text_file`): Inspect and create/update text files.
   - Folder Management (`create_folder`, `move_file`, `delete_file`): Manage files and directories on disk.
   - Duplicate Detection (`find_duplicate_files`): Fast SHA-256 duplicate file detection to reclaim disk space.

4. Process & Application Management:
   - Process Explorer (`list_processes`): List running processes, PIDs, CPU %, and memory footprint.
   - Port Lookup (`find_process_by_port`): Identify which process or service is listening on a network port.
   - Process Killer (`terminate_process`): Safely close or kill unresponsive programs (with protected OS boundaries).
   - Application Indexer (`list_installed_apps`): Discover installed desktop apps in Windows Registry and Start Menu.
   - App Launcher & Closer (`launch_app`, `close_app`): Launch programs (Chrome, VS Code, Notepad, Spotify, etc.) or close them.

5. Terminal & Desktop Automation:
   - Terminal Execution (`execute_command`): Run PowerShell or Command Prompt scripts safely.
   - Browser Automation (`browser_navigate`): Navigate and automate web tasks via Playwright browser.
   - Screen Capture (`take_screenshot`): Capture full desktop screenshots.
   - Display Geometry (`get_display_info`): Resolution, multi-monitor configuration, and DPI scale.
   - Clipboard Manager (`get_clipboard`, `set_clipboard`, `clear_clipboard`): Read, set, or wipe the Windows clipboard.
   - Toast Notifications (`show_notification`): Display native Windows Action Center notifications.
   - Task Scheduler (`create_scheduled_task`, `list_scheduled_tasks`, `cancel_scheduled_task`): Schedule reminders and automated tasks.
   - Web Search (`web_search`): Real-time live web search for facts, news, and technical documentation via Tavily.

6. Long-Term Memory & Context:
   - Fact Memory (`save_user_fact`, `recall_user_facts`): Store and retrieve Harishan's preferences, notes, and habits.
   - Persistent SQLite multi-conversation history.

SYSTEM CONTEXT:
Operating System: {os_info}
Current User: {user_name}
System Time: {current_time}

PERSISTENT USER MEMORIES & PREFERENCES:
{user_memories}

GUIDELINES:
1. Autonomously choose the right tool whenever Harishan asks for actions, diagnostics, weather, time, files, or information.
2. If Harishan asks who you are or what you can do, give an articulate, impressive, and structured overview of your identity and capabilities.
3. Keep summaries clean, professional, and conversational. Do not output raw unformatted arrays of numbers unless explicitly asked.
4. For dangerous operations (e.g. deleting files, terminating core processes), state what you are doing clearly.
"""


class AgentEngine:
    """Core autonomous agent executor."""

    def __init__(self, max_iterations: int = 6):
        self.max_iterations = max_iterations

    def _build_system_prompt(self) -> str:
        import datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_name = os.getenv("USERNAME", "User")
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"

        # Fetch recent user memories
        memories = agent_db.get_facts(limit=10)
        memory_str = "\n".join([f"- [{m.get('category', 'general')}] {m.get('fact')}" for m in memories]) if memories else "No stored memories yet."

        return SYSTEM_PROMPT_TEMPLATE.format(
            os_info=os_info,
            user_name=user_name,
            current_time=now_str,
            user_memories=memory_str
        )

    def execute(self, request: AgentExecuteRequest) -> AgentResponse:
        """Runs autonomous agent ReAct loop for a given prompt."""
        system_prompt = self._build_system_prompt()
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.get_query()}
        ]

        tools = tool_router.get_openai_tools()
        executed_tools_history: List[ToolResult] = []

        for iteration in range(self.max_iterations):
            try:
                llm_res = llm_service.chat_completion(
                    messages=messages,
                    tools=tools,
                    temperature=0.2
                )
            except Exception as e:
                logger.error(f"Agent LLM error: {e}")
                return AgentResponse(
                    content=f"Encountered an error while communicating with the AI model: {str(e)}",
                    success=False,
                    executed_tools=executed_tools_history,
                    error=str(e),
                    error_code="LLM_EXECUTION_ERROR"
                )

            assistant_content = llm_res.get("content") or ""
            tool_calls = llm_res.get("tool_calls") or []

            # If no tool calls were requested, return the final answer
            if not tool_calls:
                return AgentResponse(
                    content=assistant_content,
                    success=True,
                    executed_tools=executed_tools_history,
                    requires_confirmation=False
                )

            # Record assistant turn with tool calls
            messages.append({
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]) if isinstance(tc["arguments"], dict) else str(tc["arguments"])
                        }
                    }
                    for tc in tool_calls
                ]
            })

            # Process each requested tool call
            for tc in tool_calls:
                call_id = tc["id"]
                tool_name = tc["name"]
                tool_args = tc["arguments"]

                tool = tool_router.get_tool(tool_name)
                if not tool:
                    err_msg = f"Tool '{tool_name}' is not registered."
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps({"error": err_msg})
                    })
                    continue

                # Check permission level
                if tool.permission_level == PermissionLevel.CONFIRM:
                    # Require confirmation: create token and halt for human approval
                    token = permission_manager.create_confirmation_request(
                        tool_name=tool_name,
                        arguments=tool_args,
                        reason=f"Agent requested execution of sensitive tool '{tool_name}' with arguments: {tool_args}"
                    )
                    return AgentResponse(
                        content=assistant_content or f"I need your confirmation before executing `{tool_name}`.",
                        success=True,
                        requires_confirmation=True,
                        confirmation_token=token,
                        pending_tool_name=tool_name,
                        pending_arguments=tool_args,
                        executed_tools=executed_tools_history
                    )

                # Tool is SAFE: execute synchronously
                result = tool_router.execute_tool(tool_name, tool_args)
                executed_tools_history.append(result)

                # Format content for next LLM iteration
                result_payload = result.data if result.success else {"error": result.error, "error_code": result.error_code}
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(result_payload, default=str)
                })

        # Completed max iterations
        return AgentResponse(
            content=messages[-1].get("content", "Task processing completed."),
            success=True,
            executed_tools=executed_tools_history,
            requires_confirmation=False
        )

    def confirm(self, request: AgentConfirmRequest) -> AgentResponse:
        """Processes a human confirmation response."""
        is_valid, pending_data = permission_manager.validate_and_consume_token(request.confirmation_token)
        if not is_valid or not pending_data:
            return AgentResponse(
                content="The confirmation token is invalid, has expired, or has already been used.",
                success=False,
                error="Invalid confirmation token",
                error_code="INVALID_CONFIRMATION_TOKEN"
            )

        tool_name = pending_data["tool_name"]
        arguments = pending_data["arguments"]

        if not request.approved:
            return AgentResponse(
                content=f"Operation `{tool_name}` was cancelled by user.",
                success=True,
                requires_confirmation=False
            )

        # User approved: execute the tool
        result = tool_router.execute_tool(tool_name, arguments)
        executed_tools = [result]

        # Summarize with LLM
        summary_prompt = (
            f"The user approved the operation `{tool_name}` with arguments `{arguments}`. "
            f"Execution result: {json.dumps(result.data if result.success else {'error': result.error}, default=str)}. "
            f"Please provide a concise confirmation response to the user."
        )

        try:
            llm_res = llm_service.chat_completion(
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.2
            )
            response_text = llm_res.get("content", f"Successfully executed `{tool_name}`.")
        except Exception:
            response_text = f"Operation `{tool_name}` completed with status: {'Success' if result.success else 'Failed'}."

        return AgentResponse(
            content=response_text,
            success=result.success,
            executed_tools=executed_tools,
            error=result.error if not result.success else None,
            error_code=result.error_code if not result.success else None
        )


agent_engine = AgentEngine()
