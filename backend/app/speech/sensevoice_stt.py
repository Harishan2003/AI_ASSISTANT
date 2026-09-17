"""
Friday - Sherpa-ONNX SenseVoice-Small Speech-To-Text Engine
Robust Physical Microphone Capture
"""

from __future__ import annotations

import collections
import os
import re
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Tuple

import numpy as np
import pyaudio
import sherpa_onnx


BACKEND_DIR = Path(__file__).resolve().parents[2]
PRIMARY_MODEL_DIR = BACKEND_DIR / "models" / "sherpa" / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"


def find_valid_sensevoice_models() -> Tuple[Path, Path]:
    model = PRIMARY_MODEL_DIR / "model.int8.onnx"
    tokens = PRIMARY_MODEL_DIR / "tokens.txt"

    if model.exists() and tokens.exists() and model.stat().st_size > 1024:
        return model, tokens

    search_root = BACKEND_DIR / "models"
    if search_root.exists():
        for candidate_model in search_root.rglob("*sense*voice*.onnx"):
            if candidate_model.stat().st_size > 1024:
                candidate_tokens = list(candidate_model.parent.rglob("*tokens*.txt"))
                if candidate_tokens and candidate_tokens[0].stat().st_size > 1024:
                    return candidate_model, candidate_tokens[0]

        for candidate_model in search_root.rglob("model*.onnx"):
            if candidate_model.stat().st_size > 1024:
                candidate_tokens = list(candidate_model.parent.rglob("tokens.txt"))
                if candidate_tokens:
                    return candidate_model, candidate_tokens[0]

    return model, tokens


MODEL_PATH, TOKENS_PATH = find_valid_sensevoice_models()

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024

DEFAULT_MIC_INDEX = None
VAD_ENERGY_THRESHOLD = 25          # Sensitive threshold for reliable voice input
NATURAL_SILENCE_DURATION = 0.20
NUM_THREADS = 4


