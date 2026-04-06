import asyncio
import logging
from datetime import datetime

import redis.asyncio as aioredis
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis_client import TRANSACTION_QUEUE, publish_update
from app.models.transaction import TransactionStatus, TransactionType
from app.models.wallet import Wallet
from app.services.transaction_service import TransactionService
from app.services.wallet_service import (
    WalletService,
    InsufficientBalanceError,
    WalletNotFoundError,
)

logger = logging.getLogger(__name__)


async def _get_user_id_for_wallet(db, wallet_id: int) -> str | None:
    result = await db.execute(select(Wallet).where(Wallet.id == wallet_id))
    wallet = result.scalar_one_or_none()
    return wallet.user_id if wallet else None


async def process_transaction(transaction_id: int) -> None:
    user_id = None

    # ── Step 1: mark PROCESSING ───────────────────────────────────────────────
    try:
        async with AsyncSessionLocal() as db:
            transaction = await TransactionService.update_transaction_status(
                db, transaction_id, TransactionStatus.PROCESSING
            )
            if not transaction:
                logger.error(f"Transaction {transaction_id} not found in DB")
                return

            user_id = await _get_user_id_for_wallet(db, transaction.wallet_id)
            wallet_id = transaction.wallet_id
            amount = transaction.amount
            tx_type = transaction.transaction_type
            recipient = transaction.recipient_user_id
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to mark processing for tx {transaction_id}: {e}")
        return

    await publish_update(str(transaction_id), {
        "user_id": user_id,
        "transaction_id": transaction_id,
        "status": TransactionStatus.PROCESSING.value,
    })

    await asyncio.sleep(1)

    # ── Step 2: business logic ────────────────────────────────────────────────
    try:
        async with AsyncSessionLocal() as db:
            if tx_type == TransactionType.SEND:
                updated_wallet = await WalletService.deduct_balance(db, wallet_id, amount)
                if recipient:
                    await WalletService.add_balance(db, recipient, amount)
            else:
                updated_wallet = await WalletService.deduct_balance(db, wallet_id, amount)

            await TransactionService.update_transaction_status(
                db, transaction_id, TransactionStatus.SUCCESS
            )
            await db.commit()

        new_balance = str(updated_wallet.balance)
        logger.info(f"Transaction {transaction_id} SUCCESS | balance={new_balance}")

        await publish_update(str(transaction_id), {
            "user_id": user_id,
            "transaction_id": transaction_id,
            "status": TransactionStatus.SUCCESS.value,
            "new_balance": new_balance,
            "processed_at": datetime.utcnow().isoformat(),
        })

    except InsufficientBalanceError as e:
        logger.warning(f"Transaction {transaction_id} FAILED: {e}")
        async with AsyncSessionLocal() as db:
            await TransactionService.update_transaction_status(
                db, transaction_id, TransactionStatus.FAILURE, failure_reason=str(e)
            )
            await db.commit()
        await publish_update(str(transaction_id), {
            "user_id": user_id,
            "transaction_id": transaction_id,
            "status": TransactionStatus.FAILURE.value,
            "failure_reason": str(e),
        })

    except Exception as e:
        logger.error(f"Unexpected error on tx {transaction_id}: {e}", exc_info=True)
        async with AsyncSessionLocal() as db:
            await TransactionService.update_transaction_status(
                db, transaction_id, TransactionStatus.FAILURE,
                failure_reason=f"Internal error: {str(e)}"
            )
            await db.commit()


async def worker_loop() -> None:
    logger.info("Transaction worker started — waiting for jobs...")

    while True:
        try:
            # Fresh client every iteration — simple and reliable
            async with aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            ) as redis_client:
                result = await redis_client.brpop(TRANSACTION_QUEUE, timeout=5)

            if result is not None:
                _, transaction_id_str = result
                transaction_id = int(transaction_id_str)
                logger.info(f"Worker dequeued transaction_id={transaction_id}")
                await process_transaction(transaction_id)

        except asyncio.CancelledError:
            logger.info("Worker shutting down cleanly")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            await asyncio.sleep(2)