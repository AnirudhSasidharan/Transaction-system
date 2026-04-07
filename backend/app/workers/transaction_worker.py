import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN

import redis.asyncio as aioredis
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis_client import (
    TRANSACTION_QUEUE,
    dead_letter_transaction,
    enqueue_transaction,
    publish_update,
)
from app.models.ledger_entry import LedgerEntryType
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.wallet import Wallet
from app.services.holding_service import HoldingService, InsufficientAssetError
from app.services.ledger_service import LedgerService
from app.services.price_service import PriceService, UnsupportedAssetError
from app.services.wallet_service import (
    WalletService,
    InsufficientBalanceError,
    WalletNotFoundError,
)

logger = logging.getLogger(__name__)


def _now_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _get_user_id_for_wallet(db, wallet_id: int) -> str | None:
    result = await db.execute(select(Wallet).where(Wallet.id == wallet_id))
    wallet = result.scalar_one_or_none()
    return wallet.user_id if wallet else None


async def _mark_processing(transaction_id: int) -> tuple[Transaction | None, str | None]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .with_for_update()
        )
        tx = result.scalar_one_or_none()
        if tx is None:
            return None, None

        user_id = await _get_user_id_for_wallet(db, tx.wallet_id)

        if tx.status in {TransactionStatus.SUCCESS, TransactionStatus.FAILURE}:
            return tx, user_id

        tx.attempt_count += 1
        tx.status = TransactionStatus.PROCESSING
        tx.failure_reason = None
        await db.commit()
        await db.refresh(tx)
        return tx, user_id


async def _finalize_failure(
    transaction_id: int,
    reason: str,
    user_id: str | None,
    retryable: bool,
) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .with_for_update()
        )
        tx = result.scalar_one_or_none()
        if tx is None:
            return

        if retryable and tx.attempt_count < tx.max_attempts:
            tx.status = TransactionStatus.PENDING
            tx.failure_reason = f"Retry scheduled: {reason}"
            tx.processed_at = None
            await db.commit()
            await enqueue_transaction(str(transaction_id))

            await publish_update(str(transaction_id), {
                "user_id": user_id,
                "transaction_id": transaction_id,
                "status": TransactionStatus.PENDING.value,
                "failure_reason": tx.failure_reason,
                "attempt_count": tx.attempt_count,
            })
            return

        tx.status = TransactionStatus.FAILURE
        tx.failure_reason = reason
        tx.processed_at = _now_naive_utc()
        await db.commit()

    await dead_letter_transaction(str(transaction_id), reason)
    await publish_update(str(transaction_id), {
        "user_id": user_id,
        "transaction_id": transaction_id,
        "status": TransactionStatus.FAILURE.value,
        "failure_reason": reason,
    })


async def _process_send(db, tx: Transaction, user_id: str | None) -> Decimal:
    sender_wallet = await WalletService.deduct_balance(
        db,
        wallet_id=tx.wallet_id,
        amount=Decimal(tx.amount),
        transaction_id=tx.id,
        note=f"send_to:{tx.recipient_user_id}",
    )

    if tx.recipient_user_id:
        await WalletService.add_balance(
            db,
            user_id=tx.recipient_user_id,
            amount=Decimal(tx.amount),
            transaction_id=tx.id,
            note=f"receive_from:{user_id}",
            entry_type=LedgerEntryType.CREDIT,
        )

    return Decimal(sender_wallet.balance)


async def _process_buy(db, tx: Transaction) -> Decimal:
    amount = Decimal(tx.amount)
    price = await PriceService.get_price(tx.asset_symbol or "")

    fee = (amount * Decimal(str(settings.TRANSACTION_FEE_RATE))).quantize(Decimal("0.01"))
    net_amount = amount - fee
    if net_amount <= 0:
        raise ValueError("Amount too low after fee")

    quantity = (net_amount / price).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    if quantity <= 0:
        raise ValueError("Amount too low to purchase any asset quantity")

    wallet = await WalletService.deduct_balance(
        db,
        wallet_id=tx.wallet_id,
        amount=amount,
        transaction_id=tx.id,
        note=f"buy:{tx.asset_symbol}",
    )

    await HoldingService.add_asset(db, tx.wallet_id, tx.asset_symbol or "", quantity, price)

    tx.quantity = quantity
    tx.unit_price = price
    tx.fee_amount = fee

    await LedgerService.create_entry(
        db=db,
        wallet_id=tx.wallet_id,
        transaction_id=tx.id,
        entry_type=LedgerEntryType.BUY,
        amount_usd=-amount,
        asset_symbol=tx.asset_symbol,
        asset_quantity=quantity,
        balance_after=Decimal(wallet.balance),
        note="asset purchase",
    )

    if fee > 0:
        await LedgerService.create_entry(
            db=db,
            wallet_id=tx.wallet_id,
            transaction_id=tx.id,
            entry_type=LedgerEntryType.FEE,
            amount_usd=-fee,
            balance_after=Decimal(wallet.balance),
            note="trading fee",
        )

    return Decimal(wallet.balance)


