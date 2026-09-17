"""
Friday AI Assistant - Direct Resilient Voice Loop with Dual-Mode Audio Support
"""

from __future__ import annotations

import asyncio
import difflib
import os
import re
import signal
import time

from app.services.voice_service import voice_service
from app.speech.piper_tts import piper_tts
from app.speech.sensevoice_stt import sensevoice_stt as stt_engine


WAKE_WORDS = [
    "friday",
    "hey friday",
    "hello friday",
    "freddy",
    "hey freddy",
    "today",
    "tday",
    "ready",
    "fry day",
    "fday",
    "gdy",
    "saidide",
    "ma it",
]

LOCAL_STOP_WORDS = [
    "stop",
    "cancel",
    "be quiet",
    "shut up",
    "pause",
    "never mind",
    "halt",
    "quiet",
    "hold on",
    "enough",
    "right i stop",
]

STRICT_EXIT_COMMANDS = [
    "exit friday",
    "quit friday",
    "shutdown friday",
    "stop friday",
    "friday exit",
    "friday quit",
    "friday shutdown",
    "goodbye friday",
    "friday goodbye",
    "goodbye",
    "bye friday",
    "friday bye",
    "shutdown",
    "exit",
    "quit",
]

IGNORED_NOISE = {
    "static", "(static)", "inaudible", "(inaudible)", "noise", "music",
    "click", "applause", "laughter", "bye", "okay", "e", "snoring", "h", "yeah", "the"
}

APP_SHORTCUTS = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "ground": "chrome",
    "ch": "chrome",
    "che": "chrome",
    "whatsapp": "whatsapp:",        # Uses Windows URI scheme to launch WhatsApp Desktop
    "whatapps": "whatsapp:",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "task manager": "taskmgr",
    "taskmgr": "taskmgr",
    "explorer": "explorer",
    "file explorer": "explorer",
}

shutdown_event: asyncio.Event | None = None


def get_shutdown_event() -> asyncio.Event:
    global shutdown_event
    if shutdown_event is None:
        shutdown_event = asyncio.Event()
    return shutdown_event


