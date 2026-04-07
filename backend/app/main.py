"""
app/main.py
-----------
WHAT IS THIS?
  The entry point of the entire application.
  This is where FastAPI is created, all routers are registered,
  and background tasks (worker + Redis listener) are started.

KEY CONCEPTS:

  lifespan (startup / shutdown):
    Code BEFORE yield → runs when the server starts
    Code AFTER yield  → runs when the server stops
    Guarantees the worker and Redis listener always shut down cleanly.

  asyncio.create_task():
    Runs a coroutine as a background task alongside the web server.
    The worker and Redis listener run "in the background" —
    they don't block the API from serving requests.

  CORS (Cross-Origin Resource Sharing):
    Browsers block requests to a different domain/port by default.
    CORSMiddleware tells the browser "this API allows requests from
    these other origins."
    Required if your React frontend runs on port 3000
    and your API runs on port 8000.

  API versioning (/api/v1/):
    All routes are prefixed with /api/v1/
    If you ever make breaking changes, add /api/v2/ alongside.
    Old clients keep using v1. New clients use v2.
    No one breaks.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, wallets, transactions, websocket, portfolio
from app.services.websocket_manager import redis_listener
from app.workers.transaction_worker import worker_loop

# Configure logging — shows timestamp, level, file, message
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background tasks on startup. Stop them cleanly on shutdown."""
    logger.info("Starting up transaction system...")

    # Start Redis pub/sub listener (receives updates from worker, sends to WebSocket)
    listener_task = asyncio.create_task(
        redis_listener(), name="redis-listener"
    )

    # Start the transaction worker (processes the queue)
    worker_task = asyncio.create_task(
        worker_loop(), name="transaction-worker"
    )

    logger.info("Background tasks started: redis-listener, transaction-worker")

    yield  # ← server runs here, handling all incoming requests

    # Shutdown — cancel background tasks gracefully
    logger.info("Shutting down...")
    listener_task.cancel()
    worker_task.cancel()
    await asyncio.gather(listener_task, worker_task, return_exceptions=True)
    logger.info("Shutdown complete")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Real-Time Transaction System",
    description=(
        "Payments and trading simulator with async processing, "
        "real-time WebSocket updates, and double-spend prevention."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React (Create React App)
        "http://localhost:5173",   # React (Vite)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(wallets.router,      prefix=API_PREFIX)
app.include_router(transactions.router, prefix=API_PREFIX)
app.include_router(websocket.router,    prefix=API_PREFIX)
app.include_router(auth.router,         prefix=API_PREFIX)
app.include_router(portfolio.router,    prefix=API_PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    """
    Simple health check endpoint.
    Load balancers and Docker health checks call this to verify the app is alive.
    Returns 200 OK if the server is running.
    """
    return {"status": "ok", "service": "transaction-system"}


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", tags=["system"])
async def root():
    return {
        "message": "Real-Time Transaction System API",
        "docs": "/docs",     # Swagger UI — interactive API explorer
        "redoc": "/redoc",   # ReDoc — alternative docs viewer
        "health": "/health",
    }
