from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis_client import enqueue_transaction
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.transaction import TransactionCreate
from app.services.wallet_service import WalletService


class TransactionService:

    @staticmethod
    async def create_transaction(
        db: AsyncSession,
        data: TransactionCreate,
        idempotency_key: str | None = None,
        actor_user_id: str | None = None,
    ) -> Transaction:
        user_id = data.user_id or actor_user_id
        if not user_id:
            raise ValueError("user_id is required")
        if actor_user_id and data.user_id and data.user_id != actor_user_id:
            raise ValueError("user_id must match authenticated user")

        if float(data.amount) > settings.MAX_TRANSACTION_AMOUNT:
            raise ValueError(f"Amount exceeds max transaction limit ({settings.MAX_TRANSACTION_AMOUNT})")

        wallet = await WalletService.get_wallet_by_user(db, user_id)

        if idempotency_key:
            existing = await db.execute(
                select(Transaction).where(
                    Transaction.wallet_id == wallet.id,
                    Transaction.idempotency_key == idempotency_key,
                )
            )
            existing_tx = existing.scalar_one_or_none()
            if existing_tx:
                return existing_tx

        transaction = Transaction(
            wallet_id=wallet.id,
            transaction_type=data.transaction_type,
            amount=data.amount,
            status=TransactionStatus.PENDING,
            recipient_user_id=data.recipient_user_id,
            asset_symbol=data.asset_symbol.upper() if data.asset_symbol else None,
            idempotency_key=idempotency_key,
            max_attempts=settings.DEFAULT_MAX_ATTEMPTS,
        )
        db.add(transaction)
        await db.flush()

        await enqueue_transaction(str(transaction.id))
        return transaction

    @staticmethod
    async def get_transaction(db: AsyncSession, transaction_id: int) -> Transaction | None:
        result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_transactions(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:
        wallet = await WalletService.get_wallet_by_user(db, user_id)

        result = await db.execute(
            select(Transaction)
            .where(Transaction.wallet_id == wallet.id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_transaction_status(
        db: AsyncSession,
        transaction_id: int,
        status: TransactionStatus,
        failure_reason: str | None = None,
    ) -> Transaction | None:
        transaction = await TransactionService.get_transaction(db, transaction_id)
        if not transaction:
            return None

        transaction.status = status
        transaction.processed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if failure_reason:
            transaction.failure_reason = failure_reason

        await db.flush()
        return transaction
