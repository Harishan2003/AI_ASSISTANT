# Module: backend.app.agents.coding_agent
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.coding_agent_service import coding_agent_service

logger = logging.getLogger("friday.agents.coding")


class CodingAgent:
    """
    Dedicated autonomous coding agent for generating, debugging, refactoring,
    and explaining production-grade software code.
    """

    def __init__(self):
        self.name = "CodingAgent"
        self.service = coding_agent_service

    async def handle_task(
        self,
        query: str,
        language: Optional[str] = None,
        context: Optional[str] = None,
        task_type: str = "generate",
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Dispatches a coding task to the coding agent service."""
        if task_type == "debug":
            return await self.service.debug_code(code=query, language=language)
        elif task_type == "refactor":
            return await self.service.refactor_code(code=query, instructions=context or "Optimize and clean up code", language=language)
        elif task_type == "explain":
            return await self.service.explain_code(code=query)
        else:
            return await self.service.generate_code(prompt=query, language=language, context=context)

    async def run(self, message: str) -> str:
        """Standard single-message entrypoint."""
        return await self.service.handle_coding_query(message)


coding_agent = CodingAgent()
