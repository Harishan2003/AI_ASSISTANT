"""
Friday - Direct Low-Latency Windows Piper TTS Engine
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import threading
import time
import wave
from pathlib import Path
from typing import Optional

import pyaudio


BACKEND_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = BACKEND_DIR / "models" / "piper" / "en_US-lessac-medium.onnx"
CONFIG_PATH = BACKEND_DIR / "models" / "piper" / "en_US-lessac-medium.onnx.json"


class PiperTTS:

    def __init__(self):
        self._pa = pyaudio.PyAudio()
        self.sample_rate = 22050
        self.is_speaking = False
        self.last_spoken_text = ""
        self.last_speech_time = 0.0
        self._lock = threading.Lock()
        
        # Start persistent worker process once at startup
        cmd = [
            "piper",
            "--model", str(MODEL_PATH),
            "--config", str(CONFIG_PATH),
            "--output-raw",
        ]
        if shutil.which("piper") is None:
            cmd = ["python", "-m", "piper", "--model", str(MODEL_PATH), "--config", str(CONFIG_PATH), "--output-raw"]
            
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0
        )

    def speak(self, text: str, lang: str = "en"):
        if not text or not text.strip():
            return
            
        with self._lock:
            self.is_speaking = True
            self.last_spoken_text = text
            try:
                # Write one line to the persistent process
                clean_text = text.replace("\n", " ").strip() + "\n"
                self.proc.stdin.write(clean_text.encode("utf-8"))
                self.proc.stdin.flush()

                stream = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.sample_rate,
                    output=True,
                )

                # Read raw PCM bytes directly as they are generated
                # Lessac model outputs 22050 samples/sec (44100 bytes/sec)
                chunk_size = 2048
                while True:
                    data = self.proc.stdout.read(chunk_size)
                    if not data:
                        break
                    stream.write(data)
                    if len(data) < chunk_size:
                        break

                stream.stop_stream()
                stream.close()
            except Exception as e:
                print(f"[PiperTTS] Error: {e}")
            finally:
                self.is_speaking = False
                self.last_speech_time = time.monotonic()

    def _check_environment(self):
        if not MODEL_PATH.exists():
            print(f"[PiperTTS] Warning: Model file not found at {MODEL_PATH}")
        else:
            try:
                self._pa = pyaudio.PyAudio()
                print("[PiperTTS] Initialized direct Piper speech engine.")
            except Exception as e:
                print(f"[PiperTTS] PyAudio init error: {e}")

    def speak(self, text: str, lang: str = "en"):
        if not text or not text.strip():
            return

        with self._lock:
            self._stop_requested = False
            self.is_speaking = True
            self.last_spoken_text = text

            stream = None
            try:
                # Run piper directly to generate standard WAV bytes with valid headers
                cmd = [
                    "piper",
                    "--model", str(MODEL_PATH),
                    "--config", str(CONFIG_PATH),
                    "--output-raw",
                ]

                # Fallback to python -m piper if standalone binary is not in PATH
                use_python_module = shutil.which("piper") is None
                if use_python_module:
                    cmd = [
                        "python", "-m", "piper",
                        "--model", str(MODEL_PATH),
                        "--config", str(CONFIG_PATH),
                        "--output-raw",
                    ]

                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )

                raw_pcm, _ = process.communicate(input=text.encode("utf-8"))

                if not raw_pcm or len(raw_pcm) == 0:
                    return

                if self._pa is None:
                    self._pa = pyaudio.PyAudio()

                # Open 16-bit mono PCM playback stream
                stream = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.sample_rate,
                    output=True,
                )

                chunk_size = 2048
                for i in range(0, len(raw_pcm), chunk_size):
                    if self._stop_requested:
                        break
                    stream.write(raw_pcm[i : i + chunk_size])

                # Brief hardware drain time to avoid truncation
                time.sleep(0.05)

            except Exception as e:
                print(f"[PiperTTS] Playback error: {e}")
            finally:
                if stream is not None:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except Exception:
                        pass
                self.is_speaking = False
                self.last_speech_time = time.monotonic()

    def stop(self):
        self._stop_requested = True
        self.is_speaking = False

    def shutdown(self):
        self.stop()
        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception:
                pass


def is_interruption(text: str) -> bool:
    if not text:
        return False
    triggers = {"stop", "cancel", "shut up", "be quiet", "pause", "halt", "hold on"}
    return any(t in text.lower() for t in triggers)


piper_tts = PiperTTS()