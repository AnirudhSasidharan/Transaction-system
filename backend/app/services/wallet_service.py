from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ledger_entry import LedgerEntryType
from app.models.wallet import Wallet
from app.schemas.wallet import WalletCreate
from app.services.ledger_service import LedgerService


class InsufficientBalanceError(Exception):
    pass


class WalletNotFoundError(Exception):
    pass


class WalletService:

    @staticmethod
    async def create_wallet(db: AsyncSession, data: WalletCreate) -> Wallet:
        wallet = Wallet(
            user_id=data.user_id,
            balance=data.initial_balance,
        )
        db.add(wallet)
        await db.flush()
        await db.refresh(wallet)

        await LedgerService.create_entry(
            db=db,
            wallet_id=wallet.id,
            entry_type=LedgerEntryType.CREDIT,
            amount_usd=Decimal(wallet.balance),
            balance_after=Decimal(wallet.balance),
            note="wallet_created",
        )
        return wallet

    @staticmethod
    async def get_wallet_by_user(db: AsyncSession, user_id: str) -> Wallet:
        result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
        wallet = result.scalar_one_or_none()
        if wallet is None:
            raise WalletNotFoundError(f"No wallet found for user '{user_id}'")
        return wallet

    @staticmethod
    async def deduct_balance(
        db: AsyncSession,
        wallet_id: int,
        amount: Decimal,
        transaction_id: int | None = None,
        note: str | None = None,
    ) -> Wallet:
        result = await db.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
        wallet = result.scalar_one_or_none()

        if wallet is None:
            raise WalletNotFoundError(f"Wallet id={wallet_id} not found")

        if wallet.balance < amount:
            raise InsufficientBalanceError(f"Insufficient balance: have {wallet.balance}, need {amount}")

        wallet.balance = wallet.balance - amount
        await db.flush()

        await LedgerService.create_entry(
            db=db,
            wallet_id=wallet.id,
            transaction_id=transaction_id,
            entry_type=LedgerEntryType.DEBIT,
            amount_usd=-amount,
            balance_after=Decimal(wallet.balance),
            note=note,
        )

        await db.refresh(wallet)
        return wallet

    @staticmethod
    async def add_balance(
        db: AsyncSession,
        user_id: str,
        amount: Decimal,
        transaction_id: int | None = None,
        note: str | None = None,
        entry_type: LedgerEntryType = LedgerEntryType.TOPUP,
    ) -> Wallet:
        result = await db.execute(select(Wallet).where(Wallet.user_id == user_id).with_for_update())
        wallet = result.scalar_one_or_none()
        if wallet is None:
            raise WalletNotFoundError(f"No wallet for user '{user_id}'")

        wallet.balance = wallet.balance + amount
        await db.flush()

        await LedgerService.create_entry(
            db=db,
            wallet_id=wallet.id,
            transaction_id=transaction_id,
            entry_type=entry_type,
            amount_usd=amount,
            balance_after=Decimal(wallet.balance),
            note=note,
        )

        await db.refresh(wallet)
        return wallet
