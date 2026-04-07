import enum
from decimal import Decimal
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DECIMAL, Enum as SAEnum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LedgerEntryType(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    BUY = "buy"
    SELL = "sell"
    FEE = "fee"
    TOPUP = "topup"


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id: Mapped[Optional[int]] = mapped_column(ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)

    entry_type: Mapped[LedgerEntryType] = mapped_column(
        SAEnum(
            LedgerEntryType,
            name="ledger_entry_type",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    amount_usd: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, server_default="0.00")
    asset_symbol: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    asset_quantity: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(24, 8), nullable=True)
    balance_after: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    wallet: Mapped["Wallet"] = relationship(back_populates="ledger_entries")  # noqa: F821
    transaction: Mapped[Optional["Transaction"]] = relationship(back_populates="ledger_entries")  # noqa: F821
