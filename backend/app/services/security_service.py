"""
Friday Chat Service

Handles:

- Normal LLM chat
- System commands
- File Explorer
- Drives
- Folders
- Applications
- Current time
- Web search
- Calculator
- Weather
- Registered tools
- Conversation memory
- Streaming
"""

from __future__ import annotations

from app.core.config import settings

from app.core.llm.models import (
    ChatRequest,
    ChatResponse,
    ModelConfig,
)

from app.core.llm.provider_factory import (
    ProviderFactory,
)

from app.services.agent_router import (
    agent_router,
)

from app.tools import (
    tool_registry,
)


class ChatService:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(self):

        provider = settings.llm_provider

        print(
            f"[ChatService] Provider: "
            f"{provider.value}"
        )

        # =====================================================
        # GROQ
        # =====================================================

        if provider.value == "groq":

            print(
                "[ChatService] Using Groq configuration"
            )

            config = ModelConfig(
                provider=provider,
                model_name=settings.groq_model,
                api_url=settings.groq_url,
                api_key=settings.groq_api_key,
                timeout=settings.timeout,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )

        # =====================================================
        # OLLAMA
        # =====================================================

        elif provider.value == "ollama":

            print(
                "[ChatService] Using Ollama configuration"
            )

            config = ModelConfig(
                provider=provider,
                model_name=settings.ollama_model,
                api_url=settings.ollama_url,
                timeout=settings.timeout,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )

        else:

            raise ValueError(
                f"Unsupported LLM provider: {provider}"
            )

        # =====================================================
        # PROVIDER
        # =====================================================

        self.provider = ProviderFactory.create(
            config
        )

        print(
            "[ChatService] Provider created: "
            f"{type(self.provider).__name__}"
        )

    # =========================================================
    # HEALTH
    # =========================================================

    async def health(
        self,
    ) -> bool:

        return await (
            self.provider.health_check()
        )

    # =========================================================
    # SYSTEM COMMAND
    # =========================================================

    async def _system_command(
        self,
        command: str,
        user_message: str,
    ) -> ChatResponse:

        print()
        print(
            "[ChatService] System command detected:"
        )

        print(
            f"[ChatService] Tool: {command}"
        )

        print(
            f"[ChatService] Request: "
            f"{user_message}"
        )

        try:

            from app.services.system_service import (
                system_service,
            )

            result = (
                system_service.execute(
                    command=command,
                    user_message=user_message,
                )
            )

            print(
                "[ChatService] "
                f"System result: {result}"
            )

            return ChatResponse(
                content=result,
                model="system",
                provider=settings.llm_provider,
            )

        except Exception as e:

            print()
            print(
                "[ChatService] SystemService error:"
            )

            print(
                f"> > > {e}"
            )

            return ChatResponse(
                content=(
                    "I could not complete "
                    "that system command."
                ),
                model="system",
                provider=settings.llm_provider,
            )

    # =========================================================
    # CHAT
    # =========================================================

    async def chat(
        self,
        request: ChatRequest,
    ) -> ChatResponse:

        if not request.messages:

            raise ValueError(
                "No messages provided."
            )

        # -----------------------------------------------------
        # LAST USER MESSAGE
        # -----------------------------------------------------

        user_message = (
            request
            .messages[-1]
            .content
        )

        print()
        print(
            f"[ChatService] User: "
            f"{user_message}"
        )

        # =====================================================
        # AGENT ROUTER
        # =====================================================

        tool_name = (
            agent_router.route(
                user_message
            )
        )

        print(
            f"[ChatService] Tool: "
            f"{tool_name}"
        )

        # =====================================================
        # SYSTEM COMMANDS
        # =====================================================

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

        # =====================================================
        # WEB SEARCH
        # =====================================================

        if tool_name == "web_search":

            search_tool = (
                tool_registry.get(
                    "web_search"
                )
            )

            if search_tool is None:

                return ChatResponse(
                    content=(
                        "Web search is "
                        "not available."
                    ),
                    model="tool",
                    provider=settings.llm_provider,
                )

            try:

                result = await search_tool(
                    user_message
                )

            except Exception as e:

                print(
                    "[ChatService] "
                    f"Web search error: {e}"
                )

                return ChatResponse(
                    content=(
                        "I couldn't perform "
                        "the web search."
                    ),
                    model="tool",
                    provider=settings.llm_provider,
                )

            if isinstance(
                result,
                dict,
            ):

                content = result.get(
                    "answer",
                    result.get(
                        "content",
                        str(result),
                    ),
                )

            else:

                content = str(
                    result
                )

            return ChatResponse(
                content=content,
                model="web-search",
                provider=settings.llm_provider,
            )

        # =====================================================
        # OTHER REGISTERED TOOLS
        # =====================================================

        if tool_name:

            tool = (
                tool_registry.get(
                    tool_name
                )
            )

            if tool is None:

                print(
                    "[ChatService] Tool not found: "
                    f"{tool_name}"
                )

                raise ValueError(
                    f"Tool '{tool_name}' "
                    "is not registered."
                )

            try:

                result = tool(
                    user_message
                )

            except TypeError:

                result = tool()

            # -------------------------------------------------
            # ASYNC TOOL
            # -------------------------------------------------

            if hasattr(
                result,
                "__await__",
            ):

                result = await result

            # -------------------------------------------------
            # STRING
            # -------------------------------------------------

            if not isinstance(
                result,
                str,
            ):

                result = str(
                    result
                )

            return ChatResponse(
                content=result,
                model="tool",
                provider=settings.llm_provider,
            )

        # =====================================================
        # NORMAL LLM
        # =====================================================

        print(
            "[ChatService] Sending request "
            "to normal LLM."
        )

        return await self.provider.chat(
            request
        )

    # =========================================================
    # STREAMING CHAT
    # =========================================================

    async def stream_chat(
        self,
        request: ChatRequest,
    ):

        if not request.messages:

            raise ValueError(
                "No messages provided."
            )

        user_message = (
            request
            .messages[-1]
            .content
        )

        print(
            f"[ChatService] User: "
            f"{user_message}"
        )

        # =====================================================
        # ROUTER
        # =====================================================

        tool_name = (
            agent_router.route(
                user_message
            )
        )

        print(
            f"[ChatService] Tool: "
            f"{tool_name}"
        )

        # =====================================================
        # SYSTEM
        # =====================================================

        system_commands = {

            "open_file_explorer",

            "open_drive",

            "open_folder",

            "open_application",

        }

        if tool_name in system_commands:

            response = (
                await self._system_command(
                    command=tool_name,
                    user_message=user_message,
                )
            )

            yield response.content

            return

        # =====================================================
        # WEB SEARCH
        # =====================================================

        if tool_name == "web_search":

            response = (
                await self.chat(
                    request
                )
            )

            yield response.content

            return

        # =====================================================
        # OTHER REGISTERED TOOLS
        # =====================================================

        if tool_name:

            tool = (
                tool_registry.get(
                    tool_name
                )
            )

            if tool is None:

                raise ValueError(
                    f"Tool '{tool_name}' "
                    "is not registered."
                )

            try:

                result = tool(
                    user_message
                )

            except TypeError:

                result = tool()

            if hasattr(
                result,
                "__await__",
            ):

                result = await result

            if not isinstance(
                result,
                str,
            ):

                result = str(
                    result
                )

            yield result

            return

        # =====================================================
        # NORMAL LLM STREAM
        # =====================================================

        async for token in (
            self.provider.stream_chat(
                request
            )
        ):

            yield token

    # =========================================================
    # CLOSE
    # =========================================================

    async def close(
        self,
    ):

        await self.provider.close()


# =============================================================
# SINGLETON
# =============================================================

chat_service = ChatService()