from decimal import Decimal


class UnsupportedAssetError(Exception):
    pass


class PriceService:
    # Mock market prices. Replace with external provider integration later.
    PRICES: dict[str, Decimal] = {
        "BTC": Decimal("68000.00"),
        "ETH": Decimal("3400.00"),
        "SOL": Decimal("175.00"),
        "AAPL": Decimal("210.00"),
        "TSLA": Decimal("195.00"),
    }

    @staticmethod
    async def get_price(asset_symbol: str) -> Decimal:
        symbol = asset_symbol.upper()
        price = PriceService.PRICES.get(symbol)
        if price is None:
            raise UnsupportedAssetError(f"Unsupported asset symbol '{asset_symbol}'")
        return price
