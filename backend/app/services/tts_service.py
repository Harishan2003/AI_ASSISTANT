"""
Friday AI Assistant - Multilingual Neural Text-To-Speech (TTS) Service
Provides high-fidelity, studio-quality speech synthesis for Tamil, Tanglish, and English
using Microsoft Edge Neural TTS with Voice Changer (Male & Female) and Low-Latency In-Memory Caching.
"""

from __future__ import annotations

import io
import re
import os
import asyncio
from typing import Optional, Dict

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    from gtts import gTTS
except ImportError:
    gTTS = None


class TTSService:
    """
    Synthesizes crystal-clear natural speech for Tamil, Tanglish, and English
    with selectable male and female voice profiles and microsecond in-memory caching.
    """

    VOICES: Dict[str, Dict[str, str]] = {
        "female": {
            "tamil": "ta-IN-PallaviNeural",
            "tanglish": "en-IN-NeerjaNeural",
            "english": "en-US-JennyNeural"
        },
        "male": {
            "tamil": "ta-IN-ValluvarNeural",
            "tanglish": "en-IN-PrabhatNeural",
            "english": "en-US-GuyNeural"
        }
    }

    def __init__(self):
        self._cache: Dict[str, bytes] = {}
        self._cache_max_size = 250

    @staticmethod
    def detect_language_type(text: str) -> str:
        """
        What does this function do:
        Detects whether input text contains Tamil Unicode script, Tanglish keywords, or English.
        """
        if re.search(r"[\u0B80-\u0BFF]", text):
            return "tamil"
        
        tanglish_keywords = (
            r"\b(vanakkam|nandri|epdi|eppadi|irukinga|irukeenga|irukken|irukku|"
            r"solunga|sollunga|pannunga|panren|panniten|romba|seri|theriyuma|kudunga|"
            r"enna|enga|yaar|ungalukku|enakku|tamil|tanglish|tamilnadu|illai|aama|illa|"
            r"machan|thala|bro|vaanga|ponga|sollu|theriyum|varaverpu|anbu|nanba|nanbargale|"
            r"amma|appa|anna|thambi|thangachi|akka)\b"
        )
        if re.search(tanglish_keywords, text, re.IGNORECASE):
            return "tanglish"
        
        return "english"

    async def synthesize(
        self,
        text: str,
        language: Optional[str] = None,
        gender: Optional[str] = "female",
        voice: Optional[str] = None
    ) -> bytes:
        """
        What does this function do:
        Synthesizes text into high quality MP3 audio bytes for playback in the web frontend,
        utilizing male/female voice selection and sub-millisecond LRU memory cache.

        Args:
            text (str): The clean text to synthesize.
            language (str, optional): Target language ('tamil', 'tanglish', 'english').
            gender (str, optional): 'female' or 'male'. Defaults to 'female'.
            voice (str, optional): Custom voice model ID override.

        Returns:
            bytes: MP3 audio file content.
        """
        clean_text = text.strip()
        if not clean_text:
            return b""

        # Detect language dynamically: force Tamil voice if Tamil script is present in text
        detected_lang = self.detect_language_type(clean_text)
        if detected_lang == "tamil":
            lang_type = "tamil"
        elif language and language.lower() in ["tamil", "tanglish", "english"]:
            lang_type = language.lower()
        else:
            lang_type = detected_lang
        gender_type = (gender or "female").lower()
        if gender_type not in ["male", "female"]:
            gender_type = "female"

        # Select appropriate neural voice model
        if not voice:
            voice_map = self.VOICES.get(gender_type, self.VOICES["female"])
            voice = voice_map.get(lang_type, voice_map["english"])

        # Cache key lookup for low-latency playback
        cache_key = f"{voice}:{clean_text}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Primary engine: Microsoft Edge Neural TTS
        if edge_tts:
            try:
                communicate = edge_tts.Communicate(clean_text, voice)
                audio_buffer = bytearray()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_buffer.extend(chunk["data"])
                if len(audio_buffer) > 0:
                    result_bytes = bytes(audio_buffer)
                    if len(self._cache) >= self._cache_max_size:
                        self._cache.pop(next(iter(self._cache)))
                    self._cache[cache_key] = result_bytes
                    return result_bytes
            except Exception as e:
                print(f"[TTSService] EdgeTTS error: {e}, falling back to gTTS...")

        # 2. Secondary fallback engine: gTTS (Google Translate TTS)
        if gTTS:
            try:
                gt_lang = "ta" if lang_type == "tamil" else "en"
                gt_tld = "co.in" if (lang_type in ["tamil", "tanglish"]) else "com"
                
                def _generate_gtts():
                    tts = gTTS(text=clean_text, lang=gt_lang, tld=gt_tld, slow=False)
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    fp.seek(0)
                    return fp.read()

                result_bytes = await asyncio.to_thread(_generate_gtts)
                if result_bytes:
                    if len(self._cache) >= self._cache_max_size:
                        self._cache.pop(next(iter(self._cache)))
                    self._cache[cache_key] = result_bytes
                return result_bytes
            except Exception as e:
                print(f"[TTSService] gTTS fallback error: {e}")

        return b""


tts_service = TTSService()
