"""
Unit tests for Friday Neural TTS Service
Validates high-fidelity neural audio generation for Tamil, Tanglish, and English.
"""

import pytest
from app.services.tts_service import tts_service


@pytest.mark.anyio
async def test_language_detection():
    # Pure Tamil
    assert tts_service.detect_language_type("ஆம், நான் தமிழ் பேச முடியும்.") == "tamil"
    assert tts_service.detect_language_type("வணக்கம் ஹரிஷன்") == "tamil"
    
    # Tanglish
    assert tts_service.detect_language_type("vanakkam bro, eppadi irukinga") == "tanglish"
    assert tts_service.detect_language_type("Friday, solunga enna pannanum") == "tanglish"
    
    # English
    assert tts_service.detect_language_type("Hello Friday, what is the weather today?") == "english"


@pytest.mark.anyio
async def test_tts_synthesis_tamil():
    sample_tamil = "ஆம், நான் தமிழ் பேச முடியும்."
    audio_bytes = await tts_service.synthesize(sample_tamil, language="tamil")
    assert isinstance(audio_bytes, bytes)
    assert len(audio_bytes) > 0


@pytest.mark.anyio
async def test_tts_synthesis_tanglish():
    sample_tanglish = "Vanakkam boss, eppadi irukinga?"
    audio_bytes = await tts_service.synthesize(sample_tanglish, language="tanglish")
    assert isinstance(audio_bytes, bytes)
    assert len(audio_bytes) > 0
