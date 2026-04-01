"""
app/core/database.py
--------------------
WHAT IS THIS?
  Sets up the connection between your app and PostgreSQL.
  Think of it as the phone line — this file opens it and keeps it ready.

KEY CONCEPTS:

  async / await
    Normal Python runs one thing at a time and WAITS for each operation.
    Async Python can do OTHER work while waiting for the database to respond.
    For a web server handling hundreds of requests, this is a huge speed win.

  SQLAlchemy
    A Python library that lets you write Python instead of raw SQL.
    Instead of:  SELECT * FROM wallets WHERE id = 1
    You write:   session.get(Wallet, 1)

  create_async_engine
    The engine manages a "pool" of database connections.
    A pool keeps several connections open and ready so each request
    doesn't have to wait to open a brand new connection every time.

  AsyncSession
    One "conversation" with the database.
    It tracks everything you read and write until you commit or roll back.

  get_db (the dependency)
    FastAPI calls get_db() for every request that needs a DB session.
    It hands the session to your route, then automatically closes it
    when the request finishes — even if an error happened.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# ── Engine ────────────────────────────────────────────────────────────────────
# echo=True logs every SQL statement to the console — great for debugging
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    pool_size=10,     # keep 10 connections open and ready
    max_overflow=20,  # allow 20 extra connections if the pool is full
)

# ── Session factory ───────────────────────────────────────────────────────────
# Call AsyncSessionLocal() to get a new session
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep objects usable after commit
)


# ── Base model ────────────────────────────────────────────────────────────────
# All database models (Wallet, Transaction) inherit from this.
# It tells SQLAlchemy "this Python class maps to a database table".
class Base(DeclarativeBase):
    pass


# ── Dependency ────────────────────────────────────────────────────────────────
# FastAPI calls this automatically for routes that declare:
#   db: AsyncSession = Depends(get_db)
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session           # hand the session to the route
            await session.commit()  # save everything if no error occurred
        except Exception:
            await session.rollback()  # undo everything if an error occurred
            raise
