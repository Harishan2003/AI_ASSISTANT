"""
Controlled Terminal Execution Tools for Windows.
Executes shell commands (PowerShell / cmd) safely with timeout enforcement, output truncation, and safety guards.
"""

import os
import subprocess
import shlex
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult


class ExecuteCommandInput(BaseModel):
    command: str = Field(..., description="The command line to execute in PowerShell or cmd")
    shell_type: str = Field(default="powershell", description="Shell interpreter to use: 'powershell' or 'cmd'")
    working_dir: Optional[str] = Field(default=None, description="Working directory path for command execution")
    timeout_seconds: int = Field(default=30, ge=1, le=180, description="Max execution timeout in seconds (1 to 180)")


class ExecuteCommandTool(BaseTool):
    name: str = "execute_terminal_command"
    description: str = (
        "Executes a command line instruction on Windows using PowerShell or cmd. "
        "Guarded with timeouts and output truncation. Requires human confirmation."
    )
    permission_level: PermissionLevel = PermissionLevel.CONFIRM
    args_schema = ExecuteCommandInput

    # Explicitly forbidden commands that will never be executed
    FORBIDDEN_COMMANDS = [
        "format", "diskpart", "bcdedit", "vssadmin delete shadows",
        ":(){ :|:& };:", "del /f /s /q c:\\", "rmdir /s /q c:\\"
    ]

    def run(
        self,
        command: str,
        shell_type: str = "powershell",
        working_dir: Optional[str] = None,
        timeout_seconds: int = 30
    ) -> ToolResult:
        cmd_lower = command.lower()
        for forbidden in self.FORBIDDEN_COMMANDS:
            if forbidden in cmd_lower:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=f"Execution blocked: Command contains forbidden pattern '{forbidden}'",
                    error_code="FORBIDDEN_COMMAND"
                )

        cwd = working_dir if working_dir and os.path.isdir(working_dir) else os.getcwd()

        try:
            if shell_type.lower() == "cmd":
                args = ["cmd.exe", "/c", command]
            else:
                args = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command]

            process = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            stdout = process.stdout or ""
            stderr = process.stderr or ""

            # Truncate extremely long outputs
            max_chars = 10000
            stdout_truncated = len(stdout) > max_chars
            stderr_truncated = len(stderr) > max_chars

            if stdout_truncated:
                stdout = stdout[:max_chars] + f"\n... [Output truncated. Total characters: {len(process.stdout)}]"
            if stderr_truncated:
                stderr = stderr[:max_chars] + f"\n... [Stderr truncated. Total characters: {len(process.stderr)}]"

            return ToolResult(
                tool_name=self.name,
                success=(process.returncode == 0),
                data={
                    "command": command,
                    "shell_type": shell_type,
                    "working_dir": cwd,
                    "exit_code": process.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "stdout_truncated": stdout_truncated,
                    "stderr_truncated": stderr_truncated
                },
                error=stderr if process.returncode != 0 and stderr else None,
                error_code="COMMAND_FAILED" if process.returncode != 0 else None
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Command timed out after {timeout_seconds} seconds",
                error_code="COMMAND_TIMEOUT"
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Error executing command: {str(e)}",
                error_code="EXECUTION_ERROR"
            )
