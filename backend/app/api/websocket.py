"""
app/api/websocket.py
---------------------
WHAT IS THIS?
  The WebSocket endpoint — where browsers connect to receive real-time updates.

  URL: ws://localhost:8000/api/v1/ws/{user_id}

  Once connected:
  - Server registers the connection in WebSocketManager
  - Browser just waits — the server pushes updates to it
  - When browser disconnects (tab closed, etc.) we clean up

KEEPALIVE — PING every 30 seconds:
  WebSocket connections can silently drop (network issues, proxy timeouts).
  We send a ping every 30 seconds to keep the connection alive.
  If sending fails, the connection is dead — we clean it up.
  This is standard practice for production WebSocket servers.
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

PING_INTERVAL = 30  # seconds


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time transaction updates.

    Connect with: ws://localhost:8000/api/v1/ws/{user_id}
    The connection stays open until the client disconnects.
    Updates are pushed automatically when transactions change status.
    """
    await manager.connect(websocket, user_id)

    # Send a confirmation message so the client knows it's connected
    await websocket.send_json({
        "type": "connected",
        "user_id": user_id,
        "message": "Connected. You will receive real-time transaction updates.",
    })

    # Start a background ping task to keep the connection alive
    ping_task = asyncio.create_task(_keepalive(websocket, user_id))

    try:
        while True:
            try:
                # Wait for any message from the client (e.g. pong responses)
                await asyncio.wait_for(websocket.receive_json(), timeout=60)
            except asyncio.TimeoutError:
                continue  # no message yet — keep waiting

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user={user_id}: {e}")
    finally:
        ping_task.cancel()
        manager.disconnect(websocket, user_id)


async def _keepalive(websocket: WebSocket, user_id: str) -> None:
    """Send a ping every PING_INTERVAL seconds to keep the connection alive."""
    try:
        while True:
            await asyncio.sleep(PING_INTERVAL)
            await websocket.send_json({"type": "ping"})
    except asyncio.CancelledError:
        pass  # normal shutdown
    except Exception:
        pass  # connection already dead
