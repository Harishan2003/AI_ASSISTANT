"""
Tests for Process and Application Management Tools.
"""

import os
import pytest
from app.tools.processes.process_ops import (
    ListProcessesTool,
    FindProcessByPortTool,
    TerminateProcessTool
)
from app.tools.applications.app_ops import ListInstalledAppsTool
from app.schemas.agent_schemas import PermissionLevel


def test_list_processes():
    tool = ListProcessesTool()
    res = tool.run(limit=20)
    assert res.success is True
    assert "processes" in res.data
    assert len(res.data["processes"]) > 0


def test_protected_process_termination():
    tool = TerminateProcessTool()
    assert tool.permission_level == PermissionLevel.CONFIRM

    # Attempting to terminate PID 0 or PID 4
    res = tool.run(pid=0)
    assert res.success is False
    assert res.error_code == "PROTECTED_PROCESS"

    res4 = tool.run(pid=4)
    assert res4.success is False
    assert res4.error_code == "PROTECTED_PROCESS"


def test_list_installed_apps():
    tool = ListInstalledAppsTool()
    res = tool.run(limit=10)
    assert res.success is True
    assert "apps" in res.data
    assert isinstance(res.data["apps"], list)
