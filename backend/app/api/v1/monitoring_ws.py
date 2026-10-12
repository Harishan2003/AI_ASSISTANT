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
        import psutil
        while True:
            snapshot = monitoring_service.get_quick_snapshot()
            await websocket.send_text(json.dumps(snapshot, default=str))

            # Adaptive power interval (8s on battery, 3s on AC power) to minimize CPU wakeups
            on_battery = False
            try:
                b = psutil.sensors_battery()
                if b and not b.power_plugged:
                    on_battery = True
            except Exception:
                pass

            sleep_dur = 8.0 if on_battery else 3.0
            await asyncio.sleep(sleep_dur)
    except WebSocketDisconnect:
        logger.info("Client disconnected from telemetry WebSocket.")
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
