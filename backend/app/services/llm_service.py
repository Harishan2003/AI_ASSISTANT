"""
Provider-agnostic LLM Service supporting Groq, OpenAI, Ollama, and OpenRouter with tool calling.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Handles communication with LLM providers supporting function/tool calling."""

    def __init__(self):
        self._init_client()

    def _init_client(self):
        # Default to Groq if key exists, otherwise OpenAI or Ollama
        api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
        base_url = settings.groq_url or os.getenv("GROQ_URL", "https://api.groq.com/openai/v1")
        self.model = os.getenv("GROQ_MODEL") or settings.groq_model or "llama-3.3-70b-versatile"

        if not api_key:
            api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
            base_url = settings.openai_url or "https://api.openai.com/v1"
            self.model = settings.openai_model or "gpt-4o-mini"

        if not api_key:
            # Ollama local mode
            api_key = "ollama"
            base_url = f"{settings.ollama_url}/v1"
            self.model = settings.ollama_model or "llama3.2"

        self.client = OpenAI(
            api_key=api_key or "mock-key",
            base_url=base_url,
            timeout=float(settings.timeout or 60.0)
        )

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> Dict[str, Any]:
        """
        Calls OpenAI/Groq compatible chat completions API with tools.
        Returns dictionary containing:
        - content: str (assistant reasoning/text)
        - tool_calls: list of tool call objects [{"id", "name", "arguments"}]
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            message = choice.message

            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                    except Exception:
                        args = {}
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": args
                    })

            return {
                "content": message.content or "",
                "tool_calls": tool_calls,
                "finish_reason": choice.finish_reason
            }

        except Exception as e:
            logger.error(f"LLM chat completion error: {e}")
            raise RuntimeError(f"LLM request failed: {str(e)}")


llm_service = LLMService()
