"""
Prompt Generator Tool for Friday AI Assistant.
Enables Friday to generate master-grade prompts for Midjourney, FLUX.1, SDXL, LLMs, and Coding.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.services.prompt_generator_service import prompt_generator_service


class PromptGeneratorTool(BaseTool):
    name: str = "generate_prompt"
    description: str = "Generate master-grade, highly-detailed prompts for AI Image models (Midjourney, Flux, SDXL), LLM Agents, Coding, or Video."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    category: str = "ai_generation"

    async def execute(self, topic: str, target_type: Optional[str] = None, style: str = "cinematic", **kwargs: Any) -> ToolResult:
        try:
            res = await prompt_generator_service.generate(user_query=topic, target_type=target_type, style=style)
            text_output = prompt_generator_service.format_to_natural_speech(res)
            return ToolResult(
                tool_name=self.name,
                success=True,
                data=res,
                metadata={"summary": f"Generated {res.get('category', 'custom')} prompt for: '{topic[:60]}'"}
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Prompt generation error: {str(e)}"
            )


prompt_generator_tool = PromptGeneratorTool()
