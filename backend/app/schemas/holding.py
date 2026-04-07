from decimal import Decimal

from pydantic import BaseModel


class HoldingResponse(BaseModel):
    asset_symbol: str
    quantity: Decimal
    avg_buy_price: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal


class PortfolioResponse(BaseModel):
    user_id: str
    cash_balance: str
    total_market_value: str
    total_equity: str
    total_unrealized_pnl: str
    positions: list[HoldingResponse]