class SenseVoiceSTT:

    def __init__(
        self,
        input_device_index: Optional[int] = DEFAULT_MIC_INDEX,
        language: str = "en",  # Strictly force English
        use_itn: bool = True,
    ):
        print("\n" + "=" * 60)
        print("[SenseVoiceSTT] INITIALIZING MICROPHONE STT ENGINE")
        print("=" * 60)

        self.input_device_index = input_device_index
        self.language = language
        self.use_itn = use_itn
        self.recognizer = None
        self._pa = pyaudio.PyAudio()
        self._mic_lock = threading.Lock()

        self._check_model_files()
        self._init_recognizer()
        self._auto_detect_mic()
        print("[SenseVoiceSTT] READY\n")

    def _check_model_files(self):
        required = [MODEL_PATH, TOKENS_PATH]
        missing = [str(p) for p in required if not p.exists() or p.stat().st_size == 0]
        if missing:
            raise FileNotFoundError(f"SenseVoice model files missing: {missing}")

    def _auto_detect_mic(self):
        if self.input_device_index is not None:
            return

        try:
            default_index = None
            try:
                default_info = self._pa.get_default_input_device_info()
                default_index = default_info.get("index")
                print(f"[SenseVoiceSTT] Windows Default Mic: [{default_index}] {default_info.get('name')}")
            except Exception:
                pass

            count = self._pa.get_device_count()
            bad_keywords = ["stereo mix", "what u hear", "wave out", "cable", "virtual", "loopback", "aux"]

            for idx in range(count):
                try:
                    info = self._pa.get_device_info_by_index(idx)
                    name = info.get("name", "").lower()
                    max_in = int(info.get("maxInputChannels", 0))

                    if max_in > 0 and not any(bad in name for bad in bad_keywords):
                        if any(k in name for k in ["microphone", "array", "realtek", "headset", "usb audio"]):
                            self.input_device_index = idx
                            print(f"[SenseVoiceSTT] >>> Physical Mic Bound [{idx}]: {info.get('name')} <<<")
                            return
                except Exception:
                    pass

            self.input_device_index = default_index
            print(f"[SenseVoiceSTT] Using input device index: {self.input_device_index}")
        except Exception as e:
            print(f"[SenseVoiceSTT] Mic detection error: {e}")

    def set_capture_mode(self, mode: str):
        pass

    def _init_recognizer(self):
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(MODEL_PATH),
            tokens=str(TOKENS_PATH),
            language="en",  # Eliminates multi-language beam search latency
            use_itn=self.use_itn,
            num_threads=NUM_THREADS,
            provider="cpu",
        )

    def decode_raw_audio(self, raw_bytes: bytes) -> str:
        if not raw_bytes or len(raw_bytes) < 1600:
            return ""

        try:
            audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            max_val = np.max(np.abs(audio_np))
            if max_val > 0.01:
                audio_np = audio_np / max_val * 0.92

            stream = self.recognizer.create_stream()
            stream.accept_waveform(SAMPLE_RATE, audio_np)
            self.recognizer.decode_stream(stream)

            raw_text = stream.result.text.strip() if stream.result else ""
            cleaned = self._clean_transcript(raw_text)
            return self._apply_phonetic_fixes(cleaned)
        except Exception as e:
            return ""

    def listen_utterance(
        self,
        stop_check: Callable[[], bool],
        energy_threshold: int = VAD_ENERGY_THRESHOLD,
        silence_timeout: float = NATURAL_SILENCE_DURATION,
        max_duration: float = 12.0,
    ) -> str:
        with self._mic_lock:
            stream = None

            try:
                stream = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    input=True,
                    input_device_index=self.input_device_index,
                    frames_per_buffer=CHUNK,
                )

                time.sleep(0.04)
                try:
                    while True:
                        avail = stream.get_read_available()
                        if avail <= 0:
                            break
                        stream.read(avail, exception_on_overflow=False)
                except Exception:
                    pass

                pre_roll_chunks = int(SAMPLE_RATE / CHUNK * 0.15)
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
                        time.sleep(0.02)
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

                if not speech_started or not frames:
                    return ""

                return self.decode_raw_audio(b"".join(frames))

            except Exception as e:
                time.sleep(0.05)
                return ""
            finally:
                if stream is not None:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except Exception:
                        pass

    def scan_for_interrupt_sync(
        self,
        stop_check: Callable[[], bool],
    ) -> Optional[str]:
        if not self._mic_lock.acquire(blocking=False):
            return None

        stream = None

        try:
            stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=CHUNK,
            )

            chunk_size = int(SAMPLE_RATE / CHUNK * 0.20)
            trigger_patterns = [
                r"\bstop\b", r"\bcancel\b", r"\bfriday\b",
                r"\bfreddy\b", r"\bshut up\b", r"\bquiet\b",
                r"\bpause\b", r"\bwait\b", r"\bhold on\b",
                r"\benough\b", r"\bhalt\b", r"\bstop it\b",
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
                if rms < 20:
                    continue

                audio_np = samples.astype(np.float32) / 32768.0
                max_val = np.max(np.abs(audio_np))
                if max_val > 0.01:
                    audio_np = audio_np / max_val * 0.92

                stream_obj = self.recognizer.create_stream()
                stream_obj.accept_waveform(SAMPLE_RATE, audio_np)
                self.recognizer.decode_stream(stream_obj)

                text = stream_obj.result.text.strip().lower() if stream_obj.result else ""
                text = self._clean_transcript(text)
                text = self._apply_phonetic_fixes(text)

                if text:
                    for pattern in trigger_patterns:
                        if re.search(pattern, text.lower()):
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
            self._mic_lock.release()

        return None

    def _clean_transcript(self, text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r"<\|.*?\|>", "", text)
        cleaned = re.sub(r"<.*?>", "", cleaned)
        cleaned = re.sub(r"[^\x00-\x7F]+", "", cleaned)
        cleaned = re.sub(r"^[^\w\s]+|[^\w\s]+$", "", cleaned).strip()
        return " ".join(cleaned.split())

    def _apply_phonetic_fixes(self, text: str) -> str:
        if not text:
            return ""

        cleaned = text
        fixes = {
            r"\bg it\b": "Friday",
            r"\bfraeddale\b": "Friday",
            r"\bpen chme\b": "open chrome",
            r"\bchme\b": "chrome",
            r"\bro and chrome\b": "open chrome",
            r"\bma it\b": "Friday",
            r"\bsaidide\b": "Friday",
            r"\bfreday\b": "Friday",
            r"\bfreddy\b": "Friday",
            r"\bfriday friday\b": "Friday",
            r"\bopen ground\b": "open chrome",
            r"\bopen ch\b": "open chrome",
            r"\bch\b": "chrome",
            r"\bche\b": "chrome",
            r"\bwhat's up\b": "WhatsApp",
            r"\bwhatapps\b": "WhatsApp",
        }
        for pattern, replacement in fixes.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def shutdown(self):
        try:
            self._pa.terminate()
        except Exception:
            pass


sensevoice_stt = SenseVoiceSTT()