from decimal import Decimal
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DECIMAL, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    balance: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 2),
        nullable=False,
        server_default="1000.00",
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="wallet", lazy="select")  # noqa: F821
    holdings: Mapped[list["Holding"]] = relationship(back_populates="wallet", lazy="select")  # noqa: F821
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="wallet", lazy="select")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Wallet user={self.user_id} balance={self.balance}>"
