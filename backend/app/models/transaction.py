import enum
from decimal import Decimal
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DECIMAL, ForeignKey, Enum as SAEnum, Text, func, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"


class TransactionType(str, enum.Enum):
    SEND = "send"
    BUY = "buy"
    SELL = "sell"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    recipient_user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    asset_symbol: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    quantity: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(24, 8), nullable=True)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 2), nullable=True)
    fee_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    status: Mapped[TransactionStatus] = mapped_column(
        SAEnum(
            TransactionStatus,
            name="transaction_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=TransactionStatus.PENDING,
        server_default="pending",
        index=True,
    )

    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(
            TransactionType,
            name="transaction_type",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")

    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    wallet: Mapped["Wallet"] = relationship(back_populates="transactions")  # noqa: F821
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="transaction")  # noqa: F821

    __table_args__ = (
        Index("ix_transactions_wallet_created", "wallet_id", "created_at"),
        Index("ix_transactions_wallet_idempotency", "wallet_id", "idempotency_key", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} "
            f"type={self.transaction_type} "
            f"status={self.status} "
            f"amount={self.amount}>"
        )
