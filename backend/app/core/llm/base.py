from abc import ABC, abstractmethod

from .models import (
    ChatRequest,
    ChatResponse,
    ModelConfig,
)


class BaseLLMProvider(ABC):

    def __init__(
        self,
        config: ModelConfig,
    ):

        self.config = config

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    @abstractmethod
    async def chat(
        self,
        request: ChatRequest,
    ) -> ChatResponse:
        pass

    @abstractmethod
    async def stream_chat(
        self,
        request: ChatRequest,
    ):
        pass

    @abstractmethod
    async def close(self):
        pass