"""
app/services/wallet_service.py
-------------------------------
WHAT IS A SERVICE?
  The service layer contains the actual BUSINESS LOGIC.
  Routes handle HTTP. Services handle "what does this action mean?"

  This separation keeps things clean:
  - Route:   "I got a POST /wallets request with this JSON"
  - Service: "Here is how to actually create a wallet"

  Benefits:
  - Routes stay thin and readable
  - Logic is testable without needing HTTP
  - Logic can be reused across multiple routes

KEY CONCEPT — SELECT FOR UPDATE (double-spend prevention):
  Without locking:
    Request A reads balance = 1000
    Request B reads balance = 1000  ← both see the same value
    Request A deducts 800 → writes 200
    Request B deducts 800 → writes 200  ← WRONG! Both succeeded
    Total deducted = 1600 from a balance of 1000

  With SELECT FOR UPDATE:
    Request A locks the row → reads 1000
    Request B tries to lock → WAITS (blocked)
    Request A deducts 800 → writes 200 → releases lock
    Request B now reads 200 → not enough → fails correctly
    ✓ No double spend
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import Wallet
from app.schemas.wallet import WalletCreate


class InsufficientBalanceError(Exception):
    """Raised when a wallet does not have enough funds."""
    pass


class WalletNotFoundError(Exception):
    """Raised when no wallet exists for a given user."""
    pass


class WalletService:

    @staticmethod
    async def create_wallet(db: AsyncSession, data: WalletCreate) -> Wallet:
        """
        Create a new wallet for a user.

        db.add()  → tells SQLAlchemy to track this new object
        db.flush() → sends the INSERT to DB but does not commit yet
                     this gives us the auto-generated wallet.id
                     without fully committing the transaction
        """
        wallet = Wallet(
            user_id=data.user_id,
            balance=data.initial_balance,
        )
        db.add(wallet)
        await db.flush()
        return wallet

    @staticmethod
    async def get_wallet_by_user(db: AsyncSession, user_id: str) -> Wallet:
        """
        Fetch a wallet by user_id.
        Raises WalletNotFoundError if no wallet exists for this user.
        """
        result = await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = result.scalar_one_or_none()
        if wallet is None:
            raise WalletNotFoundError(f"No wallet found for user '{user_id}'")
        return wallet

    @staticmethod
    async def deduct_balance(
        db: AsyncSession,
        wallet_id: int,
        amount: Decimal,
    ) -> Wallet:
        """
        Deduct amount from a wallet's balance.

        Uses SELECT FOR UPDATE to lock the row during the transaction.
        This prevents two simultaneous requests from both reading the
        same balance and both approving withdrawals that exceed it.

        If balance < amount → raises InsufficientBalanceError
        The worker catches this and marks the transaction as FAILED.
        """
        # .with_for_update() adds "FOR UPDATE" to the SQL query
        # This locks the row until our session commits or rolls back
        result = await db.execute(
            select(Wallet)
            .where(Wallet.id == wallet_id)
            .with_for_update()        # ← THE LOCK
        )
        wallet = result.scalar_one_or_none()

        if wallet is None:
            raise WalletNotFoundError(f"Wallet id={wallet_id} not found")

        if wallet.balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance: have {wallet.balance}, need {amount}"
            )

        wallet.balance -= amount
        await db.flush()
        return wallet

    @staticmethod
    async def add_balance(
        db: AsyncSession,
        user_id: str,
        amount: Decimal,
    ) -> Wallet:
        """
        Add funds to a wallet.
        Used for:
        - The recipient side of a "send" transaction
        - Demo top-up endpoint
        """
        result = await db.execute(
            select(Wallet)
            .where(Wallet.user_id == user_id)
            .with_for_update()
        )
        wallet = result.scalar_one_or_none()
        if wallet is None:
            raise WalletNotFoundError(f"No wallet for user '{user_id}'")

        wallet.balance += amount
        await db.flush()
        return wallet
