"""
Tests for Security, Permissions, Audit Logging, and Confirmation Workflows.
"""

import pytest
from app.core.permission_manager import permission_manager
from app.core.audit_logger import audit_logger
from app.database.agent_db import agent_db
from app.tools.terminal.terminal_ops import ExecuteCommandTool


def test_confirmation_token_lifecycle():
    tool_name = "delete_file"
    args = {"target_path": "C:\\temp\\some_file.txt", "permanent": True}
    token = permission_manager.create_confirmation_request(
        tool_name=tool_name,
        arguments=args,
        reason="Test confirmation"
    )
    assert token.startswith("cnf_")

    # Validate and consume token
    is_valid, pending_data, _ = permission_manager.validate_and_consume_token(token)
    assert is_valid is True
    assert pending_data["tool_name"] == tool_name
    assert pending_data["arguments"]["target_path"] == "C:\\temp\\some_file.txt"

    # Second consumption must fail (single-use)
    is_valid_second, _, _ = permission_manager.validate_and_consume_token(token)
    assert is_valid_second is False


def test_audit_secret_redaction():
    audit_logger.log_execution(
        tool_name="test_tool",
        arguments={"api_key": "gsk_1234567890abcdef1234567890abcdef", "password": "superSecretPassword123!"},
        result_data={"token": "sk-proj-999999999999999999999999"},
        execution_time_ms=12.5,
        success=True
    )

    logs = agent_db.get_audit_logs(limit=1, tool_name="test_tool")
    assert len(logs) == 1
    log = logs[0]
    assert log["arguments"]["api_key"] == "[REDACTED_SECRET]"
    assert log["arguments"]["password"] == "[REDACTED_SECRET]"


def test_terminal_forbidden_command():
    tool = ExecuteCommandTool()
    res = tool.run(command="format C: /fs:ntfs")
    assert res.success is False
    assert res.error_code == "FORBIDDEN_COMMAND"
