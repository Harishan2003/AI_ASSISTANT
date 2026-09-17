from __future__ import annotations

from .base import BaseLLMProvider
from .models import (
    LLMProvider,
    ModelConfig,
)

from .groq_provider import GroqProvider
from .ollama_provider import OllamaProvider


class ProviderFactory:

    @staticmethod
    def create(
        config: ModelConfig,
    ) -> BaseLLMProvider:

        if config.provider == LLMProvider.GROQ:

            return GroqProvider(config)

        if config.provider == LLMProvider.OLLAMA:

            return OllamaProvider(config)

        raise ValueError(
            f"Provider '{config.provider}' "
            f"is not implemented."
        )