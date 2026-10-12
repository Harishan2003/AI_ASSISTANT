"""
Friday AI Assistant - Multilingual Neural Text-To-Speech (TTS) Service
Provides ultra-low latency, studio-quality speech synthesis for Tamil, Tanglish, and English
using Microsoft Edge Neural TTS, Windows Native SAPI5 Ultra-Fast Local Engine, and Memory Caching.
"""

from __future__ import annotations

import io
import re
import os
import wave
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
    with selectable male and female voice profiles and sub-millisecond in-memory caching.
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
        self._cache_max_size = 300

    @staticmethod
    def detect_language_type(text: str) -> str:
        """
        Detects whether input text contains Tamil Unicode script, Tanglish keywords, or English.
        """
        if re.search(r"[\u0B80-\u0BFF]", text):
            return "tamil"

        # Strong Tanglish phrases or multiple phonetic Tamil words in Latin script
        words = set(re.findall(r'\b[a-zA-Z]{3,}\b', text.lower()))
        tanglish_distinct = {
            "vanakkam", "nandri", "epdi", "eppadi", "irukinga", "irukeenga", "irukken",
            "solunga", "sollunga", "pannunga", "panren", "panniten", "pannanum", "pannalam",
            "theriyuma", "kudunga", "machan", "vaanga", "ponga", "varaverpu", "thambi",
            "thangachi", "panreenga", "seekiram", "seekram", "varuvaaru", "saptacha",
            "saptingala", "enna", "romba", "nalla", "illai"
        }
        matches = words.intersection(tanglish_distinct)
        if len(matches) >= 2 or any(w in words for w in ["vanakkam", "nandri", "irukeenga", "irukinga", "seekiram", "solunga", "sollunga", "pannanum"]):
            return "tanglish"

        return "english"

    @staticmethod
    def _clean_text_for_speech(text: str) -> str:
        """Strips markdown links, emojis, bolding, and code artifacts for smooth pronunciation."""
        if not text:
            return ""
        t = re.sub(r'```[\s\S]*?```', '', text)
        t = re.sub(r'`[^`]+`', '', t)
        t = re.sub(r'\[\[ACTION:[^\]]+\]\]', '', t)
        t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
        t = re.sub(r'\*\*([^*]+)\*\*', r'\1', t)
        t = re.sub(r'\*([^*]+)\*', r'\1', t)
        t = re.sub(r'[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF\U0001F600-\U0001F64F]', '', t)
        return re.sub(r'\s+', ' ', t).strip()

    @staticmethod
    def _generate_sapi5(text: str, gender: str = "female") -> bytes:
        """Ultra-fast (50-100ms) local Windows SAPI5 synthesizer producing valid WAV bytes."""
        if os.name != "nt":
            return b""
        try:
            import pythoncom
            pythoncom.CoInitialize()
            import win32com.client
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            stream = win32com.client.Dispatch("SAPI.SpMemoryStream")
            stream.Format.Type = 39  # SAFT22kHz16BitMono
            voice.AudioOutputStream = stream

            voices = voice.GetVoices()
            for i in range(voices.Count):
                v_desc = voices.Item(i).GetDescription().lower()
                if gender == "female" and ("zira" in v_desc or "female" in v_desc):
                    voice.Voice = voices.Item(i)
                    break
                elif gender == "male" and ("david" in v_desc or "male" in v_desc):
                    voice.Voice = voices.Item(i)
                    break

            voice.Speak(text)
            raw_pcm = bytes(stream.GetData())
            pythoncom.CoUninitialize()

            if not raw_pcm:
                return b""

            out = io.BytesIO()
            with wave.open(out, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(22050)
                w.writeframes(raw_pcm)
            return out.getvalue()
        except Exception:
            return b""

    async def synthesize(
        self,
        text: str,
        language: Optional[str] = None,
        gender: Optional[str] = "female",
        voice: Optional[str] = None
    ) -> bytes:
        """
        Synthesizes text into low-latency audio bytes.
        """
        clean_text = self._clean_text_for_speech(text)
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

        # Cache key lookup for instant sub-millisecond playback
        cache_key = f"{voice}:{clean_text}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Primary engine: Microsoft Edge Neural TTS with fast 3.0s timeout
        if edge_tts:
            try:
                async def _fetch_edge():
                    communicate = edge_tts.Communicate(clean_text, voice)
                    audio_buffer = bytearray()
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_buffer.extend(chunk["data"])
                    return bytes(audio_buffer) if len(audio_buffer) > 0 else b""

                result_bytes = await asyncio.wait_for(_fetch_edge(), timeout=3.0)
                if result_bytes:
                    if len(self._cache) >= self._cache_max_size:
                        self._cache.pop(next(iter(self._cache)))
                    self._cache[cache_key] = result_bytes
                    return result_bytes
            except Exception as e:
                print(f"[TTSService] EdgeTTS fast timeout/notice: {type(e).__name__}", flush=True)

        # 2. Instant Local Fallback: Windows SAPI5 (50ms ultra-low latency)
        if os.name == "nt" and lang_type in ["english", "tanglish"]:
            try:
                sapi_bytes = await asyncio.to_thread(self._generate_sapi5, clean_text, gender_type)
                if sapi_bytes:
                    if len(self._cache) >= self._cache_max_size:
                        self._cache.pop(next(iter(self._cache)))
                    self._cache[cache_key] = sapi_bytes
                    return sapi_bytes
            except Exception:
                pass

        # 3. Neural Fallback: gTTS with strict 2.5s timeout
        if gTTS:
            try:
                gt_lang = "ta" if lang_type == "tamil" else "en"
                gt_tld = "co.in" if (lang_type in ["tamil", "tanglish"]) else "us"
                def _fetch_gtts():
                    tts = gTTS(text=clean_text, lang=gt_lang, tld=gt_tld, slow=False)
                    buf = io.BytesIO()
                    tts.write_to_fp(buf)
                    return buf.getvalue()

                gtts_bytes = await asyncio.wait_for(asyncio.to_thread(_fetch_gtts), timeout=2.5)
                if gtts_bytes:
                    if len(self._cache) >= self._cache_max_size:
                        self._cache.pop(next(iter(self._cache)))
                    self._cache[cache_key] = gtts_bytes
                    return gtts_bytes
            except Exception as e:
                print(f"[TTSService] gTTS fallback notice: {e}", flush=True)

        return b""


tts_service = TTSService()
