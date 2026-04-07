from decimal import Decimal
from datetime import datetime

from sqlalchemy import String, DECIMAL, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    asset_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(24, 8), nullable=False, server_default="0")
    avg_buy_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    wallet: Mapped["Wallet"] = relationship(back_populates="holdings")  # noqa: F821

    __table_args__ = (
        Index("ix_holdings_wallet_asset", "wallet_id", "asset_symbol", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Holding wallet_id={self.wallet_id} asset={self.asset_symbol} qty={self.quantity}>"
