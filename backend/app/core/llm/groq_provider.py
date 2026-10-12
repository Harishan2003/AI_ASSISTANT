"""
Groq LLM Provider
Filters models to only valid, terms-free chat models on the active Groq account.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator, List, Optional

import httpx

from .base import BaseLLMProvider
from .models import (
    ChatRequest,
    ChatResponse,
    LLMProvider,
    ModelConfig,
)


class GroqProvider(BaseLLMProvider):

    # Preferred active text models from Groq (ultra-fast, zero-thinking-latency first)
    ACCOUNT_PREFERENCE_ORDER = [
        "qwen/qwen3.8-27b",
        "allam-2-7b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ]

    def __init__(self, config: ModelConfig):
        self.config = config

        if not config.api_key:
            raise ValueError("GROQ_API_KEY is missing.")

        raw_url = (config.api_url or "https://api.groq.com/openai/v1").strip().rstrip("/")
        if raw_url.endswith("/chat/completions"):
            raw_url = raw_url[:-len("/chat/completions")].rstrip("/")
        if not raw_url.endswith("/openai/v1") and not raw_url.endswith("/v1"):
            raw_url = f"{raw_url}/openai/v1"

        self.base_url = raw_url
        self.model_name = config.model_name or "llama-3.3-70b-versatile"
        self._discovered_models: List[str] = []

        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

    # =====================================================
    # DYNAMIC MODEL DISCOVERY & FILTERING
    # =====================================================

    def _is_valid_chat_model(self, model_id: str) -> bool:
        """Filters out classifiers, audio engines, and prompt-guards."""
        mid = model_id.lower()
        blocked_keywords = [
            "whisper", "guard", "safeguard", "orpheus",
            "vision", "tts", "embedding"
        ]
        return not any(b in mid for b in blocked_keywords)

    async def _fetch_valid_models(self) -> List[str]:
        if self._discovered_models:
            return self._discovered_models

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(f"{self.base_url}/models", headers=self.headers)
                if res.status_code == 200:
                    data = res.json()
                    all_ids = [m["id"] for m in data.get("data", [])]
                    
                    # Sort by preference list first
                    filtered = [m for m in self.ACCOUNT_PREFERENCE_ORDER if m in all_ids]
                    # Add any other valid chat models not in preference list
                    filtered += [m for m in all_ids if m not in filtered and self._is_valid_chat_model(m)]

                    if filtered:
                        self._discovered_models = filtered
                        print(f"[GroqProvider] Usable conversational models: {self._discovered_models}")
                        return self._discovered_models
        except Exception as e:
            print(f"[GroqProvider] Failed to fetch /models: {e}")

        return self.ACCOUNT_PREFERENCE_ORDER

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/models", headers=self.headers)
                return response.status_code == 200
        except Exception as e:
            print(f"[Groq Health Error] {e}")
            return False

    # =====================================================
    # NORMAL CHAT
    # =====================================================

    async def chat(
        self,
        request: ChatRequest,
    ) -> ChatResponse:

        available_models = await self._fetch_valid_models()
        candidate_models = available_models if available_models else self.ACCOUNT_PREFERENCE_ORDER

        messages_payload = [
            {
                "role": message.role.value if hasattr(message.role, "value") else str(message.role),
                "content": message.content,
            }
            for message in request.messages
        ]

        timeout = httpx.Timeout(45.0, connect=5.0)
        endpoint_url = f"{self.base_url}/chat/completions"

        last_error = None

        async with httpx.AsyncClient(timeout=timeout) as client:
            for candidate in candidate_models:
                try:
                    payload = {
                        "model": candidate,
                        "messages": messages_payload,
                        "temperature": getattr(request, "temperature", 0.7),
                        "max_tokens": getattr(request, "max_tokens", 4096),
                        "stream": False,
                    }

                    response = await client.post(endpoint_url, headers=self.headers, json=payload)

                    if response.status_code == 200:
                        self.model_name = candidate
                        data = response.json()
                        content = data["choices"][0]["message"]["content"]
                        return ChatResponse(
                            content=content,
                            model=self.model_name,
                            provider=LLMProvider.GROQ,
                        )

                    last_error = response.text
                    print(f"[GroqProvider] Model '{candidate}' returned {response.status_code}. Trying next model...", flush=True)
                except Exception as e:
                    print(f"[GroqProvider] Model '{candidate}' error: {e}. Trying next model...", flush=True)

        raise RuntimeError(f"All Groq chat models failed. Last response: {last_error}")

    # =====================================================
    # STREAMING
    # =====================================================

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncGenerator[str, None]:

        available_models = await self._fetch_valid_models()
        candidate_models = available_models if available_models else self.ACCOUNT_PREFERENCE_ORDER

        messages_payload = [
            {
                "role": message.role.value if hasattr(message.role, "value") else str(message.role),
                "content": message.content,
            }
            for message in request.messages
        ]

        timeout = httpx.Timeout(45.0, connect=5.0)
        endpoint_url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=timeout) as client:
            for candidate in candidate_models:
                payload = {
                    "model": candidate,
                    "messages": messages_payload,
                    "temperature": getattr(request, "temperature", 0.7),
                    "max_tokens": getattr(request, "max_tokens", 4096),
                    "stream": True,
                }

                async with client.stream("POST", endpoint_url, headers=self.headers, json=payload) as response:
                    if response.status_code == 200:
                        self.model_name = candidate

                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            if line == "data: [DONE]":
                                break
                            if not line.startswith("data: "):
                                continue

                            try:
                                data = json.loads(line[6:])
                                choices = data.get("choices", [])
                                if not choices:
                                    continue
                                delta = choices[0].get("delta", {})
                                token = delta.get("content")
                                if token:
                                    yield token
                            except Exception as e:
                                print(f"[Groq Stream Parse Error] {e}")

                        return

                    err_body = await response.aread()
                    print(f"[GroqProvider Stream] Model '{candidate}' returned {response.status_code}. Trying next...")

    # =====================================================
    # CLOSE
    # =====================================================

    async def close(self):
        pass