import enum
from decimal import Decimal
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DECIMAL, ForeignKey, Enum as SAEnum, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TransactionStatus(str, enum.Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    SUCCESS    = "success"
    FAILURE    = "failure"


class TransactionType(str, enum.Enum):
    SEND = "send"
    BUY  = "buy"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    recipient_user_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    asset_symbol: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )

    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)

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

    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), index=True
    )

    processed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    wallet: Mapped["Wallet"] = relationship(back_populates="transactions")  # noqa: F821

    __table_args__ = (
        Index("ix_transactions_wallet_created", "wallet_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} "
            f"type={self.transaction_type} "
            f"status={self.status} "
            f"amount={self.amount}>"
        )