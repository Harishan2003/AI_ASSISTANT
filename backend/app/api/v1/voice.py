# Module: backend.app.api.v1.voice
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel

from app.services.tts_service import tts_service

logger = logging.getLogger("friday.api.voice")

router = APIRouter(
    prefix="/voice",
    tags=["Voice & TTS"],
)

# Global Voice State tracking
GLOBAL_VOICE_STATE: Dict[str, Any] = {
    "state": "idle",
    "is_listening": True,
    "is_thinking": False,
    "is_speaking": False,
}

USER_PROFILE_FILE = Path(__file__).resolve().parent.parent.parent.parent / "database" / "user_profile.json"


def get_default_voice_gender() -> str:
    if USER_PROFILE_FILE.exists():
        try:
            with open(USER_PROFILE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("voice_gender", "female")
        except Exception:
            pass
    return "female"


class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = None
    gender: Optional[str] = None
    voice: Optional[str] = None


class VoiceStateRequest(BaseModel):
    state: Optional[str] = "idle"
    is_speaking: Optional[bool] = False
    is_thinking: Optional[bool] = False
    is_listening: Optional[bool] = True


@router.get("/state", summary="Get current voice assistant state")
def get_voice_state():
    return {"status": "success", "state": GLOBAL_VOICE_STATE}


@router.post("/state", summary="Update voice assistant state")
def update_voice_state(req: VoiceStateRequest):
    GLOBAL_VOICE_STATE["state"] = req.state or "idle"
    if req.is_speaking is not None:
        GLOBAL_VOICE_STATE["is_speaking"] = req.is_speaking
    if req.is_thinking is not None:
        GLOBAL_VOICE_STATE["is_thinking"] = req.is_thinking
    if req.is_listening is not None:
        GLOBAL_VOICE_STATE["is_listening"] = req.is_listening
    return {"status": "success", "state": GLOBAL_VOICE_STATE}


@router.post("/stop", summary="Stop current voice playback and active actions")
def stop_voice():
    GLOBAL_VOICE_STATE["state"] = "idle"
    GLOBAL_VOICE_STATE["is_speaking"] = False
    GLOBAL_VOICE_STATE["is_thinking"] = False
    return {"status": "success", "message": "Voice synthesis halted"}


@router.get("/tts", summary="Neural Text-to-Speech audio stream")
async def tts_get(
    text: str,
    language: Optional[str] = None,
    gender: Optional[str] = None,
    voice: Optional[str] = None,
):
    """
    Streams synthesized neural speech MP3/WAV audio for real-time browser playback.
    """
    if not gender:
        gender = get_default_voice_gender()
    audio_bytes = await tts_service.synthesize(text, language=language, gender=gender, voice=voice)
    if not audio_bytes:
        return Response(content=b"", media_type="audio/mpeg", status_code=204)
    media_type = "audio/wav" if audio_bytes.startswith(b"RIFF") else "audio/mpeg"
    return Response(content=audio_bytes, media_type=media_type)


@router.post("/tts", summary="Neural Text-to-Speech audio stream (POST)")
async def tts_post(req: TTSRequest):
    """
    POST endpoint for streaming synthesized neural speech MP3/WAV audio.
    """
    gender = req.gender or get_default_voice_gender()
    audio_bytes = await tts_service.synthesize(req.text, language=req.language, gender=gender, voice=req.voice)
    if not audio_bytes:
        return Response(content=b"", media_type="audio/mpeg", status_code=204)
    media_type = "audio/wav" if audio_bytes.startswith(b"RIFF") else "audio/mpeg"
    return Response(content=audio_bytes, media_type=media_type)
