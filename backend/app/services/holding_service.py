from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.holding import Holding


class InsufficientAssetError(Exception):
    pass


class HoldingService:

    @staticmethod
    async def get_or_create_holding(
        db: AsyncSession,
        wallet_id: int,
        asset_symbol: str,
    ) -> Holding:
        symbol = asset_symbol.upper()
        result = await db.execute(
            select(Holding)
            .where(Holding.wallet_id == wallet_id, Holding.asset_symbol == symbol)
            .with_for_update()
        )
        holding = result.scalar_one_or_none()
        if holding:
            return holding

        holding = Holding(
            wallet_id=wallet_id,
            asset_symbol=symbol,
            quantity=Decimal("0"),
            avg_buy_price=Decimal("0"),
        )
        db.add(holding)
        await db.flush()
        await db.refresh(holding)
        return holding

    @staticmethod
    async def add_asset(
        db: AsyncSession,
        wallet_id: int,
        asset_symbol: str,
        quantity: Decimal,
        unit_price: Decimal,
    ) -> Holding:
        holding = await HoldingService.get_or_create_holding(db, wallet_id, asset_symbol)

        current_qty = Decimal(holding.quantity)
        current_avg = Decimal(holding.avg_buy_price)

        new_qty = current_qty + quantity
        if new_qty <= 0:
            raise ValueError("Holding quantity must remain positive")

        total_cost = (current_qty * current_avg) + (quantity * unit_price)
        new_avg = total_cost / new_qty

        holding.quantity = new_qty
        holding.avg_buy_price = new_avg.quantize(Decimal("0.01"))
        await db.flush()
        await db.refresh(holding)
        return holding

    @staticmethod
    async def remove_asset(
        db: AsyncSession,
        wallet_id: int,
        asset_symbol: str,
        quantity: Decimal,
    ) -> Holding:
        holding = await HoldingService.get_or_create_holding(db, wallet_id, asset_symbol)

        current_qty = Decimal(holding.quantity)
        if current_qty < quantity:
            raise InsufficientAssetError(
                f"Insufficient asset quantity: have {current_qty}, need {quantity}"
            )

        holding.quantity = current_qty - quantity
        if holding.quantity == 0:
            holding.avg_buy_price = Decimal("0")

        await db.flush()
        await db.refresh(holding)
        return holding

    @staticmethod
    async def list_holdings(db: AsyncSession, wallet_id: int) -> list[Holding]:
        result = await db.execute(
            select(Holding)
            .where(Holding.wallet_id == wallet_id)
            .order_by(Holding.asset_symbol.asc())
        )
        return list(result.scalars().all())
