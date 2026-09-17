"""
Tests for Agent Engine and Multi-Tool Execution Loop.
"""

from unittest.mock import MagicMock, patch
import pytest
from app.core.agent import agent_engine
from app.services.llm_service import llm_service
from app.schemas.agent_schemas import AgentExecuteRequest, AgentConfirmRequest
from app.tools import register_all_tools


@pytest.fixture(autouse=True)
def setup_tools():
    register_all_tools()


def test_agent_direct_response():
    with patch.object(llm_service, "chat_completion") as mock_chat:
        mock_chat.return_value = {
            "content": "Hello! I am Friday, your local Windows AI assistant.",
            "tool_calls": []
        }

        req = AgentExecuteRequest(command="Hello Friday")
        resp = agent_engine.execute(req)

        assert resp.success is True
        assert "Friday" in resp.response
        assert resp.requires_confirmation is False


def test_agent_safe_tool_execution():
    with patch.object(llm_service, "chat_completion") as mock_chat:
        mock_chat.side_effect = [
            {
                "content": "Checking CPU status...",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "name": "get_cpu_status",
                        "arguments": {"include_top_processes": False}
                    }
                ]
            },
            {
                "content": "Your current CPU usage is 15%.",
                "tool_calls": []
            }
        ]

        req = AgentExecuteRequest(command="How much CPU am I using?")
        resp = agent_engine.execute(req)

        assert resp.success is True
        assert len(resp.executed_tools) == 1
        assert "15%" in resp.response


def test_agent_confirm_sensitive_tool():
    with patch.object(llm_service, "chat_completion") as mock_chat:
        mock_chat.return_value = {
            "content": "I am about to delete the file for you.",
            "tool_calls": [
                {
                    "id": "call_del",
                    "name": "delete_file",
                    "arguments": {"path": "C:\\temp\\junk.tmp"}
                }
            ]
        }

        req = AgentExecuteRequest(command="Delete C:\\temp\\junk.tmp")
        resp = agent_engine.execute(req)

        assert resp.requires_confirmation is True
        assert resp.confirmation_token is not None
        assert resp.pending_tool_name == "delete_file"
