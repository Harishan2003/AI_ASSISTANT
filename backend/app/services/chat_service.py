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

import asyncio
import inspect
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.llm.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, ModelConfig
from app.core.llm.provider_factory import ProviderFactory
from app.services.agent_router import agent_router
from app.services.web_search_context import gather_all_web_context
from app.tools.tool_registry import tool_registry


class ChatService:

    def __init__(self):
        provider = settings.llm_provider
        print(f"[ChatService] Provider: {provider.value}")

        if provider.value == "groq":
            config = ModelConfig(
                provider=provider,
                model_name=settings.groq_model or "llama-3.3-70b-versatile",
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

    async def _fetch_web_search(self, query: str) -> str:
        """Fetches live search and news results for real-time grounding."""
        try:
            print(f"[ChatService] Fetching live web/news intelligence for: {query}", flush=True)
            res = await gather_all_web_context(query)
            return res or ""
        except Exception as e:
            print(f"[ChatService] Web context error: {e}", flush=True)
            return ""

    def _ensure_system_prompt(self, messages: list[ChatMessage], live_context: str = "") -> list[ChatMessage]:
        """Ensures the assistant answers with up-to-date real world knowledge, personal warmth, and caring context."""
        from datetime import datetime
        current_date_str = datetime.now().strftime("%A, %B %d, %Y, %I:%M %p")
        
        agent_name = "Friday"
        user_name = "Harishan"
        try:
            from app.services.command_executor import load_user_profile
            prof = load_user_profile()
            agent_name = prof.get("agent_profile", {}).get("agent_name") or prof.get("agent_name") or prof.get("wake_word") or "Friday"
            user_name = prof.get("profile", {}).get("name") or prof.get("name") or "Harishan"
        except Exception:
            pass

        persona_context = ""
        try:
            from app.services.user_persona_service import user_persona_service
            persona_context = user_persona_service.get_care_and_wellbeing_context()
        except Exception:
            pass

        system_content = (
            f"You are {agent_name}, {user_name}'s dedicated personal AI companion, trusted advisor, and intelligent partner. "
            f"Current real-world date and time: {current_date_str}.\n\n"
            + (f"{persona_context}\n\n" if persona_context else "")
            + "CORE GUIDELINES:\n"
            + "- You have full built-in AI image generation, photo editing, and computer vision capabilities powered by FLUX.1. Never claim you cannot render or output images.\n"
            + "- You run directly on Harishan's Windows 10/11 PC with full Device Monitoring & Control enabled (screen reading, mouse cursor tracking, window management, file operations, app launching, volume/brightness control, and email client automation). NEVER state that you cannot control the screen, access files, inspect the cursor, or send emails.\n"
            + "- NEVER output fake or fabricated markdown image URLs (such as ![...](http://localhost:8000/api/v1/images/...)). Image rendering is handled automatically by Friday's internal neural diffusion pipeline.\n"
            + "- State verified facts clearly without robotic self-correction loops or internal reasoning traces."
        )
        
        if live_context:
            system_content += f"\n\nLIVE REAL-TIME DATA / BREAKING NEWS FOR THIS QUERY:\n{live_context}\n(Synthesize the verified live headlines and information above into a direct, helpful answer)."

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

        # Contextual search query resolution for follow-ups
        search_query = user_message
        if len(request.messages) > 1:
            prev_user_msgs = [m.content for m in request.messages[:-1] if m.role == MessageRole.USER]
            if prev_user_msgs:
                last_user_topic = prev_user_msgs[-1]
                pronoun_triggers = ["he", "she", "it", "they", "this", "that", "his", "her", "their", "score", "price", "rate", "what about", "how about", "why", "when", "more"]
                if any(p in user_message.lower().split() for p in pronoun_triggers) or len(user_message.split()) <= 4:
                    search_query = f"{last_user_topic} {user_message}"

        live_context = ""
        keywords = [
            "latest", "current", "who is", "who are", "who was", "news", "headline", "headlines", "breaking",
            "update", "updates", "weather", "temperature", "election", "today", "todays", "yesterday", "tomorrow",
            "2026", "score", "match", "stock", "sensex", "nifty", "gold rate", "price",
            "politics", "political", "government", "assembly", "parliament", "chief minister", "prime minister",
            "president", "governor", "founder", "ceo", "net worth", "capital of",
            "movie", "movies", "film", "films", "cinema", "trailer", "teaser", "box office", "release", "releasing", "ott",
            "actor", "actress", "director", "song", "songs", "album", "review", "reviews", "cast",
            "tell me about", "about actor", "about person", "profile of", "age", "how old",
            "born", "birthday", "birth date", "party", "political party",
            "happened", "happening", "happen in", "what happened", "whats happening", "is there anything"
        ]
        if any(k in search_query.lower() for k in keywords):
            live_context = await self._fetch_web_search(search_query)

        request.messages = self._ensure_system_prompt(request.messages, live_context)
        response = await self.provider.chat(request)
        if response and response.content:
            response.content = self._sanitize_output(response.content)
            try:
                from app.services.user_persona_service import user_persona_service
                loop = asyncio.get_running_loop()
                loop.run_in_executor(None, user_persona_service.analyze_chat_turn, user_message, response.content, "chat_service")
            except Exception:
                pass
        return response

    async def handle_input(self, user_input: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
        text = str(user_input).strip()
        if not text:
            return "Standing by, boss."

        messages = []
        if history:
            for h in history:
                r = str(h.get("role", "")).lower()
                c = str(h.get("content", "")).strip()
                if c:
                    role_enum = MessageRole.USER if r == "user" else MessageRole.ASSISTANT
                    messages.append(ChatMessage(role=role_enum, content=c))

        messages.append(ChatMessage(role=MessageRole.USER, content=text))
        request = ChatRequest(messages=messages)
        response = await self.chat(request)
        content = response.content if hasattr(response, "content") else str(response)
        return self._sanitize_output(content)

    async def process_message(self, user_input: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
        return await self.handle_input(user_input, history=history)

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
        keywords = [
            "latest", "current", "who is", "who are", "who was", "news", "headline", "headlines", "breaking",
            "update", "updates", "weather", "temperature", "election", "today", "todays", "yesterday",
            "2026", "score", "match", "stock", "sensex", "nifty", "gold rate", "price",
            "tell me about", "about actor", "about person", "profile of", "age", "how old",
            "born", "birthday", "birth date", "party", "political party", "chief minister", "prime minister",
            "president", "governor", "founder", "ceo", "net worth", "capital of"
        ]
        if any(k in user_message.lower() for k in keywords):
            live_context = await self._fetch_web_search(user_message)

        request.messages = self._ensure_system_prompt(request.messages, live_context)
        async for token in self.provider.stream_chat(request):
            cleaned_token = self._sanitize_output(token)
            if cleaned_token:
                yield cleaned_token

    async def close(self):
        await self.provider.close()


chat_service = ChatService()