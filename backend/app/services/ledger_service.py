from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ledger_entry import LedgerEntry, LedgerEntryType


class LedgerService:

    @staticmethod
    async def create_entry(
        db: AsyncSession,
        wallet_id: int,
        entry_type: LedgerEntryType,
        balance_after: Decimal,
        amount_usd: Decimal = Decimal("0"),
        asset_symbol: str | None = None,
        asset_quantity: Decimal | None = None,
        transaction_id: int | None = None,
        note: str | None = None,
    ) -> LedgerEntry:
        entry = LedgerEntry(
            wallet_id=wallet_id,
            transaction_id=transaction_id,
            entry_type=entry_type,
            amount_usd=amount_usd,
            asset_symbol=asset_symbol,
            asset_quantity=asset_quantity,
            balance_after=balance_after,
            note=note,
        )
        db.add(entry)
        await db.flush()
        return entry
