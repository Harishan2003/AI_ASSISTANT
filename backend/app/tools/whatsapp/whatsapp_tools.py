"""
WhatsApp Agent Tools for Friday AI Assistant.
Provides tool interfaces for sending WhatsApp messages, making voice/video calls, and toggling auto-monitoring.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.services.whatsapp_service import whatsapp_service


# -------------------------------------------------------------
# 1. SEND WHATSAPP MESSAGE TOOL
# -------------------------------------------------------------
class SendMessageInput(BaseModel):
    contact: str = Field(..., description="Name of the contact or group as saved in WhatsApp (e.g. 'John', 'Mom', 'Project Team').")
    message: str = Field(..., description="The text message content to send.")


class SendWhatsAppMessageTool(BaseTool):
    name: str = "send_whatsapp_message"
    description: str = "Sends a WhatsApp text message to any contact or group on WhatsApp Desktop."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    category: str = "communication"
    args_schema = SendMessageInput

    def run(self, contact: str, message: str, **kwargs: Any) -> ToolResult:
        contact_clean = contact.strip()
        msg_clean = message.strip()
        if not contact_clean or not msg_clean:
            return ToolResult(tool_name=self.name, success=False, error="Both contact name and message text are required.")

        res = whatsapp_service.send_message(contact_clean, msg_clean)
        if res.get("success"):
            return ToolResult(
                tool_name=self.name,
                success=True,
                data=res,
                metadata={"summary": f"Sent WhatsApp message to '{contact_clean}': \"{msg_clean}\""}
            )
        return ToolResult(tool_name=self.name, success=False, error=res.get("error", "Failed to send message."))


# -------------------------------------------------------------
# 2. START WHATSAPP CALL TOOL
# -------------------------------------------------------------
class StartCallInput(BaseModel):
    contact: str = Field(..., description="Name of the contact to call on WhatsApp.")
    call_type: str = Field(default="voice", description="'voice' for audio call or 'video' for video call.")


class StartWhatsAppCallTool(BaseTool):
    name: str = "start_whatsapp_call"
    description: str = "Initiates a voice or video call with a contact via WhatsApp Desktop."
    permission_level: PermissionLevel = PermissionLevel.CONFIRM
    category: str = "communication"
    args_schema = StartCallInput

    def run(self, contact: str, call_type: str = "voice", **kwargs: Any) -> ToolResult:
        contact_clean = contact.strip()
        if not contact_clean:
            return ToolResult(tool_name=self.name, success=False, error="Contact name is required.")

        res = whatsapp_service.start_call(contact_clean, call_type=call_type)
        if res.get("success"):
            return ToolResult(
                tool_name=self.name,
                success=True,
                data=res,
                metadata={"summary": f"Triggered {call_type} call to '{contact_clean}' on WhatsApp."}
            )
        return ToolResult(tool_name=self.name, success=False, error=res.get("error", "Failed to initiate call."))


# -------------------------------------------------------------
# 3. TOGGLE WHATSAPP MONITOR TOOL
# -------------------------------------------------------------
class ToggleMonitorInput(BaseModel):
    status: str = Field(..., description="'on' to enable WhatsApp toast notification monitoring & auto-replies, 'off' to disable.")
    auto_reply: bool = Field(default=True, description="Whether Friday should generate and send contextual AI replies to incoming messages.")


class ToggleWhatsAppMonitorTool(BaseTool):
    name: str = "toggle_whatsapp_monitor"
    description: str = "Turns WhatsApp background notification monitoring and AI auto-reply on or off."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    category: str = "communication"
    args_schema = ToggleMonitorInput

    def run(self, status: str, auto_reply: bool = True, **kwargs: Any) -> ToolResult:
        enable = status.strip().lower() in ["on", "true", "start", "enable", "active"]
        res = whatsapp_service.set_monitoring(enabled=enable, auto_reply=auto_reply)

        state_str = "ACTIVE" if res.get("monitoring_active") else "DISABLED"
        return ToolResult(
            tool_name=self.name,
            success=True,
            data=res,
            metadata={"summary": f"WhatsApp Background Monitor is now {state_str} (Auto-Reply: {res.get('auto_reply')})."}
        )


# -------------------------------------------------------------
# 4. GET WHATSAPP STATUS TOOL
# -------------------------------------------------------------
class GetWhatsAppStatusTool(BaseTool):
    name: str = "get_whatsapp_status"
    description: str = "Checks the current monitoring status, replied message count, and system readiness of the WhatsApp plugin."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    category: str = "communication"

    def run(self, **kwargs: Any) -> ToolResult:
        res = whatsapp_service.get_status()
        active = res.get("monitoring_active", False)
        count = res.get("replied_count", 0)
        return ToolResult(
            tool_name=self.name,
            success=True,
            data=res,
            metadata={"summary": f"WhatsApp Monitoring: {'ENABLED' if active else 'OFF'} | Replied: {count} messages"}
        )