def normalize(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\btday\b", "friday", text)
    text = re.sub(r"\bfday\b", "friday", text)
    text = re.sub(r"\bgdy\b", "friday", text)
    text = re.sub(r"\bfreddy\b", "friday", text)
    text = re.sub(r"\bread it\b", "friday", text)
    text = re.sub(r"\bsaidide\b", "friday", text)
    text = re.sub(r"\bma it\b", "friday", text)
    return " ".join(text.split())


def is_self_speech_echo(recognized_text: str) -> bool:
    """Detects and discards remnant speaker output captured by the mic immediately after TTS."""
    if not recognized_text:
        return False

    last_speech_time = getattr(piper_tts, "last_speech_time", 0.0)
    if time.monotonic() - last_speech_time > 2.5:
        return False

    last_spoken = getattr(piper_tts, "last_spoken_text", "")
    if not last_spoken:
        return False

    norm_rec = normalize(recognized_text)
    norm_spoken = normalize(last_spoken)

    if not norm_rec:
        return False

    if norm_rec in norm_spoken:
        return True

    rec_words = [w for w in norm_rec.split() if w not in {"friday", "freddy", "hey", "hello"} and len(w) > 2]
    if not rec_words:
        return False

    spoken_words = set(norm_spoken.split())
    matched = [w for w in rec_words if w in spoken_words]

    if (len(matched) / len(rec_words)) >= 0.45:
        return True

    ratio = difflib.SequenceMatcher(None, norm_rec, norm_spoken[:len(norm_rec) + 20]).ratio()
    return ratio >= 0.55


def is_exit_command(text: str) -> bool:
    command = normalize(text)
    if not command:
        return False
    exit_words = ["exit", "quit", "goodbye", "bye", "shutdown"]
    words = command.split()
    return any(w in exit_words for w in words)


def is_local_stop_command(command: str) -> bool:
    normalized_cmd = normalize(command)
    if not normalized_cmd:
        return False
    words = normalized_cmd.split()
    non_stop = [w for w in words if w not in ["stop", "cancel", "friday", "please", "quiet", "hold", "on", "right", "i"]]
    if len(non_stop) == 0:
        return True
    for stop_phrase in LOCAL_STOP_WORDS:
        if stop_phrase in normalized_cmd:
            return True
    return False


def extract_wake_and_command(text: str) -> tuple[bool, str]:
    cleaned = normalize(text)
    if not cleaned or cleaned in IGNORED_NOISE:
        return False, ""

    if is_exit_command(cleaned):
        return True, "exit"

    for wake in ["friday", "today", "ready"]:
        pattern = rf"\b{wake}\b"
        if re.search(pattern, cleaned):
            command = re.sub(pattern, "", cleaned).strip()
            return True, command

    action_starters = [
        "open ", "launch ", "start ", "play ", "run ",
        "what is ", "what time ", "who is ", "calculate ",
        "search ", "browse ", "call ", "message ", "send ", "select ", "tell me "
    ]
    for act in action_starters:
        if cleaned.startswith(act):
            return True, cleaned

    return False, ""


# =============================================================
# SPEAK (DIRECT TTS)
# =============================================================

async def speak_with_interrupt(
    text: str,
    monitor_interrupt: bool = False,
) -> tuple[bool, str]:
    if not text:
        return False, ""

    event = get_shutdown_event()
    if event.is_set() and text != "Goodbye. Have a great day!":
        return True, "exit"

    print(f"\n[Friday] Speaking: {text}\n")

    await asyncio.to_thread(piper_tts.speak, text, "en")
    await asyncio.sleep(0.2)
    return False, ""


# =============================================================
# WAKE LISTENER
# =============================================================

async def wait_for_wake_word() -> tuple[bool, str]:
    event = get_shutdown_event()

    print("\n" + "=" * 60)
    print("[Friday] LISTENING... (Say 'Friday <command>' or 'Open <app>')")
    print("=" * 60)

    while not event.is_set():
        try:
            text = await asyncio.to_thread(
                stt_engine.listen_utterance,
                lambda: event.is_set(),
            )

            if not text:
                await asyncio.sleep(0.02)
                continue

            if is_self_speech_echo(text):
                continue

            cleaned = normalize(text)
            if not cleaned or cleaned in IGNORED_NOISE or len(cleaned) < 2:
                continue

            print(f"[Voice Input] Recognized: '{text}'")

            if is_exit_command(text):
                event.set()
                return True, "exit"

            has_wake, command = extract_wake_and_command(text)
            if has_wake:
                if is_exit_command(command):
                    event.set()
                    return True, "exit"
                return True, command

        except KeyboardInterrupt:
            event.set()
            return False, ""
        except Exception as e:
            print(f"[VoiceLoop] Listener warning: {e}")
            await asyncio.sleep(0.02)

    return False, ""


# =============================================================
# PROCESS COMMAND
# =============================================================

async def process_command(command: str) -> str:
    if not command:
        return ""

    if is_local_stop_command(command):
        print(f"[Friday] Local stop: '{command}'")
        piper_tts.stop()
        return ""

    norm_cmd = normalize(command)

    # Dynamic Audio Mode Toggle Commands
    if "system sound" in norm_cmd or "system audio" in norm_cmd or "pc audio" in norm_cmd:
        if "off" in norm_cmd or "stop" in norm_cmd or "disable" in norm_cmd:
            if hasattr(stt_engine, "set_capture_mode"):
                stt_engine.set_capture_mode("mic")
            return "Switched back to microphone only. System sound is now ignored."
        else:
            if hasattr(stt_engine, "set_capture_mode"):
                stt_engine.set_capture_mode("system")
            return "Now listening to system sound."

    # Fast-path for opening applications (sub-50ms execution)
    for trigger, app in APP_SHORTCUTS.items():
        if norm_cmd.startswith(f"open {trigger}") or norm_cmd == f"open {trigger}" or norm_cmd == trigger:
            os.system(f"start {app}")
            return f"Opening {trigger}."

    print(f"\n[Friday] Executing command: '{command}'")

    try:
        answer = await voice_service.process(command)
        return answer or ""
    except Exception as e:
        print(f"[Friday] Processing error: {e}")
        return ""


def handle_signal(signum, frame):
    print("\n[Friday] Shutdown signal received.")
    get_shutdown_event().set()
    try:
        piper_tts.stop()
    except Exception:
        pass


# =============================================================
# MAIN EVENT LOOP
# =============================================================

async def main():
    event = get_shutdown_event()

    print("\n" + "=" * 60)
    print("             FRIDAY AI ASSISTANT ONLINE")
    print("=" * 60)

    try:
        await speak_with_interrupt("Hello, I am Friday. How can I help you?", monitor_interrupt=False)
    except Exception:
        pass

    pending_command = ""

    while not event.is_set():
        try:
            if pending_command:
                command = pending_command
                pending_command = ""
                woke = True
            else:
                woke, command = await wait_for_wake_word()

            if event.is_set() or not woke or command == "exit":
                await speak_with_interrupt("Goodbye. Have a great day!", monitor_interrupt=False)
                break

            # Handle standalone wake words by asking for clarification
            if not command:
                await speak_with_interrupt("Yes? How can I help you?", monitor_interrupt=False)
                raw_followup = await asyncio.to_thread(
                    stt_engine.listen_utterance,
                    lambda: event.is_set(),
                )
                if not raw_followup:
                    continue
                if is_exit_command(raw_followup):
                    await speak_with_interrupt("Goodbye. Have a great day!", monitor_interrupt=False)
                    break
                command = normalize(raw_followup)

            answer = await process_command(command)
            if answer:
                await speak_with_interrupt(answer, monitor_interrupt=False)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[Friday] Error: {e}")
            await asyncio.sleep(0.02)

    piper_tts.stop()
    piper_tts.shutdown()
    stt_engine.shutdown()
    print("\n[Friday] System offline.")


if __name__ == "__main__":
    try:
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
    except Exception:
        pass

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Friday] Exited.")