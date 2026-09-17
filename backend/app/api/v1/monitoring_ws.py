"""
WebSocket endpoint for real-time live system telemetry broadcasting.
"""

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Real-time Telemetry"])


@router.websocket("/ws/telemetry")
async def websocket_telemetry_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected to telemetry WebSocket.")
    try:
        while True:
            snapshot = monitoring_service.get_quick_snapshot()
            await websocket.send_text(json.dumps(snapshot, default=str))
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        logger.info("Client disconnected from telemetry WebSocket.")
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
