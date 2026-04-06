"""
app/workers/transaction_worker.py
----------------------------------
WHAT IS A WORKER?
  A background task that runs alongside the API server.
  It has one job: pop transaction IDs from the Redis queue and process them.

WHY A SEPARATE WORKER AND NOT PROCESS IN THE ROUTE?
  The API must respond fast — milliseconds.
  Processing a transaction involves:
    - Locking a DB row
    - Deducting balance
    - Crediting recipient
    - Updating status
    - Publishing WebSocket update
  All of this can take 1-2 seconds.
  Doing it in the route would make every client wait.
  The worker does it in the background — client gets a response instantly.

THE COMPLETE FLOW:
  1.  Client  → POST /transactions
  2.  API     → saves Transaction(status=PENDING) in DB
  3.  API     → pushes transaction_id to Redis queue     (~1ms)
  4.  API     → returns 201 PENDING to client            (client is done waiting)
  5.  Worker  → BRPOP unblocks, gets the ID
  6.  Worker  → sets status=PROCESSING, publishes to Redis pub/sub
  7.  Browser → receives "processing" via WebSocket
  8.  Worker  → deducts balance (with SELECT FOR UPDATE lock)
  9.  Worker  → sets status=SUCCESS or FAILURE
  10. Worker  → publishes final status to Redis pub/sub
  11. Browser → receives final update via WebSocket

KEY CONCEPT — BRPOP:
  Blocking Right POP.
  If the queue is empty, BRPOP sleeps and waits.
  When something is pushed in, it wakes up instantly.
  No busy-looping, no wasted CPU.
  timeout=5 means: if nothing arrives in 5 seconds, return None and loop again.
  This lets us check for shutdown signals (CancelledError) regularly.

KEY CONCEPT — ATOMIC processing:
  All DB changes in one transaction — either ALL succeed or ALL are undone.
  You never end up with balance deducted but status still PENDING.
  This is what database transactions are for.
"""

import asyncio
import logging
from datetime import datetime, timezone

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
    """Helper: look up the user_id for a given wallet_id."""
    result = await db.execute(
        select(Wallet).where(Wallet.id == wallet_id)
    )
    wallet = result.scalar_one_or_none()
    return wallet.user_id if wallet else None


async def process_transaction(transaction_id: int) -> None:
    """
    Process one transaction end-to-end.

    Uses TWO separate DB sessions:
      Session 1: mark as PROCESSING (committed immediately so client
                 sees the status change via WebSocket right away)
      Session 2: do the actual work (deduct balance, credit recipient,
                 mark SUCCESS/FAILURE) — all in one atomic transaction
    """

    # ── Session 1: mark PROCESSING ────────────────────────────────────────────
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
        asset = transaction.asset_symbol
        await db.commit()

    # Notify browser: "we're working on it"
    await publish_update(str(transaction_id), {
        "user_id": user_id,
        "transaction_id": transaction_id,
        "status": TransactionStatus.PROCESSING.value,
    })

    # ── Simulate real-world processing delay ──────────────────────────────────
    # In production: call payment gateway, verify asset price, check fraud, etc.
    await asyncio.sleep(1)

    # ── Session 2: business logic (atomic) ────────────────────────────────────
    async with AsyncSessionLocal() as db:
        try:
            if tx_type == TransactionType.SEND:
                # Deduct from sender (locked row)
                updated_wallet = await WalletService.deduct_balance(
                    db, wallet_id, amount
                )
                # Credit the recipient
                if recipient:
                    await WalletService.add_balance(db, recipient, amount)

            elif tx_type == TransactionType.BUY:
                # Deduct the purchase amount (asset delivery out of scope)
                updated_wallet = await WalletService.deduct_balance(
                    db, wallet_id, amount
                )

            # Mark SUCCESS
            await TransactionService.update_transaction_status(
                db, transaction_id, TransactionStatus.SUCCESS
            )
            await db.commit()

            new_balance = str(updated_wallet.balance)
            logger.info(
                f"Transaction {transaction_id} SUCCESS | "
                f"user={user_id} | new_balance={new_balance}"
            )

            # Notify browser: "done, here is your new balance"
            await publish_update(str(transaction_id), {
                "user_id": user_id,
                "transaction_id": transaction_id,
                "status": TransactionStatus.SUCCESS.value,
                "new_balance": new_balance,
                "processed_at": datetime.utcnow().isoformat(),
            })

        except InsufficientBalanceError as e:
            # Rollback balance changes, mark FAILURE
            await db.rollback()
            await TransactionService.update_transaction_status(
                db, transaction_id, TransactionStatus.FAILURE,
                failure_reason=str(e),
            )
            await db.commit()
            logger.warning(f"Transaction {transaction_id} FAILED: {e}")

            # Notify browser: "failed, here is why"
            await publish_update(str(transaction_id), {
                "user_id": user_id,
                "transaction_id": transaction_id,
                "status": TransactionStatus.FAILURE.value,
                "failure_reason": str(e),
            })

        except WalletNotFoundError as e:
            await db.rollback()
            await TransactionService.update_transaction_status(
                db, transaction_id, TransactionStatus.FAILURE,
                failure_reason=str(e),
            )
            await db.commit()
            logger.error(f"Transaction {transaction_id} FAILED (wallet missing): {e}")

            await publish_update(str(transaction_id), {
                "user_id": user_id,
                "transaction_id": transaction_id,
                "status": TransactionStatus.FAILURE.value,
                "failure_reason": str(e),
            })

        except Exception as e:
            await db.rollback()
            logger.error(
                f"Unexpected error on transaction {transaction_id}: {e}",
                exc_info=True,
            )
            try:
                await TransactionService.update_transaction_status(
                    db, transaction_id, TransactionStatus.FAILURE,
                    failure_reason=f"Internal error: {str(e)}",
                )
                await db.commit()
            except Exception:
                pass


async def worker_loop() -> None:
    """
    The main worker loop. Runs forever.

    BRPOP blocks until a transaction ID appears in the queue.
    When it gets one, it processes the transaction, then loops back
    and waits for the next one.

    On shutdown (CancelledError), it exits cleanly.
    """
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    logger.info("Transaction worker started — waiting for jobs...")

    try:
        while True:
            try:
                # BRPOP returns (list_name, value) or None on timeout
                result = await redis_client.brpop(
                    TRANSACTION_QUEUE, timeout=5
                )
                if result is None:
                    continue  # timeout, no jobs yet — loop and wait again

                _, transaction_id_str = result
                transaction_id = int(transaction_id_str)
                logger.info(f"Worker picked up transaction_id={transaction_id}")

                await process_transaction(transaction_id)

            except asyncio.CancelledError:
                raise  # propagate to exit the loop cleanly
            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)
                await asyncio.sleep(1)  # brief pause before retrying

    except asyncio.CancelledError:
        logger.info("Worker received shutdown signal")
    finally:
        await redis_client.aclose()
        logger.info("Worker shut down cleanly")
