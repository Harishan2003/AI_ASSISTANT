"""
Friday - Sherpa-ONNX Speech-To-Text Engine
Production High-Accuracy Acoustic Normalization
"""

from __future__ import annotations

import collections
import os
import re
import time
from pathlib import Path
from typing import Callable, Optional, Tuple

import numpy as np
import pyaudio
import sherpa_onnx

# ============================================================
# MODEL PATH RESOLUTION
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]
PRIMARY_MODEL_DIR = BACKEND_DIR / "models" / "sherpa" / "sherpa-onnx-whisper-small"


def find_valid_sherpa_models() -> Tuple[Path, Path, Path]:
    enc = PRIMARY_MODEL_DIR / "small-encoder.int8.onnx"
    dec = PRIMARY_MODEL_DIR / "small-decoder.int8.onnx"
    tok = PRIMARY_MODEL_DIR / "small-tokens.txt"

    if enc.exists() and dec.exists() and tok.exists() and enc.stat().st_size > 1024:
        return enc, dec, tok

    search_root = BACKEND_DIR / "models"
    if search_root.exists():
        for candidate_enc in search_root.rglob("*encoder*.onnx"):
            if candidate_enc.stat().st_size > 1024:
                candidate_dir = candidate_enc.parent
                candidate_dec = list(candidate_dir.rglob("*decoder*.onnx"))
                candidate_tok = list(candidate_dir.rglob("*tokens*.txt"))
                if candidate_dec and candidate_tok and candidate_dec[0].stat().st_size > 1024:
                    return candidate_enc, candidate_dec[0], candidate_tok[0]

    return enc, dec, tok


ENCODER, DECODER, TOKENS = find_valid_sherpa_models()

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024

DEFAULT_MIC_INDEX = None
VAD_ENERGY_THRESHOLD = 120  # Raised to prevent background noise triggering
NATURAL_SILENCE_DURATION = 0.85  # Gives you time between words before stopping
NUM_THREADS = 4


# ============================================================
# STT CLASS
# ============================================================

