"""
Friday Chat Service

Responsibilities:
- Normal LLM chat
- System commands
- Application launching
- Chat/Call Automation
- File/folder/drive navigation
- Registered tools
- Web search / Calculator / Weather
"""

from __future__ import annotations

import inspect
import re
from duckduckgo_search import DDGS

from app.core.config import settings
from app.core.llm.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, ModelConfig
from app.core.llm.provider_factory import ProviderFactory
from app.services.agent_router import agent_router
from app.tools import tool_registry


class ChatService:

    def __init__(self):
        provider = settings.llm_provider
        print(f"[ChatService] Provider: {provider.value}")

        if provider.value == "groq":
            config = ModelConfig(
                provider=provider,
                model_name="qwen/qwen3.6-27b",
                api_url=settings.groq_url,
                api_key=settings.groq_api_key,
                timeout=settings.timeout,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
        elif provider.value == "ollama":
            config = ModelConfig(
                provider=provider,
                model_name=settings.ollama_model,
                api_url=settings.ollama_url,
                timeout=settings.timeout,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        self.provider = ProviderFactory.create(config)
        print(f"[ChatService] Provider created: {type(self.provider).__name__}")

    def _sanitize_output(self, text: str) -> str:
        """Failsafe isolator for ChatService responses."""
        if not text:
            return ""
        if "<think>" in text.lower():
            print(f"\n[ChatService Thinking Trace Isolated]:\n{text}\n", flush=True)
            
        if "</think>" in text.lower():
            parts = re.split(r"</think>", text, flags=re.IGNORECASE)
            text = parts[-1]
            
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"<think[\s\S]*$", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    async def health(self) -> bool:
        return await self.provider.health_check()

    async def _system_command(
        self,
        command: str,
        user_message: str,
    ) -> ChatResponse:
        print()
        print("[ChatService] System command detected:")
        print(f"[ChatService] Tool: {command}")
        print(f"[ChatService] Request: {user_message}")

        try:
            from app.services.system_service import system_service

            result = system_service.execute(
                action=command,
                user_message=user_message,
            )

            print(f"[ChatService] System result: {result}")

            return ChatResponse(
                content=self._sanitize_output(result),
                model="system",
                provider=settings.llm_provider,
            )

        except Exception as e:
            print("\n[ChatService] SystemService error:")
            print(f"> > > {e}")

            return ChatResponse(
                content="I could not complete that system command.",
                model="system",
                provider=settings.llm_provider,
            )

    async def _execute_tool(
        self,
        tool_name: str,
        user_message: str,
    ) -> ChatResponse:

        print()
        print("[ChatService] Executing tool")
        print(f"[ChatService] Tool: {tool_name}")
        print(f"[ChatService] Input: {user_message}")

        if tool_name == "context_execution":
            if hasattr(agent_router, "_last_context_result") and agent_router._last_context_result:
                return ChatResponse(
                    content=self._sanitize_output(str(agent_router._last_context_result)),
                    model="context",
                    provider=settings.llm_provider,
                )
            try:
                from app.services.context_service import context_service

                res = context_service.try_handle_context(user_command=user_message)
                if res:
                    return ChatResponse(
                        content=self._sanitize_output(str(res)),
                        model="context",
                        provider=settings.llm_provider,
                    )
            except Exception as err:
                print(f"[ChatService] Context handling error: {err}")

        system_commands = {
            "open_file_explorer",
            "open_drive",
            "open_folder",
            "open_application",
        }

        if tool_name in system_commands:
            return await self._system_command(
                command=tool_name,
                user_message=user_message,
            )

        try:
            tool = tool_registry.get(tool_name)
        except Exception as e:
            print(f"[ChatService] Tool registry error: {e}")
            return ChatResponse(
                content=f"Tool '{tool_name}' is not available.",
                model="tool",
                provider=settings.llm_provider,
            )

        if tool is None:
            return ChatResponse(
                content=f"Tool '{tool_name}' is not available.",
                model="tool",
                provider=settings.llm_provider,
            )

        try:
            result = tool(user_message)
        except TypeError:
            try:
                result = tool()
            except Exception as e:
                print(f"[ChatService] Tool execution error: {e}")
                return ChatResponse(
                    content="I could not execute that command.",
                    model="tool",
                    provider=settings.llm_provider,
                )
        except Exception as e:
            print(f"[ChatService] Tool execution error: {e}")
            return ChatResponse(
                content="I could not execute that command.",
                model="tool",
                provider=settings.llm_provider,
            )

        if inspect.isawaitable(result):
            result = await result

        if result is None:
            result = "Command completed."
        elif not isinstance(result, str):
            result = str(result)

        result = self._sanitize_output(result)

        return ChatResponse(
            content=result,
            model="tool",
            provider=settings.llm_provider,
        )

    def _fetch_web_search(self, query: str) -> str:
        """Fetches live search results for real-time grounding."""
        try:
            print(f"[ChatService] Fetching live web search for: {query}")
            with DDGS() as ddgs:
                results = [r.get("body", "") for r in ddgs.text(query, max_results=3)]
                if results:
                    return " | ".join(results)
        except Exception as e:
            print(f"[ChatService] Web search error: {e}")
        return ""

    def _ensure_system_prompt(self, messages: list[ChatMessage], live_context: str = "") -> list[ChatMessage]:
        """Ensures Friday/Jarvis answers directly with up-to-date real world knowledge."""
        system_content = (
            "You are an intelligent, concise personal AI assistant with full real-time awareness of global current affairs, "
            "geopolitics, wars, climate and weather events, food/water crises, and space science updates. "
            "Answer inquiries directly, factually, and concisely without conversational fluff."
        )
        
        if live_context:
            system_content += f"\n\nLIVE REAL-TIME WEB SEARCH DATA FOR THIS QUERY:\n{live_context}\n(Use this live data to provide an accurate, up-to-date answer)."

        has_system = any(m.role == MessageRole.SYSTEM for m in messages)
        if not has_system:
            return [ChatMessage(role=MessageRole.SYSTEM, content=system_content)] + messages
        
        for m in messages:
            if m.role == MessageRole.SYSTEM:
                m.content = system_content + "\n\n" + m.content
                return messages
                
        return [ChatMessage(role=MessageRole.SYSTEM, content=system_content)] + messages

    async def chat(
        self,
        request: ChatRequest | str,
    ) -> ChatResponse:

        if isinstance(request, str):
            request = ChatRequest(
                messages=[ChatMessage(role=MessageRole.USER, content=request)]
            )

        if not request.messages:
            raise ValueError("No messages provided.")

        user_message = request.messages[-1].content
        tool_name = agent_router.route(message=user_message)

        if tool_name:
            return await self._execute_tool(tool_name, user_message)

        live_context = ""
        keywords = ["latest", "current", "who is", "news", "update", "weather", "election", "today", "2026"]
        if any(k in user_message.lower() for k in keywords):
            live_context = self._fetch_web_search(user_message)

        request.messages = self._ensure_system_prompt(request.messages, live_context)
        response = await self.provider.chat(request)
        if response and response.content:
            response.content = self._sanitize_output(response.content)
        return response

    async def handle_input(self, user_input: str) -> str:
        text = str(user_input).strip()
        if not text:
            return "Standing by, boss."

        response = await self.chat(text)
        content = response.content if hasattr(response, "content") else str(response)
        return self._sanitize_output(content)

    async def process_message(self, user_input: str) -> str:
        return await self.handle_input(user_input)

    async def stream_chat(
        self,
        request: ChatRequest,
    ):
        if not request.messages:
            raise ValueError("No messages provided.")

        user_message = request.messages[-1].content
        tool_name = agent_router.route(message=user_message)

        if tool_name:
            response = await self._execute_tool(tool_name, user_message)
            yield self._sanitize_output(response.content)
            return

        live_context = ""
        keywords = ["latest", "current", "who is", "news", "update", "weather", "election", "today", "2026"]
        if any(k in user_message.lower() for k in keywords):
            live_context = self._fetch_web_search(user_message)

        request.messages = self._ensure_system_prompt(request.messages, live_context)
        async for token in self.provider.stream_chat(request):
            cleaned_token = self._sanitize_output(token)
            if cleaned_token:
                yield cleaned_token

    async def close(self):
        await self.provider.close()


chat_service = ChatService()