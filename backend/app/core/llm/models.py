from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    GROQ = "groq"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    OPENAI = "openai"
    GEMINI = "gemini"
    LMSTUDIO = "lmstudio"


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]

    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
    )

    max_tokens: int = Field(
        default=4096,
        ge=1,
    )

    stream: bool = False


class ChatResponse(BaseModel):
    content: str
    model: str
    provider: LLMProvider


class ModelConfig(BaseModel):
    provider: LLMProvider

    model_name: str

    api_url: Optional[str] = None

    api_key: Optional[str] = None

    timeout: int = 60

    temperature: float = 0.7

    max_tokens: int = 4096


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ToolResult(BaseModel):
    tool_name: str
    output: str