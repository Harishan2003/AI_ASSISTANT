# Module: backend.app.api.v1.conversations_api
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.conversation_memory_service import conversation_memory_service

logger = logging.getLogger("friday.api.conversations")

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


# --- REQUEST & RESPONSE SCHEMAS ---
class CreateConversationRequest(BaseModel):
    title: Optional[str] = None


class RenameConversationRequest(BaseModel):
    title: str


class AddMessageRequest(BaseModel):
    role: str
    content: str


# --- ENDPOINTS ---
@router.post("", summary="Create a new conversation session")
async def create_conversation_endpoint(req: Optional[CreateConversationRequest] = None):
    """
    Creates a new isolated conversation thread with sliding 24-hour retention window.
    """
    title = req.title if req and req.title else "New Session"
    conv = await conversation_memory_service.create_conversation(title=title)
    return {"status": "success", "conversation": conv}


@router.get("", summary="List all non-expired conversations")
async def list_conversations_endpoint():
    """
    Lists all non-expired conversations sorted chronologically by last updated timestamp.
    """
    convs = await conversation_memory_service.list_conversations()
    return {"status": "success", "conversations": convs}


@router.get("/{conversation_id}", summary="Retrieve conversation details and messages")
async def get_conversation_endpoint(conversation_id: str):
    """
    Retrieves complete metadata and messages for a specific conversation session.
    """
    conv = await conversation_memory_service.get_conversation(conversation_id)
    if not conv:
        return {"status": "error", "message": "Conversation not found or expired"}
    return {"status": "success", "conversation": conv}


@router.patch("/{conversation_id}", summary="Rename a conversation session")
async def rename_conversation_endpoint(conversation_id: str, req: RenameConversationRequest):
    """
    Renames the title of an existing conversation session.
    """
    success = await conversation_memory_service.rename_conversation(conversation_id, req.title)
    return {"status": "success" if success else "error"}


@router.delete("/{conversation_id}", summary="Permanently delete a conversation")
async def delete_conversation_endpoint(conversation_id: str):
    """
    Permanently deletes a conversation thread and its associated messages.
    """
    success = await conversation_memory_service.delete_conversation(conversation_id)
    return {"status": "success" if success else "error"}


@router.delete("/{conversation_id}/messages", summary="Clear all messages in a conversation")
async def clear_messages_endpoint(conversation_id: str):
    """
    Clears all messages within a conversation while retaining the session itself.
    """
    success = await conversation_memory_service.clear_messages(conversation_id)
    return {"status": "success" if success else "error"}


@router.get("/{conversation_id}/messages", summary="Get paginated messages for a conversation")
async def get_messages_endpoint(
    conversation_id: str,
    limit: int = 50,
    before_message_id: Optional[str] = None,
):
    """
    Fetches paginated messages from a conversation history.
    """
    messages = await conversation_memory_service.get_messages(
        conversation_id,
        limit=limit,
        before_message_id=before_message_id,
    )
    return {"status": "success", "messages": messages}


@router.post("/{conversation_id}/messages", summary="Add a user or assistant message to a conversation")
async def add_message_endpoint(conversation_id: str, req: AddMessageRequest):
    """
    Appends a new user or assistant message to a conversation session.
    """
    msg = await conversation_memory_service.add_message(conversation_id, req.role, req.content)
    return {"status": "success", "message": msg}


@router.post("/cleanup/expired", summary="Purge expired conversations")
async def cleanup_expired_conversations_endpoint():
    """
    Triggers cleanup of stale conversations that have exceeded their sliding retention window.
    """
    cleaned = conversation_memory_service.cleanup_expired_conversations()
    return {"status": "success", "cleaned_count": cleaned}
