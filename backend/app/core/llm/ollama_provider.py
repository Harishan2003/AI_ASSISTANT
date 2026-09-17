from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx

from .base import BaseLLMProvider
from .models import (
    ChatRequest,
    ChatResponse,
    LLMProvider,
)


class OllamaProvider(BaseLLMProvider):

    def __init__(self, config):

        super().__init__(config)

        self.client = httpx.AsyncClient(
            base_url=config.api_url,
            timeout=config.timeout,
        )

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def health_check(self) -> bool:

        try:

            response = await self.client.get(
                "/api/tags"
            )

            return response.status_code == 200

        except Exception:
            return False

    async def chat(
        self,
        request: ChatRequest,
    ) -> ChatResponse:

        payload = {
            "model": self.config.model_name,

            "messages": [
                {
                    "role": message.role.value,
                    "content": message.content,
                }
                for message in request.messages
            ],

            "stream": False,

            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        response = await self.client.post(
            "/api/chat",
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

        return ChatResponse(
            content=data["message"]["content"],
            model=self.config.model_name,
            provider=LLMProvider.OLLAMA,
        )

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncGenerator[str, None]:

        payload = {
            "model": self.config.model_name,

            "messages": [
                {
                    "role": message.role.value,
                    "content": message.content,
                }
                for message in request.messages
            ],

            "stream": True,

            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        async with self.client.stream(
            "POST",
            "/api/chat",
            json=payload,
        ) as response:

            response.raise_for_status()

            async for line in response.aiter_lines():

                if not line:
                    continue

                try:

                    data = json.loads(line)

                    content = data.get(
                        "message",
                        {}
                    ).get(
                        "content",
                        ""
                    )

                    if content:
                        yield content

                except json.JSONDecodeError:
                    continue

    async def close(self):
        await self.client.aclose()