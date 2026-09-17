"""
Audit Logger with automatic secret masking and persistent SQLite recording.
"""
from __future__ import annotations

import datetime
import re
from typing import Any, Dict, List, Optional
from app.database.agent_db import agent_db


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|auth|jwt|private[_-]?key)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"),
    re.compile(r"(gsk_[a-zA-Z0-9]{20,})"),
    re.compile(r"(tvly-[a-zA-Z0-9_\-]{20,})"),
    re.compile(r"(sk-[a-zA-Z0-9]{20,})"),
    re.compile(r"(bearer\s+[a-zA-Z0-9_\-\.]{20,})", re.IGNORECASE),
]


def sanitize_secrets(value: Any) -> Any:
    """Recursively masks sensitive tokens, passwords, and API keys."""
    if isinstance(value, str):
        sanitized = value
        for pattern in SECRET_PATTERNS:
            sanitized = pattern.sub(r"[REDACTED_SECRET]", sanitized)
        return sanitized
    elif isinstance(value, dict):
        clean_dict = {}
        for k, v in value.items():
            if any(s in str(k).lower() for s in ["password", "secret", "token", "api_key", "key"]):
                clean_dict[k] = "[REDACTED_SECRET]"
            else:
                clean_dict[k] = sanitize_secrets(v)
        return clean_dict
    elif isinstance(value, list):
        return [sanitize_secrets(item) for item in value]
    return value


class AuditLogger:
    def __init__(self):
        self.db = agent_db

    def log_execution(
        self,
        session_id: str = "default",
        user_request: str = "",
        tool_name: str = "",
        arguments: Optional[Dict[str, Any]] = None,
        permission_level: str = "SAFE",
        status: str = "SUCCESS",
        result_summary: Optional[str] = None,
        result_data: Optional[Any] = None,
        error: Optional[str] = None,
        execution_time_ms: float = 0.0,
        success: Optional[bool] = None
    ) -> int:
        if arguments is None:
            arguments = {}
        if result_data is not None and result_summary is None:
            result_summary = str(result_data)
        if success is not None:
            status = "SUCCESS" if success else "FAILED"

        clean_args = sanitize_secrets(arguments)
        clean_req = sanitize_secrets(user_request)
        clean_summary = sanitize_secrets(result_summary) if result_summary else None
        clean_err = sanitize_secrets(error) if error else None

        return self.db.add_audit_log(
            session_id=session_id,
            user_request=clean_req,
            tool_name=tool_name,
            arguments=clean_args,
            permission_level=permission_level,
            status=status,
            result_summary=clean_summary,
            error=clean_err,
            execution_time_ms=execution_time_ms
        )


audit_logger = AuditLogger()
