"""
app/services/websocket_manager.py
----------------------------------
WHAT IS WEBSOCKET?
  Normal HTTP:
    Browser asks → Server answers → connection closes
    Browser must ask AGAIN to get updates (polling — we avoid this)

  WebSocket:
    Browser connects once → connection stays open permanently
    Server can PUSH messages to the browser any time without being asked
    Perfect for: live transaction status, stock tickers, chat apps

HOW THIS WORKS IN OUR SYSTEM:
  1. Browser connects to ws://localhost:8000/api/v1/ws/{user_id}
  2. WebSocketManager registers this connection
  3. Worker finishes a transaction → publishes update to Redis pub/sub
  4. redis_listener() receives it → finds the user's WebSocket connections
  5. Sends the JSON update directly to the browser

  The browser NEVER polls. It just receives updates automatically.

KEY CONCEPT — WebSocketManager:
  Tracks which WebSocket connections belong to which user.
  Stored as a dict: { "user123": [ws_conn_1, ws_conn_2] }
  One user can have multiple browser tabs open — we send to all of them.

KEY CONCEPT — redis_listener():
  A background task running forever.
  Subscribed to the Redis pub/sub channel.
  When the worker publishes an update, this function receives it
  and forwards it to the correct WebSocket connection.
"""

import asyncio
import json
import logging

from fastapi import WebSocket
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.redis_client import TRANSACTION_CHANNEL

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages all active WebSocket connections.
    Maps user_id → list of open WebSocket connections.
    """

    def __init__(self):
        # { user_id: [WebSocket, WebSocket, ...] }
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Accept a new WebSocket connection and register it."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected: user={user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a WebSocket when the client disconnects."""
        if user_id in self.active_connections:
            self.active_connections[user_id] = [
                ws for ws in self.active_connections[user_id]
                if ws != websocket
            ]
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected: user={user_id}")

    async def send_to_user(self, user_id: str, data: dict) -> None:
        """Send a JSON message to all connections for a specific user."""
        connections = self.active_connections.get(user_id, [])
        dead = []

        for websocket in connections:
            try:
                await websocket.send_json(data)
            except Exception:
                dead.append(websocket)

        # Clean up any broken connections
        for ws in dead:
            self.disconnect(ws, user_id)


# Single global instance — shared across all routes
manager = WebSocketManager()


async def redis_listener() -> None:
    """
    Background task that runs forever, listening to Redis pub/sub.

    When the worker publishes a transaction update to Redis,
    this function receives it and forwards it to the right WebSocket client.

    Flow:
      Worker publishes → Redis → this function → WebSocket → browser
    """
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()

    await pubsub.subscribe(TRANSACTION_CHANNEL)
    logger.info(f"Redis listener subscribed to: {TRANSACTION_CHANNEL}")

    try:
        async for message in pubsub.listen():
            # pubsub.listen() yields different message types
            # "message" is the type for actual published data
            if message["type"] != "message":
                continue

            try:
                data = json.loads(message["data"])
                user_id = data.get("user_id")
                if user_id:
                    await manager.send_to_user(user_id, data)
                    logger.debug(f"Forwarded update to user={user_id}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from Redis: {message['data']}")
            except Exception as e:
                logger.error(f"Error processing Redis message: {e}")

    except asyncio.CancelledError:
        logger.info("Redis listener shutting down")
        await pubsub.unsubscribe(TRANSACTION_CHANNEL)
        await redis_client.aclose()
