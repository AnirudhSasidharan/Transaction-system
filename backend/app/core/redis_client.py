"""
app/core/redis_client.py
------------------------
WHAT IS THIS?
  Redis is an in-memory database — it stores data in RAM instead of on disk,
  making it extremely fast (microseconds vs milliseconds for Postgres).

  We use Redis for TWO things in this project:

  1. QUEUE
     A list of transaction IDs waiting to be processed.
     The API pushes an ID in → the worker pops an ID out and processes it.
     This is the "API → Queue → Worker" part of the event-driven flow.

  2. PUB/SUB (publish / subscribe)
     When the worker finishes a transaction, it "publishes" a message
     to a channel — like a radio broadcast.
     The WebSocket manager "subscribes" to that channel and receives
     the message instantly, then forwards it to the browser.
     This is how the frontend gets real-time updates WITHOUT polling.

KEY CONCEPTS:

  pub/sub
    Publisher:  "Transaction 42 is now SUCCESS" → broadcasts to channel
    Subscriber: "I was listening, I got it"     → forwards to WebSocket clients

  LPUSH / BRPOP
    LPUSH: push to the LEFT of a Redis list   (API adds jobs)
    BRPOP: blocking pop from RIGHT of list    (worker waits for jobs)
    Together they make a First-In-First-Out queue.

  Connection pool
    Instead of opening a new Redis connection for every request,
    the pool keeps several connections open and shares them.
"""

import json
import redis.asyncio as aioredis

from app.core.config import settings


# ── Connection pool ───────────────────────────────────────────────────────────
redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    decode_responses=True,  # return strings instead of raw bytes
)


def get_redis() -> aioredis.Redis:
    """Return a Redis client using the shared connection pool."""
    return aioredis.Redis(connection_pool=redis_pool)


# ── Queue helpers ─────────────────────────────────────────────────────────────
TRANSACTION_QUEUE = "transactions:queue"  # the Redis list key


async def enqueue_transaction(transaction_id: str) -> None:
    """
    Push a transaction ID onto the queue for the worker to pick up.
    The API calls this after saving the transaction as PENDING.
    """
    r = get_redis()
    await r.lpush(TRANSACTION_QUEUE, transaction_id)


# ── Pub/Sub helpers ───────────────────────────────────────────────────────────
TRANSACTION_CHANNEL = "transactions:updates"  # the pub/sub channel name


async def publish_update(transaction_id: str, data: dict) -> None:
    """
    Broadcast a transaction status update to all WebSocket listeners.

    Example data:
      {"user_id": "user_001", "transaction_id": 42, "status": "success", "new_balance": "800.00"}

    The WebSocket manager receives this and forwards it to the right browser.
    """
    r = get_redis()
    message = json.dumps({"transaction_id": transaction_id, **data})
    await r.publish(TRANSACTION_CHANNEL, message)
