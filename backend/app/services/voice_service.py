"""
Friday Voice Service
Production STT/TTS coordination, conversational memory, and context-aware action execution.
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional, List

# Unified SenseVoice-Small STT engine
from app.speech.sensevoice_stt import sensevoice_stt as stt_engine


SYSTEM_PROMPT = (
    "You are Friday, an intelligent, versatile desktop AI assistant. "
    "By default, keep spoken answers concise and direct. "
    "However, if the user explicitly asks for a specific length, format, list, or detailed explanation "
    "(e.g., 'in 10 lines', 'explain step by step', 'give 5 points'), follow their requested length and format exactly."
)


class VoiceService:

    WAKE_DURATION = 2.0
    INTERRUPT_DURATION = 1.8
    NORMAL_DURATION = 2.0
    COMMAND_MAX_DURATION = 30.0
    COMMAND_SILENCE_DURATION = 1.5
    COMMAND_START_TIMEOUT = 5.0
    MAX_MEMORY_MESSAGES = 40

    def __init__(self):
        self.stt = stt_engine
        self.is_listening = False
        self.is_interruption_listening = False
        self.conversation_history: List[dict] = []

        print()
        print("============================================================")
        print("[VoiceService] INITIALIZED")
        print("============================================================")

    def listen(self, duration: float = NORMAL_DURATION) -> str:
        if duration <= 0:
            duration = self.NORMAL_DURATION
        print("\n[VoiceService] Listening...")
        self.is_listening = True
        try:
            text = self.stt.listen_utterance(lambda: not self.is_listening)
            text = self._clean_text(text)
            print(f"[VoiceService] Recognized: {text}")
            return text
        except KeyboardInterrupt:
            return ""
        except Exception as e:
            print(f"[VoiceService] Listen error: {e}")
            return ""
        finally:
            self.is_listening = False

    def listen_wake_word(self, duration: float = WAKE_DURATION) -> str:
        if duration <= 0:
            duration = self.WAKE_DURATION
        print("\n[VoiceService] Listening for wake word...")
        self.is_listening = True
        try:
            text = self.stt.listen_utterance(lambda: not self.is_listening)
            text = self._clean_text(text)
            print(f"[VoiceService] Wake result: {text}")
            return text
        except KeyboardInterrupt:
            return ""
        except Exception as e:
            print(f"[VoiceService] Wake error: {e}")
            return ""
        finally:
            self.is_listening = False

    def listen_interrupt(self, duration: float = INTERRUPT_DURATION) -> str:
        if duration <= 0:
            duration = self.INTERRUPT_DURATION
        self.is_interruption_listening = True
        try:
            text = self.stt.scan_for_interrupt_sync(lambda: not self.is_interruption_listening)
            text = self._clean_text(text)
            if text:
                print(f"[VoiceService] Interrupt STT: {text}")
            return text or ""
        except KeyboardInterrupt:
            return ""
        except Exception as e:
            print(f"[VoiceService] Interrupt listen error: {e}")
            return ""
        finally:
            self.is_interruption_listening = False

    def listen_command(
        self,
        max_duration: float = COMMAND_MAX_DURATION,
        silence_duration: float = COMMAND_SILENCE_DURATION,
        start_timeout: float = COMMAND_START_TIMEOUT,
    ) -> str:
        self.is_listening = True
        try:
            text = self.stt.listen_utterance(
                lambda: not self.is_listening,
                silence_timeout=silence_duration,
                max_duration=max_duration,
            )
            text = self._clean_text(text)
            print(f"[VoiceService] Command recognized: {text}")
            return text
        except KeyboardInterrupt:
            return ""
        except Exception as e:
            print(f"[VoiceService] Command listen error: {e}")
            return ""
        finally:
            self.is_listening = False

    def _add_user_message(self, message: str) -> None:
        message = self._clean_text(message)
        if not message:
            return
        self.conversation_history.append({"role": "user", "content": message})
        self._trim_memory()

    def _add_assistant_message(self, message: str) -> None:
        message = self._clean_text(message)
        if not message:
            return
        self.conversation_history.append({"role": "assistant", "content": message})
        self._trim_memory()

    def _trim_memory(self) -> None:
        if len(self.conversation_history) <= self.MAX_MEMORY_MESSAGES:
            return
        self.conversation_history = self.conversation_history[-self.MAX_MEMORY_MESSAGES:]

    def get_memory(self) -> List[dict]:
        return list(self.conversation_history)

    def memory_count(self) -> int:
        return len(self.conversation_history)

    def clear_memory(self) -> None:
        count = len(self.conversation_history)
        self.conversation_history.clear()
        print("\n============================================================")
        print("[VoiceService] CONVERSATION MEMORY CLEARED")
        print(f"[VoiceService] Removed {count} messages.")
        print("============================================================\n")

    def is_exit_command(self, text: str) -> bool:
        text = self._clean_text(text).lower()
        exit_commands = {
            "exit", "quit", "goodbye", "good bye", "shutdown",
            "close friday", "exit friday", "quit friday", "shutdown friday",
        }
        return text in exit_commands

    async def process(self, user_message: str) -> str:
        user_message = self._clean_text(user_message)
        if not user_message:
            return ""

        if self.is_exit_command(user_message):
            print("[VoiceService] Exit command detected.")
            self.clear_memory()
            return ""

        print("\n[VoiceService] Sending to ChatService:")
        print(f"> > > {user_message}")

        try:
            from app.services.chat_service import chat_service
            from app.core.llm.models import ChatRequest, ChatMessage, MessageRole

            self._add_user_message(user_message)

            messages = [ChatMessage(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT)]
            for item in self.conversation_history:
                role = MessageRole.USER if item["role"] == "user" else MessageRole.ASSISTANT
                messages.append(ChatMessage(role=role, content=item["content"]))

            request = ChatRequest(messages=messages)
            result = await chat_service.chat(request)

            if result is None or getattr(result, "content", None) is None:
                if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                    self.conversation_history.pop()
                return ""

            answer = str(result.content).strip()
            if not answer:
                if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                    self.conversation_history.pop()
                return ""

            self._add_assistant_message(answer)
            print(f"\n[VoiceService] Assistant:\n{answer}\n")
            return answer

        except asyncio.CancelledError:
            raise
        except KeyboardInterrupt:
            return ""
        except Exception as e:
            print(f"\n[VoiceService] ChatService error:\n> > > {e}")
            if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                self.conversation_history.pop()
            return ""

    def _clean_text(self, text: Optional[str]) -> str:
        if text is None:
            return ""
        text = str(text).strip()
        if not text:
            return ""
        invalid = {
            "[inaudible]", "(inaudible)", "[static]", "(static)", "[music]",
            "(music)", "[noise]", "(noise)", "[silence]", "(silence)",
            "[blank_audio]", "(blank_audio)", "[unknown]", "(unknown)",
            "[unintelligible]", "(unintelligible)", "...",
        }
        if text.lower() in invalid:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def get_language(self) -> Optional[str]:
        return "en"

    def shutdown(self) -> None:
        self.clear_memory()
        self.is_listening = False
        self.is_interruption_listening = False


# Singleton Instance
voice_service = VoiceService()