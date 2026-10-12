"""
FastAPI Route for Prompt Generation & Engineering.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.prompt_generator_service import prompt_generator_service

router = APIRouter(prefix="/prompt", tags=["Prompt Generator"])


class PromptGenerateRequest(BaseModel):
    topic: str
    target_type: Optional[str] = None  # 'image', 'code', 'llm', 'video', 'general'
    style: Optional[str] = "cinematic"


@router.post("/generate")
async def generate_prompt_endpoint(req: PromptGenerateRequest):
    """
    Generates production-grade master prompts for Midjourney, FLUX, LLMs, Coding, and Video.
    """
    res = await prompt_generator_service.generate(
        user_query=req.topic,
        target_type=req.target_type,
        style=req.style or "cinematic"
    )
    formatted = prompt_generator_service.format_to_natural_speech(res)
    return {
        "success": True,
        "data": res,
        "formatted_text": formatted
    }
