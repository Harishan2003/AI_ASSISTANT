"""
Application management tools for Windows.
Enumerates installed applications via Windows Registry, launches apps, and terminates apps.
"""

import os
import subprocess
import winreg
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
import psutil


class ListInstalledAppsInput(BaseModel):
    query: Optional[str] = Field(default=None, description="Optional search filter for application name")
    limit: int = Field(default=100, description="Max number of installed apps to return")


class ListInstalledAppsTool(BaseTool):
    name: str = "list_installed_apps"
    description: str = "Lists applications installed on Windows by querying standard Registry keys (64-bit and 32-bit)."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = ListInstalledAppsInput

    def run(self, query: Optional[str] = None, limit: int = 100) -> ToolResult:
        apps = []
        seen = set()

        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for hkey, subkey_path in registry_paths:
            try:
                with winreg.OpenKey(hkey, subkey_path) as key:
                    num_subkeys = winreg.QueryInfoKey(key)[0]
                    for i in range(num_subkeys):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as app_key:
                                try:
                                    display_name = winreg.QueryValueEx(app_key, "DisplayName")[0]
                                except (FileNotFoundError, OSError):
                                    continue

                                if not display_name or display_name in seen:
                                    continue

                                try:
                                    version = winreg.QueryValueEx(app_key, "DisplayVersion")[0]
                                except (FileNotFoundError, OSError):
                                    version = None

                                try:
                                    publisher = winreg.QueryValueEx(app_key, "Publisher")[0]
                                except (FileNotFoundError, OSError):
                                    publisher = None

                                try:
                                    install_loc = winreg.QueryValueEx(app_key, "InstallLocation")[0]
                                except (FileNotFoundError, OSError):
                                    install_loc = None

                                try:
                                    uninstall_str = winreg.QueryValueEx(app_key, "UninstallString")[0]
                                except (FileNotFoundError, OSError):
                                    uninstall_str = None

                                if query and query.lower() not in display_name.lower():
                                    continue

                                seen.add(display_name)
                                apps.append({
                                    "name": display_name,
                                    "version": version,
                                    "publisher": publisher,
                                    "install_location": install_loc,
                                    "uninstall_string": uninstall_str
                                })
                                if len(apps) >= limit:
                                    break
                        except (PermissionError, OSError):
                            continue
            except (FileNotFoundError, PermissionError, OSError):
                continue

        apps.sort(key=lambda x: x["name"].lower())
        return ToolResult(
            tool_name=self.name,
            success=True,
            data={"total_found": len(apps), "apps": apps}
        )


class LaunchAppInput(BaseModel):
    app_name_or_path: str = Field(..., description="Application name (e.g. 'notepad', 'calc', 'chrome') or full path to executable")
    arguments: Optional[List[str]] = Field(default=None, description="Optional command-line arguments to pass to the application")


class LaunchAppTool(BaseTool):
    name: str = "launch_application"
    description: str = "Launches a Windows desktop application or process in the background."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = LaunchAppInput

    def run(self, app_name_or_path: str, arguments: Optional[List[str]] = None) -> ToolResult:
        try:
            # Common shortcuts
            known_apps = {
                "notepad": "notepad.exe",
                "calculator": "calc.exe",
                "calc": "calc.exe",
                "mspaint": "mspaint.exe",
                "paint": "mspaint.exe",
                "cmd": "cmd.exe",
                "powershell": "powershell.exe",
                "explorer": "explorer.exe",
                "taskmgr": "taskmgr.exe",
                "chrome": "chrome.exe",
                "firefox": "firefox.exe",
                "edge": "msedge.exe",
                "code": "code.cmd"
            }

            target = known_apps.get(app_name_or_path.lower(), app_name_or_path)
            cmd = [target]
            if arguments:
                cmd.extend(arguments)

            process = subprocess.Popen(
                cmd,
                shell=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "message": f"Successfully initiated launch of '{app_name_or_path}'",
                    "pid": process.pid,
                    "target": target
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Failed to launch '{app_name_or_path}': {str(e)}",
                error_code="APP_LAUNCH_FAILED"
            )


class CloseAppInput(BaseModel):
    app_name: str = Field(..., description="Application process name to close (e.g., 'notepad.exe', 'chrome.exe', 'Spotify.exe')")
    force: bool = Field(default=False, description="If true, forcefully terminates the process; otherwise requests graceful termination")


class CloseAppTool(BaseTool):
    name: str = "close_application"
    description: str = "Closes all instances of a running application by name. Requires human confirmation."
    permission_level: PermissionLevel = PermissionLevel.CONFIRM
    args_schema = CloseAppInput

    def run(self, app_name: str, force: bool = False) -> ToolResult:
        # Protected system processes
        protected = {
            "csrss.exe", "lsass.exe", "smss.exe", "wininit.exe", "services.exe",
            "svchost.exe", "dwm.exe", "explorer.exe", "system", "registry"
        }

        normalized = app_name.lower().strip()
        if not normalized.endswith(".exe"):
            normalized_with_exe = f"{normalized}.exe"
        else:
            normalized_with_exe = normalized

        if normalized in protected or normalized_with_exe in protected:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Refusing to terminate critical system process '{app_name}'",
                error_code="PROTECTED_PROCESS"
            )

        terminated_pids = []
        errors = []

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pname = (proc.info['name'] or '').lower()
                if pname == normalized or pname == normalized_with_exe or normalized in pname:
                    if force:
                        proc.kill()
                    else:
                        proc.terminate()
                    terminated_pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                errors.append(f"PID {proc.info.get('pid')}: {str(e)}")

        if not terminated_pids and not errors:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"No running instances found for application '{app_name}'",
                error_code="APP_NOT_RUNNING"
            )

        return ToolResult(
            tool_name=self.name,
            success=True,
            data={
                "app_name": app_name,
                "terminated_instances": len(terminated_pids),
                "terminated_pids": terminated_pids,
                "force": force,
                "errors": errors
            }
        )
