"""
app/services/transaction_service.py
-------------------------------------
WHAT IS THIS?
  Handles creating transactions and querying them.

IMPORTANT — creating a transaction does NOT process it immediately.
  We just:
    1. Validate the wallet exists
    2. Save the transaction as PENDING in the DB
    3. Push its ID onto the Redis queue
    4. Return immediately — the API responds fast

  The worker picks it up from the queue and processes it asynchronously.
  This is the event-driven pattern:

    API → saves PENDING → pushes to queue → returns fast (~5ms)
    Worker → pops from queue → processes → updates DB → publishes WebSocket

WHY SEPARATE CREATE FROM PROCESS?
  Processing can be slow: deducting balance, crediting recipient,
  calling external APIs, retrying on failure.
  The API should never do slow work — it returns immediately
  and lets the background worker handle everything.

PAGINATION (limit / offset):
  Databases can have millions of rows.
  You never fetch all of them at once.
  limit=50  → return at most 50 rows
  offset=0  → start from the beginning
  offset=50 → skip the first 50 (page 2)
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionStatus
from app.schemas.transaction import TransactionCreate
from app.services.wallet_service import WalletService
from app.core.redis_client import enqueue_transaction


class TransactionService:

    @staticmethod
    async def create_transaction(
        db: AsyncSession,
        data: TransactionCreate,
    ) -> Transaction:
        """
        Create a PENDING transaction and enqueue it for processing.

        Steps:
        1. Find the wallet (fail fast if not found)
        2. Create transaction row with status=PENDING
        3. Push ID to Redis queue
        4. Return the pending transaction to the caller
        """
        # Step 1 — validate wallet exists before creating transaction
        wallet = await WalletService.get_wallet_by_user(db, data.user_id)

        # Step 2 — create the transaction record
        transaction = Transaction(
            wallet_id=wallet.id,
            transaction_type=data.transaction_type,
            amount=data.amount,
            status=TransactionStatus.PENDING,
            recipient_user_id=data.recipient_user_id,
            asset_symbol=data.asset_symbol,
        )
        db.add(transaction)
        await db.flush()  # get the auto-generated transaction.id

        # Step 3 — push to Redis queue (fast, non-blocking)
        await enqueue_transaction(str(transaction.id))

        return transaction

    @staticmethod
    async def get_transaction(
        db: AsyncSession,
        transaction_id: int,
    ) -> Transaction | None:
        """Fetch a single transaction by ID. Returns None if not found."""
        result = await db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_transactions(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:
        """
        Get paginated transaction history for a user.

        limit/offset pagination:
          limit=10, offset=0  → rows 1-10  (page 1)
          limit=10, offset=10 → rows 11-20 (page 2)
          limit=10, offset=20 → rows 21-30 (page 3)
        """
        wallet = await WalletService.get_wallet_by_user(db, user_id)

        result = await db.execute(
            select(Transaction)
            .where(Transaction.wallet_id == wallet.id)
            .order_by(Transaction.created_at.desc())  # newest first
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
        """
        Update a transaction's status.
        Called by the worker after processing.
        Sets processed_at to the current UTC time.
        """
        transaction = await TransactionService.get_transaction(db, transaction_id)
        if not transaction:
            return None

        transaction.status = status
        transaction.processed_at = datetime.utcnow()
        if failure_reason:
            transaction.failure_reason = failure_reason

        await db.flush()
        return transaction
