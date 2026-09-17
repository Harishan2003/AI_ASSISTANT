from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatInput, ChatOutput
from app.services.chat_service import chat_service

from app.core.llm.models import (
    ChatMessage,
    ChatRequest,
    MessageRole,
)


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


# =====================================================
# NORMAL CHAT
# =====================================================

@router.post(
    "",
    response_model=ChatOutput,
)
async def chat(request: ChatInput):

    if not await chat_service.health():

        raise HTTPException(
            status_code=503,
            detail="LLM Provider Offline",
        )

    llm_request = ChatRequest(
        messages=[
            ChatMessage(
                role=MessageRole.USER,
                content=request.message,
            )
        ]
    )

    response = await chat_service.chat(
        llm_request
    )

    return ChatOutput(
        response=response.content
    )


# =====================================================
# STREAMING CHAT
# =====================================================

@router.post(
    "/stream"
)
async def stream_chat(request: ChatInput):

    if not await chat_service.health():

        raise HTTPException(
            status_code=503,
            detail="LLM Provider Offline",
        )

    llm_request = ChatRequest(
        messages=[
            ChatMessage(
                role=MessageRole.USER,
                content=request.message,
            )
        ],
        stream=True,
    )

    async def generator():

        async for token in chat_service.stream_chat(
            llm_request
        ):

            yield token

    return StreamingResponse(
        generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )