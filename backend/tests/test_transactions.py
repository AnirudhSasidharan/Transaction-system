import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.holding import Holding  # noqa: F401
from app.models.ledger_entry import LedgerEntry  # noqa: F401
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User  # noqa: F401
from app.models.wallet import Wallet
from app.schemas.transaction import TransactionCreate
from app.schemas.wallet import WalletCreate
from app.services.holding_service import HoldingService, InsufficientAssetError
from app.services.transaction_service import TransactionService
from app.services.wallet_service import InsufficientBalanceError, WalletService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_wallet(db_session):
    data = WalletCreate(user_id="user_001", initial_balance=Decimal("500.00"))
    wallet = await WalletService.create_wallet(db_session, data)

    assert wallet.id is not None
    assert wallet.user_id == "user_001"
    assert wallet.balance == Decimal("500.00")


@pytest.mark.asyncio
async def test_deduct_balance(db_session):
    data = WalletCreate(user_id="user_002", initial_balance=Decimal("1000.00"))
    wallet = await WalletService.create_wallet(db_session, data)

    updated = await WalletService.deduct_balance(db_session, wallet.id, Decimal("300.00"))
    assert updated.balance == Decimal("700.00")


@pytest.mark.asyncio
async def test_insufficient_balance_raises(db_session):
    data = WalletCreate(user_id="user_003", initial_balance=Decimal("100.00"))
    wallet = await WalletService.create_wallet(db_session, data)

    with pytest.raises(InsufficientBalanceError):
        await WalletService.deduct_balance(db_session, wallet.id, Decimal("500.00"))


@pytest.mark.asyncio
async def test_add_balance(db_session):
    data = WalletCreate(user_id="user_004", initial_balance=Decimal("200.00"))
    await WalletService.create_wallet(db_session, data)

    updated = await WalletService.add_balance(db_session, "user_004", Decimal("300.00"))
    assert updated.balance == Decimal("500.00")


@pytest.mark.asyncio
async def test_create_transaction_returns_pending(db_session):
    wallet_data = WalletCreate(user_id="user_005", initial_balance=Decimal("1000.00"))
    await WalletService.create_wallet(db_session, wallet_data)

    with patch("app.services.transaction_service.enqueue_transaction", new_callable=AsyncMock) as mock_enqueue:
        tx_data = TransactionCreate(
            user_id="user_005",
            transaction_type=TransactionType.BUY,
            amount=Decimal("200.00"),
            asset_symbol="BTC",
        )
        transaction = await TransactionService.create_transaction(db_session, tx_data, idempotency_key="abc-123")

        assert transaction.status == TransactionStatus.PENDING
        assert transaction.amount == Decimal("200.00")
        assert transaction.idempotency_key == "abc-123"
        mock_enqueue.assert_called_once_with(str(transaction.id))


@pytest.mark.asyncio
async def test_idempotency_returns_existing_transaction(db_session):
    wallet_data = WalletCreate(user_id="user_009", initial_balance=Decimal("1000.00"))
    await WalletService.create_wallet(db_session, wallet_data)

    with patch("app.services.transaction_service.enqueue_transaction", new_callable=AsyncMock) as mock_enqueue:
        tx_data = TransactionCreate(
            user_id="user_009",
            transaction_type=TransactionType.BUY,
            amount=Decimal("50.00"),
            asset_symbol="ETH",
        )
        tx1 = await TransactionService.create_transaction(db_session, tx_data, idempotency_key="same-key")
        tx2 = await TransactionService.create_transaction(db_session, tx_data, idempotency_key="same-key")

        assert tx1.id == tx2.id
        mock_enqueue.assert_called_once()


@pytest.mark.asyncio
async def test_send_transaction_requires_recipient():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TransactionCreate(
            user_id="user_006",
            transaction_type=TransactionType.SEND,
            amount=Decimal("100.00"),
        )


@pytest.mark.asyncio
async def test_buy_transaction_requires_asset_symbol():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TransactionCreate(
            user_id="user_007",
            transaction_type=TransactionType.BUY,
            amount=Decimal("100.00"),
        )


@pytest.mark.asyncio
async def test_sell_transaction_requires_asset_symbol():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TransactionCreate(
            user_id="user_007",
            transaction_type=TransactionType.SELL,
            amount=Decimal("100.00"),
        )


@pytest.mark.asyncio
async def test_update_transaction_status(db_session):
    wallet_data = WalletCreate(user_id="user_008", initial_balance=Decimal("1000.00"))
    await WalletService.create_wallet(db_session, wallet_data)

    with patch("app.services.transaction_service.enqueue_transaction", new_callable=AsyncMock):
        tx_data = TransactionCreate(
            user_id="user_008",
            transaction_type=TransactionType.BUY,
            amount=Decimal("50.00"),
            asset_symbol="ETH",
        )
        transaction = await TransactionService.create_transaction(db_session, tx_data)

    updated = await TransactionService.update_transaction_status(db_session, transaction.id, TransactionStatus.SUCCESS)

    assert updated.status == TransactionStatus.SUCCESS
    assert updated.processed_at is not None


@pytest.mark.asyncio
async def test_holding_add_and_remove(db_session):
    wallet_data = WalletCreate(user_id="user_hold_001", initial_balance=Decimal("1000.00"))
    wallet = await WalletService.create_wallet(db_session, wallet_data)

    holding = await HoldingService.add_asset(
        db_session,
        wallet_id=wallet.id,
        asset_symbol="BTC",
        quantity=Decimal("0.01000000"),
        unit_price=Decimal("60000.00"),
    )
    assert holding.quantity == Decimal("0.01000000")

    holding = await HoldingService.remove_asset(
        db_session,
        wallet_id=wallet.id,
        asset_symbol="BTC",
        quantity=Decimal("0.00500000"),
    )
    assert holding.quantity == Decimal("0.00500000")


@pytest.mark.asyncio
async def test_holding_remove_insufficient_raises(db_session):
    wallet_data = WalletCreate(user_id="user_hold_002", initial_balance=Decimal("1000.00"))
    wallet = await WalletService.create_wallet(db_session, wallet_data)

    await HoldingService.add_asset(
        db_session,
        wallet_id=wallet.id,
        asset_symbol="ETH",
        quantity=Decimal("0.50000000"),
        unit_price=Decimal("3000.00"),
    )

    with pytest.raises(InsufficientAssetError):
        await HoldingService.remove_asset(
            db_session,
            wallet_id=wallet.id,
            asset_symbol="ETH",
            quantity=Decimal("0.60000000"),
        )
