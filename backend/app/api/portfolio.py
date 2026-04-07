from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.holding import HoldingResponse, PortfolioResponse
from app.services.auth_service import get_current_user_id
from app.services.holding_service import HoldingService
from app.services.price_service import PriceService, UnsupportedAssetError
from app.services.wallet_service import WalletService, WalletNotFoundError

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/me", response_model=PortfolioResponse)
async def get_my_portfolio(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        wallet = await WalletService.get_wallet_by_user(db, user_id)
    except WalletNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    holdings = await HoldingService.list_holdings(db, wallet.id)
    positions: list[HoldingResponse] = []

    total_market_value = Decimal("0")
    total_unrealized_pnl = Decimal("0")

    for holding in holdings:
        if Decimal(holding.quantity) <= 0:
            continue
        try:
            market_price = await PriceService.get_price(holding.asset_symbol)
        except UnsupportedAssetError:
            continue

        market_value = (Decimal(holding.quantity) * market_price).quantize(Decimal("0.01"))
        cost_basis = (Decimal(holding.quantity) * Decimal(holding.avg_buy_price)).quantize(Decimal("0.01"))
        pnl = (market_value - cost_basis).quantize(Decimal("0.01"))

        total_market_value += market_value
        total_unrealized_pnl += pnl

        positions.append(
            HoldingResponse(
                asset_symbol=holding.asset_symbol,
                quantity=Decimal(holding.quantity),
                avg_buy_price=Decimal(holding.avg_buy_price),
                market_price=market_price,
                market_value=market_value,
                unrealized_pnl=pnl,
            )
        )

    total_equity = (Decimal(wallet.balance) + total_market_value).quantize(Decimal("0.01"))

    return PortfolioResponse(
        user_id=user_id,
        cash_balance=str(Decimal(wallet.balance).quantize(Decimal("0.01"))),
        total_market_value=str(total_market_value.quantize(Decimal("0.01"))),
        total_equity=str(total_equity),
        total_unrealized_pnl=str(total_unrealized_pnl.quantize(Decimal("0.01"))),
        positions=positions,
    )
