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

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(system_router)
api_v1_router.include_router(agent_router)
api_v1_router.include_router(tools_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(tasks_router)

__all__ = ["api_v1_router", "ws_router"]
