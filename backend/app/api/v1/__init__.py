"""
FastAPI v1 API Routers aggregation.
"""

from fastapi import APIRouter

from app.api.v1.system_api import router as system_router
from app.api.v1.agent_api import router as agent_router
from app.api.v1.tools_api import router as tools_router
from app.api.v1.audit_api import router as audit_router
from app.api.v1.tasks_api import router as tasks_router
from app.api.v1.monitoring_ws import router as ws_router
from app.api.v1.prompt_api import router as prompt_router
from app.api.v1.vision_models_api import router as vision_models_router
from app.api.v1.conversations_api import router as conversations_router
from app.api.v1.memory import router as memory_router
from app.api.v1.voice import router as voice_router
from app.mcp.router import mcp_api_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(system_router)
api_v1_router.include_router(agent_router)
api_v1_router.include_router(tools_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(tasks_router)
api_v1_router.include_router(prompt_router)
api_v1_router.include_router(vision_models_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(memory_router)
api_v1_router.include_router(voice_router)
api_v1_router.include_router(mcp_api_router)

__all__ = ["api_v1_router", "ws_router"]
