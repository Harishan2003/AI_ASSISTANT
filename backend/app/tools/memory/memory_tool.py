"""
Memory management tools for Friday AI Assistant.
Saves and recalls user preferences, facts, and context across sessions.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.database.agent_db import agent_db


class SaveUserFactInput(BaseModel):
    fact: str = Field(..., description="The user fact, preference, or context to remember (e.g. 'User prefers dark mode and Python 3.12')")
    category: str = Field(default="general", description="Category for the fact: 'general', 'hardware', 'preferences', 'projects'")


class SaveUserFactTool(BaseTool):
    name: str = "save_user_memory"
    description: str = "Stores a key fact, user preference, or personal instruction into persistent long-term memory."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = SaveUserFactInput

    def run(self, fact: str, category: str = "general") -> ToolResult:
        success = agent_db.save_fact(fact=fact, category=category)
        if success:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"message": f"Successfully remembered: '{fact}'", "category": category}
            )
        else:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="Failed to save fact to database",
                error_code="MEMORY_SAVE_FAILED"
            )


class RecallUserFactsInput(BaseModel):
    query: Optional[str] = Field(default=None, description="Optional search keyword to filter stored memories")
    category: Optional[str] = Field(default=None, description="Optional category filter")


class RecallUserFactsTool(BaseTool):
    name: str = "recall_user_memories"
    description: str = "Recalls long-term facts, instructions, and user preferences stored in memory."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = RecallUserFactsInput

    def run(self, query: Optional[str] = None, category: Optional[str] = None) -> ToolResult:
        facts = agent_db.get_facts(query=query, category=category)
        return ToolResult(
            tool_name=self.name,
            success=True,
            data={"total_memories": len(facts), "memories": facts}
        )
