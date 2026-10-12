"""
AI Image Generation Tool for Friday AI Assistant.
Generates images using FLUX.1 Turbo, SDXL, and Pollinations Engine.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.services.image_generation_service import image_generation_service


class ImageGenerationTool(BaseTool):
    name: str = "generate_image"
    description: str = "Generate high-resolution images, illustrations, sci-fi HUDs, wallpapers, and photorealistic art using FLUX.1 and SDXL."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    category: str = "ai_generation"

    async def execute(self, prompt: str, width: int = 1024, height: int = 1024, **kwargs: Any) -> ToolResult:
        try:
            res = await image_generation_service.generate_image(prompt=prompt, width=width, height=height)
            if res.get("success"):
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    data=res,
                    metadata={"summary": f"Generated image for: '{prompt[:60]}'"}
                )
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=res.get("error", "Image generation failed.")
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Image generation error: {str(e)}"
            )


image_generation_tool = ImageGenerationTool()
