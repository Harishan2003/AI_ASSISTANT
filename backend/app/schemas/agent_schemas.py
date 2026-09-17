"""
Pydantic schemas for Friday AI PC Agent
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PermissionLevel(str, Enum):
    SAFE = "SAFE"
    CONFIRM = "CONFIRM"
    RESTRICTED = "RESTRICTED"


class ToolResult(BaseModel):
    tool_name: Optional[str] = None
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    code: Optional[str] = None
    requires_confirmation: bool = False
    confirmation_token: Optional[str] = None
    warning: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    name: str
    description: str
    permission_level: PermissionLevel
    parameters: Dict[str, Any]
    timeout_seconds: float = 30.0
    category: str = "general"


class AgentExecuteRequest(BaseModel):
    command: Optional[str] = Field(default=None, description="Natural language command from user")
    prompt: Optional[str] = Field(default=None, description="Alternative alias for command")
    session_id: Optional[str] = Field("default", description="Conversation session ID")
    language: Optional[str] = Field("english", description="Response language")
    auto_confirm: Optional[bool] = Field(False, description="Automatically confirm CONFIRM-level actions if pre-authorized")

    def get_query(self) -> str:
        return self.command or self.prompt or ""


class AgentConfirmRequest(BaseModel):
    confirmation_token: str = Field(..., description="Secure confirmation token provided by agent")
    approved: bool = Field(True, description="Whether the user approved or rejected the action")


class AgentResponse(BaseModel):
    success: bool = True
    response: str = ""
    content: Optional[str] = None
    tools_executed: List[Dict[str, Any]] = Field(default_factory=list)
    executed_tools: List[ToolResult] = Field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_token: Optional[str] = None
    pending_tool_name: Optional[str] = None
    pending_arguments: Optional[Dict[str, Any]] = None
    confirmation_details: Optional[Dict[str, Any]] = None
    execution_time_seconds: float = 0.0
    error: Optional[str] = None
    error_code: Optional[str] = None

    def __init__(self, **data: Any):
        if "content" in data and "response" not in data:
            data["response"] = data["content"]
        elif "response" in data and "content" not in data:
            data["content"] = data["response"]
        super().__init__(**data)


class AuditLogEntry(BaseModel):
    id: Optional[int] = None
    timestamp: str
    session_id: str
    user_request: str
    tool_name: str
    arguments: str
    permission_level: str
    status: str
    result_summary: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: float


class ScheduledTaskItem(BaseModel):
    id: str
    name: str
    action: str
    schedule_time: Optional[str] = None
    cron: Optional[str] = None
    status: str = "SCHEDULED"
    created_at: str
