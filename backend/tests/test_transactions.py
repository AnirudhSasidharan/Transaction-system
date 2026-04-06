"""
tests/test_transactions.py
---------------------------
WHAT ARE TESTS?
  Automated checks that verify your code works correctly.
  You write them once, run them every time you make a change.
  If something breaks, the test fails immediately — before production.

WHAT WE USE:
  pytest         → test runner, discovers and runs test_ functions
  pytest-asyncio → lets us write async test functions
  aiosqlite      → in-memory SQLite DB for fast tests (no Postgres needed)

WHY SQLite FOR TESTS?
  Postgres requires a running server.
  SQLite runs entirely in memory — no setup, no cleanup, instant.
  Tests run in isolation and don't affect your real database.

KEY CONCEPTS:
  @pytest.fixture
    Setup code shared across multiple tests.
    Instead of creating a DB session in every test, define it once.
    pytest injects it wherever you use the parameter name.

  AsyncMock
    Replaces real functions with fakes that return nothing.
    We mock enqueue_transaction so tests don't need a real Redis.
    This keeps tests fast and isolated from external services.

  pytest.raises(SomeError)
    Asserts that a specific exception IS raised.
    If the exception is NOT raised, the test FAILS.
    Used to verify error handling works correctly.
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.schemas.wallet import WalletCreate
from app.schemas.transaction import TransactionCreate
from app.services.wallet_service import WalletService, InsufficientBalanceError
from app.services.transaction_service import TransactionService


# ── In-memory test database ───────────────────────────────────────────────────
# SQLite in memory — no Postgres needed for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """
    Creates a fresh in-memory database for each test.
    Drops all tables after the test so tests don't affect each other.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    # Teardown — drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── Wallet tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_wallet(db_session):
    """A new wallet should be created with the correct balance."""
    data = WalletCreate(user_id="user_001", initial_balance=Decimal("500.00"))
    wallet = await WalletService.create_wallet(db_session, data)

    assert wallet.id is not None
    assert wallet.user_id == "user_001"
    assert wallet.balance == Decimal("500.00")


@pytest.mark.asyncio
async def test_deduct_balance(db_session):
    """Deducting from a wallet should reduce the balance correctly."""
    data = WalletCreate(user_id="user_002", initial_balance=Decimal("1000.00"))
    wallet = await WalletService.create_wallet(db_session, data)
    await db_session.flush()

    updated = await WalletService.deduct_balance(
        db_session, wallet.id, Decimal("300.00")
    )
    assert updated.balance == Decimal("700.00")


@pytest.mark.asyncio
async def test_insufficient_balance_raises(db_session):
    """Deducting more than the balance should raise InsufficientBalanceError."""
    data = WalletCreate(user_id="user_003", initial_balance=Decimal("100.00"))
    wallet = await WalletService.create_wallet(db_session, data)
    await db_session.flush()

    with pytest.raises(InsufficientBalanceError):
        await WalletService.deduct_balance(
            db_session, wallet.id, Decimal("500.00")
        )


@pytest.mark.asyncio
async def test_add_balance(db_session):
    """Adding funds should increase the balance correctly."""
    data = WalletCreate(user_id="user_004", initial_balance=Decimal("200.00"))
    await WalletService.create_wallet(db_session, data)
    await db_session.flush()

    updated = await WalletService.add_balance(
        db_session, "user_004", Decimal("300.00")
    )
    assert updated.balance == Decimal("500.00")


# ── Transaction tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_transaction_returns_pending(db_session):
    """Creating a transaction should save it as PENDING and enqueue it."""
    wallet_data = WalletCreate(user_id="user_005", initial_balance=Decimal("1000.00"))
    await WalletService.create_wallet(db_session, wallet_data)
    await db_session.flush()

    # Mock Redis so we don't need a real Redis connection
    with patch(
        "app.services.transaction_service.enqueue_transaction",
        new_callable=AsyncMock
    ) as mock_enqueue:
        tx_data = TransactionCreate(
            user_id="user_005",
            transaction_type=TransactionType.BUY,
            amount=Decimal("200.00"),
            asset_symbol="BTC",
        )
        transaction = await TransactionService.create_transaction(db_session, tx_data)

        # Status must be PENDING immediately
        assert transaction.status == TransactionStatus.PENDING
        assert transaction.amount == Decimal("200.00")

        # enqueue must have been called with the transaction ID
        mock_enqueue.assert_called_once_with(str(transaction.id))


@pytest.mark.asyncio
async def test_send_transaction_requires_recipient():
    """A send transaction without recipient_user_id should fail validation."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        TransactionCreate(
            user_id="user_006",
            transaction_type=TransactionType.SEND,
            amount=Decimal("100.00"),
            # Missing recipient_user_id — should raise
        )


@pytest.mark.asyncio
async def test_buy_transaction_requires_asset_symbol():
    """A buy transaction without asset_symbol should fail validation."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        TransactionCreate(
            user_id="user_007",
            transaction_type=TransactionType.BUY,
            amount=Decimal("100.00"),
            # Missing asset_symbol — should raise
        )


@pytest.mark.asyncio
async def test_update_transaction_status(db_session):
    """Updating a transaction status should persist and set processed_at."""
    wallet_data = WalletCreate(user_id="user_008", initial_balance=Decimal("1000.00"))
    await WalletService.create_wallet(db_session, wallet_data)
    await db_session.flush()

    with patch(
        "app.services.transaction_service.enqueue_transaction",
        new_callable=AsyncMock
    ):
        tx_data = TransactionCreate(
            user_id="user_008",
            transaction_type=TransactionType.BUY,
            amount=Decimal("50.00"),
            asset_symbol="ETH",
        )
        transaction = await TransactionService.create_transaction(db_session, tx_data)

    updated = await TransactionService.update_transaction_status(
        db_session, transaction.id, TransactionStatus.SUCCESS
    )

    assert updated.status == TransactionStatus.SUCCESS
    assert updated.processed_at is not None