class WhisperSTT:

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        input_device_index: Optional[int] = DEFAULT_MIC_INDEX,
    ):
        print("\n" + "=" * 60)
        print("[SherpaSTT] INITIALIZING PRODUCTION STT ENGINE")
        print("=" * 60)

        self.input_device_index = input_device_index
        self._recognizers = {}

        self._check_model_files()
        self._load_recognizer(language="en")

        self._auto_detect_mic()
        print("[SherpaSTT] READY\n")

    def _check_model_files(self):
        required = [ENCODER, DECODER, TOKENS]
        missing = [str(p) for p in required if not p.exists() or p.stat().st_size == 0]
        if missing:
            raise FileNotFoundError(f"Sherpa-ONNX model files missing: {missing}")

    def _auto_detect_mic(self):
        if self.input_device_index is not None:
            return

        audio = pyaudio.PyAudio()
        try:
            count = audio.get_device_count()
            found_mic = False
            for idx in range(count):
                try:
                    info = audio.get_device_info_by_index(idx)
                    name = info.get("name", "").lower()
                    if int(info.get("maxInputChannels", 0)) > 0:
                        if "microphone array" in name or "realtek" in name or "headset" in name:
                            self.input_device_index = idx
                            print(f"[SherpaSTT] >>> Selected Hardware Mic [{idx}]: {info.get('name')} <<<")
                            found_mic = True
                            break
                except Exception:
                    pass

            if not found_mic:
                self.input_device_index = None
                print("[SherpaSTT] Using Windows Default Audio Input Device")
        finally:
            audio.terminate()

    def _load_recognizer(self, language: str = "en"):
        key = language or "en"
        if key in self._recognizers:
            return self._recognizers[key]

        recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=str(ENCODER),
            decoder=str(DECODER),
            tokens=str(TOKENS),
            language=language,
            task="transcribe",
            num_threads=NUM_THREADS,
            provider="cpu",
            decoding_method="greedy_search",
        )
        self._recognizers[key] = recognizer
        return recognizer

    def decode_raw_audio(self, raw_bytes: bytes, language: str = "en") -> str:
        if not raw_bytes or len(raw_bytes) < 4800:
            return ""

        try:
            recognizer = self._load_recognizer(language)
            audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            # Safe Peak Normalization without over-amplifying low noise
            max_val = np.max(np.abs(audio_np))
            if max_val > 0.05:
                audio_np = audio_np / max_val * 0.90

            stream = recognizer.create_stream()
            stream.accept_waveform(SAMPLE_RATE, audio_np)
            recognizer.decode_stream(stream)

            text = stream.result.text.strip() if stream.result else ""
            text = " ".join(text.split())
            return self._apply_phonetic_fixes(text)
        except Exception as e:
            print(f"[SherpaSTT] Decode error: {e}")
            return ""

    def listen_utterance(
        self,
        stop_check: Callable[[], bool],
        energy_threshold: int = VAD_ENERGY_THRESHOLD,
        silence_timeout: float = NATURAL_SILENCE_DURATION,
        max_duration: float = 12.0,
    ) -> str:
        audio = pyaudio.PyAudio()
        stream = None

        try:
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=CHUNK,
            )

            try:
                avail = stream.get_read_available()
                if avail > 0:
                    stream.read(avail, exception_on_overflow=False)
            except Exception:
                pass

            pre_roll_chunks = int(SAMPLE_RATE / CHUNK * 0.6)
            pre_buffer = collections.deque(maxlen=pre_roll_chunks)

            frames = []
            speech_started = False
            last_voice_time = None
            start_time = time.monotonic()

            while not stop_check():
                if speech_started and (time.monotonic() - start_time >= max_duration):
                    break

                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                except Exception:
                    continue

                if not data:
                    continue

                samples = np.frombuffer(data, dtype=np.int16)
                if len(samples) == 0:
                    continue

                rms = int(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
                current_time = time.monotonic()

                if not speech_started:
                    pre_buffer.append(data)
                    if rms >= energy_threshold:
                        speech_started = True
                        last_voice_time = current_time
                        frames.extend(list(pre_buffer))
                        start_time = current_time
                else:
                    frames.append(data)
                    if rms >= energy_threshold:
                        last_voice_time = current_time
                    else:
                        if last_voice_time and (current_time - last_voice_time >= silence_timeout):
                            break

            if not frames:
                return ""

            return self.decode_raw_audio(b"".join(frames), language="en")

        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            audio.terminate()

    def scan_for_interrupt_sync(
        self,
        stop_check: Callable[[], bool],
    ) -> Optional[str]:
        audio = pyaudio.PyAudio()
        stream = None

        try:
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=CHUNK,
            )

            chunk_size = int(SAMPLE_RATE / CHUNK * 0.35)
            recognizer = self._load_recognizer("en")

            trigger_patterns = [
                r"\bstop\b",
                r"\bcancel\b",
                r"\bfriday\b",
                r"\bfreddy\b",
                r"\bshut up\b",
                r"\bpause\b",
                r"\bquit\b",
                r"\bwait\b",
            ]

            while not stop_check():
                frames = []
                for _ in range(chunk_size):
                    if stop_check():
                        break
                    try:
                        data = stream.read(CHUNK, exception_on_overflow=False)
                        if data:
                            frames.append(data)
                    except Exception:
                        continue

                if not frames or stop_check():
                    break

                raw_bytes = b"".join(frames)
                samples = np.frombuffer(raw_bytes, dtype=np.int16)

                rms = int(np.sqrt(np.mean(samples.astype(np.float32) ** 2))) if len(samples) > 0 else 0
                if rms < 350:
                    continue

                audio_np = samples.astype(np.float32) / 32768.0

                sherpa_stream = recognizer.create_stream()
                sherpa_stream.accept_waveform(SAMPLE_RATE, audio_np)
                recognizer.decode_stream(sherpa_stream)

                text = sherpa_stream.result.text.strip().lower() if sherpa_stream.result else ""

                if text:
                    for pattern in trigger_patterns:
                        if re.search(pattern, text):
                            return text

        except Exception:
            pass
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            audio.terminate()

        return None

    # ========================================================
    # COMPREHENSIVE PHONETIC NORMALIZATION
    # ========================================================

    def _apply_phonetic_fixes(self, text: str) -> str:
        if not text:
            return ""

        cleaned = text

        # 1. Hallucination removal
        noise_patterns = [
            r"\[music playing\]",
            r"\[music\]",
            r"\(upbeat music\)",
            r"\(electronic music\)",
            r"\(indistinct\)",
            r"\(static\)",
            r"\(applause\)",
            r"\(laughter\)",
            r"\(snoring\)",
            r"snoring",
            r"\[no",
        ]
        for pat in noise_patterns:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

        # 2. Command and Wake word mappings
        fixes = {
            r"\bwatch up\b": "WhatsApp",
            r"\bwatch app\b": "WhatsApp",
            r"\bwhats up\b": "WhatsApp",
            r"\bwhat's up\b": "WhatsApp",
            r"\bone whatsapp\b": "open WhatsApp",
            r"\bcall her knee\b": "call Harini",
            r"\bcall harani\b": "call Harini",
            r"\bfor ide\b": "Friday",
            r"\bfry day\b": "Friday",
            r"\bfreddy\b": "Friday",
        }
        for pattern, replacement in fixes.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        return cleaned.strip()


whisper_stt = WhisperSTT()