"""
Agent REST Endpoints for natural-language execution and confirmation workflows.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.schemas.agent_schemas import (
    AgentExecuteRequest,
    AgentConfirmRequest,
    AgentResponse
)
from app.core.agent import agent_engine
from app.core.tool_router import tool_router

router = APIRouter(prefix="/agent", tags=["Agent Execution"])


@router.post("/execute", response_model=AgentResponse)
def execute_agent_prompt(request: AgentExecuteRequest) -> AgentResponse:
    """Executes a natural-language task using the autonomous local agent."""
    return agent_engine.execute(request)


@router.post("/confirm", response_model=AgentResponse)
def confirm_agent_action(request: AgentConfirmRequest) -> AgentResponse:
    """Confirms or rejects a pending human-in-the-loop action."""
    return agent_engine.confirm(request)


@router.get("/status")
def get_agent_status() -> Dict[str, Any]:
    """Retrieves agent system status and tool registry details."""
    return {
        "status": "ready",
        "registered_tools_count": len(tool_router.list_tools()),
        "max_iterations": agent_engine.max_iterations
    }
