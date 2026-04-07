"""
app/core/config.py
------------------
WHAT IS THIS?
  Reads your .env file and loads all settings into one Python object.
  Every other file imports from here instead of calling os.getenv() directly.
  One place to change a setting = safe and predictable.

KEY CONCEPT — pydantic-settings:
  Pydantic validates data types at runtime.
  pydantic-settings extends it to read from environment variables automatically.
  If a required variable is missing it raises a clear error on startup
  instead of crashing later mid-request (fail-fast principle).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # ── Database 
    # postgresql+asyncpg:// tells SQLAlchemy to use the async Postgres driver
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/transactions_db"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── App ───────────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # ── Business rules ────────────────────────────────────────────────────────
    MAX_TRANSACTION_AMOUNT: float = 1_000_000.00
    WORKER_POLL_INTERVAL: int = 1  # seconds between queue checks
    DEFAULT_MAX_ATTEMPTS: int = 3
    TRANSACTION_FEE_RATE: float = 0.0025

    # Tell pydantic-settings to read a .env file automatically
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")



# from app.core.config import settings
settings = Settings()
