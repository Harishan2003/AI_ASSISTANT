"""
BFS Best Face Swap Tool for Friday AI Assistant.
Enables Friday to perform photorealistic face swapping on images.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.services.face_swap_service import face_swap_service


class FaceSwapTool(BaseTool):
    name: str = "face_swap"
    description: str = "Swap a source face onto a target portrait/body image using Alissonerdx/BFS-Best-Face-Swap."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    category: str = "ai_generation"

    async def execute(self, source_face: str, target_image: str, enhance: bool = True, **kwargs: Any) -> ToolResult:
        try:
            res = await face_swap_service.swap_face(
                source_face_image=source_face,
                target_body_image=target_image,
                enhance_quality=enhance
            )
            if res.get("success"):
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    data=res,
                    metadata={"summary": f"Generated face swap saved to: {res.get('output_path')}"}
                )
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=res.get("error", "Face swap failed.")
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Face swap tool error: {str(e)}"
            )


face_swap_tool = FaceSwapTool()
