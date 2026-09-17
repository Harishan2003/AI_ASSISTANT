# Module: backend.app.api.router
from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.memory import router as memory_router

api_router = APIRouter()

api_router.include_router(chat_router)
api_router.include_router(memory_router)