async def _process_sell(db, tx: Transaction, user_id: str | None) -> Decimal:
    amount = Decimal(tx.amount)
    price = await PriceService.get_price(tx.asset_symbol or "")

    quantity = (amount / price).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    if quantity <= 0:
        raise ValueError("Amount too low to sell any asset quantity")

    fee = (amount * Decimal(str(settings.TRANSACTION_FEE_RATE))).quantize(Decimal("0.01"))
    credit = amount - fee
    if credit <= 0:
        raise ValueError("Sell credit must be positive")

    await HoldingService.remove_asset(db, tx.wallet_id, tx.asset_symbol or "", quantity)

    wallet = await WalletService.add_balance(
        db,
        user_id=user_id or "",
        amount=credit,
        transaction_id=tx.id,
        note=f"sell:{tx.asset_symbol}",
        entry_type=LedgerEntryType.SELL,
    )

    tx.quantity = quantity
    tx.unit_price = price
    tx.fee_amount = fee

    await LedgerService.create_entry(
        db=db,
        wallet_id=tx.wallet_id,
        transaction_id=tx.id,
        entry_type=LedgerEntryType.SELL,
        amount_usd=credit,
        asset_symbol=tx.asset_symbol,
        asset_quantity=-quantity,
        balance_after=Decimal(wallet.balance),
        note="asset sale",
    )

    if fee > 0:
        await LedgerService.create_entry(
            db=db,
            wallet_id=tx.wallet_id,
            transaction_id=tx.id,
            entry_type=LedgerEntryType.FEE,
            amount_usd=-fee,
            balance_after=Decimal(wallet.balance),
            note="trading fee",
        )

    return Decimal(wallet.balance)


async def process_transaction(transaction_id: int) -> None:
    tx, user_id = await _mark_processing(transaction_id)
    if tx is None:
        # Race-safe behavior: transaction may not be committed yet when dequeued.
        # Requeue once and let it retry shortly instead of leaving it stuck pending.
        logger.warning(f"Transaction {transaction_id} not found yet; requeueing")
        await asyncio.sleep(0.25)
        await enqueue_transaction(str(transaction_id))
        return

    if tx.status in {TransactionStatus.SUCCESS, TransactionStatus.FAILURE}:
        logger.info(f"Skipping already finalized tx {transaction_id}")
        return

    await publish_update(str(transaction_id), {
        "user_id": user_id,
        "transaction_id": transaction_id,
        "status": TransactionStatus.PROCESSING.value,
        "attempt_count": tx.attempt_count,
    })

    await asyncio.sleep(1)

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Transaction)
                .where(Transaction.id == transaction_id)
                .with_for_update()
            )
            tx = result.scalar_one_or_none()
            if tx is None:
                return

            user_id = await _get_user_id_for_wallet(db, tx.wallet_id)

            if tx.transaction_type == TransactionType.SEND:
                new_balance = await _process_send(db, tx, user_id)
            elif tx.transaction_type == TransactionType.BUY:
                new_balance = await _process_buy(db, tx)
            elif tx.transaction_type == TransactionType.SELL:
                new_balance = await _process_sell(db, tx, user_id)
            else:
                raise ValueError(f"Unsupported transaction type {tx.transaction_type}")

            tx.status = TransactionStatus.SUCCESS
            tx.failure_reason = None
            tx.processed_at = _now_naive_utc()
            await db.commit()

        logger.info(f"Transaction {transaction_id} SUCCESS | balance={new_balance}")
        await publish_update(str(transaction_id), {
            "user_id": user_id,
            "transaction_id": transaction_id,
            "status": TransactionStatus.SUCCESS.value,
            "new_balance": str(new_balance),
            "processed_at": _now_naive_utc().isoformat(),
            "quantity": str(tx.quantity) if tx.quantity is not None else None,
            "unit_price": str(tx.unit_price) if tx.unit_price is not None else None,
            "fee_amount": str(tx.fee_amount),
            "attempt_count": tx.attempt_count,
        })

    except (InsufficientBalanceError, WalletNotFoundError, InsufficientAssetError, UnsupportedAssetError, ValueError) as e:
        logger.warning(f"Transaction {transaction_id} FAILED: {e}")
        await _finalize_failure(
            transaction_id=transaction_id,
            reason=str(e),
            user_id=user_id,
            retryable=False,
        )
    except Exception as e:
        logger.error(f"Unexpected error on tx {transaction_id}: {e}", exc_info=True)
        await _finalize_failure(
            transaction_id=transaction_id,
            reason=f"Internal error: {e}",
            user_id=user_id,
            retryable=True,
        )


async def worker_loop() -> None:
    logger.info("Transaction worker started - waiting for jobs...")

    while True:
        try:
            async with aioredis.from_url(settings.REDIS_URL, decode_responses=True) as redis_client:
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
