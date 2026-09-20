"""
Permission Manager for Friday AI PC Agent.
Enforces SAFE, CONFIRM, and RESTRICTED security boundaries, generates cryptographic
confirmation tokens, and prevents unauthorized or destructive system operations.
"""
from __future__ import annotations

import datetime
import secrets
import time
from typing import Any, Dict, Optional, Tuple

from app.database.agent_db import agent_db
from app.schemas.agent_schemas import PermissionLevel, ToolResult


# System critical processes that can NEVER be terminated
PROTECTED_SYSTEM_PROCESSES = {
    "system", "system idle process", "smss.exe", "csrss.exe", "wininit.exe",
    "services.exe", "lsass.exe", "svchost.exe", "winlogon.exe", "dwm.exe",
    "explorer.exe", "spoolsv.exe", "registry", "memory compression"
}

# Strict destructive patterns that are RESTRICTED (cannot even be confirmed)
STRICT_RESTRICTED_PATTERNS = [
    "format c:", "format d:", "rmdir /s /q c:\\windows", "del /f /s /q c:\\windows",
    "vssadmin delete shadows", "bcdedit /set", "disable-windowsoptionalfeature",
    "set-mppreference -disablerealtimemonitoring $true", "reg delete hklm",
    "net user administrator", "mimikatz", "samdump2"
]


class PermissionManager:
    def __init__(self, token_ttl_seconds: float = 300.0):
        self.token_ttl_seconds = token_ttl_seconds
        self.db = agent_db

    def evaluate_action_permission(
        self,
        tool_name: str,
        declared_level: PermissionLevel,
        arguments: Dict[str, Any]
    ) -> Tuple[PermissionLevel, Optional[str]]:
        """
        Dynamically analyzes the requested tool call and arguments to determine
        the actual effective permission level (SAFE, CONFIRM, or RESTRICTED).
        """
        args_str = " ".join(str(v).lower() for v in arguments.values())

        # 1. Check for strictly restricted malicious / destructive actions
        for pattern in STRICT_RESTRICTED_PATTERNS:
            if pattern in args_str:
                return (
                    PermissionLevel.RESTRICTED,
                    f"Action matches critical security restriction pattern: '{pattern}'. Operation blocked."
                )

        # 2. Check process termination safety
        if tool_name in ("terminate_process", "kill_process", "force_close_application"):
            target_name = str(arguments.get("process_name") or arguments.get("name") or "").lower().strip()
            target_pid = arguments.get("pid")
            
            if target_name in PROTECTED_SYSTEM_PROCESSES:
                return (
                    PermissionLevel.RESTRICTED,
                    f"Process '{target_name}' is a critical Windows system process and cannot be terminated."
                )
            if target_pid in (0, 4):
                return (
                    PermissionLevel.RESTRICTED,
                    f"PID {target_pid} is a core Windows kernel/system process and cannot be terminated."
                )
            # All other terminations require human confirmation
            return PermissionLevel.CONFIRM, "Terminating running processes requires human confirmation."

        # 3. Check filesystem deletions & overwrites
        if tool_name in ("delete_file", "delete_folder", "delete_directory", "remove_file"):
            return PermissionLevel.CONFIRM, "Permanently deleting files/folders requires user confirmation."

        # 4. Check terminal / shell execution
        if tool_name in ("execute_terminal_command", "run_command", "execute_command"):
            cmd = str(arguments.get("command") or "").lower().strip()
            # Destructive triggers require confirmation
            destructive_triggers = [
                "del ", "rmdir ", "remove-item", "erase ", "drop ", "truncate ",
                "pip install", "npm install", "git reset --hard", "git clean -fd",
                "net stop", "sc delete", "taskkill", "attrib"
            ]
            if any(t in cmd for t in destructive_triggers):
                return PermissionLevel.CONFIRM, f"Command contains potentially modifying operations: '{cmd[:60]}...'"
            return PermissionLevel.SAFE, None

        # 5. Service stop / restart
        if tool_name in ("manage_service", "stop_service", "restart_service"):
            action = str(arguments.get("action") or "").lower()
            if action in ("stop", "restart", "disable"):
                return PermissionLevel.CONFIRM, f"Changing Windows service state requires confirmation."

        # 6. Device Control & External File Sending Actions
        if tool_name in ("drag_file_to_app", "send_file", "close_application"):
            return PermissionLevel.CONFIRM, f"Desktop action '{tool_name}' requires human confirmation before proceeding."

        return declared_level, None


    def create_confirmation_request(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        description: str = "",
        reason: Optional[str] = None
    ) -> str:
        """Generates a cryptographically secure token and stores the pending confirmation."""
        desc = reason or description or f"Confirmation requested for {tool_name}"
        token = "cnf_" + secrets.token_urlsafe(24)
        now = datetime.datetime.now().isoformat()
        expires_at = time.time() + self.token_ttl_seconds

        self.db.save_pending_confirmation(
            token=token,
            tool_name=tool_name,
            arguments=arguments,
            description=desc,
            created_at=now,
            expires_at=expires_at,
        )
        return token

    def validate_and_consume_token(
        self,
        token: str,
        approved: bool = True
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Validates confirmation token expiration and authorization."""
        pending = self.db.get_pending_confirmation(token)
        if not pending:
            return False, None, "Confirmation token not found or already consumed."

        if pending["status"] != "PENDING":
            return False, None, f"Confirmation token is already {pending['status']}."

        if time.time() > pending["expires_at"]:
            self.db.update_confirmation_status(token, "EXPIRED")
            return False, None, "Confirmation token has expired."

        if not approved:
            self.db.update_confirmation_status(token, "REJECTED")
            return False, pending, "User rejected the operation."

        self.db.update_confirmation_status(token, "APPROVED")
        return True, pending, None


permission_manager = PermissionManager()
