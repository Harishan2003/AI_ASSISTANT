"""
Qwen Vision Tool for Friday AI Assistant.
Enables Friday to perform uncensored image analysis, object detection, and visual QA.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.services.qwen_vision_service import qwen_vision_service


class QwenVisionTool(BaseTool):
    name: str = "qwen_vision_inspect"
    description: str = "Analyze images, photos, UI screenshots, or handwritten notes in uncensored, high-fidelity detail using Qwen-Image-2.1."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    category: str = "ai_vision"

    async def execute(self, image_path: str, prompt: str = "Analyze and describe this image thoroughly.", **kwargs: Any) -> ToolResult:
        try:
            res = await qwen_vision_service.analyze_image(image_input=image_path, prompt=prompt)
            if res.get("success"):
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    data=res,
                    metadata={"summary": f"Analyzed image with {res.get('model_used')}"}
                )
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=res.get("error", "Vision inspection failed.")
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Qwen Vision tool error: {str(e)}"
            )


qwen_vision_tool = QwenVisionTool()
