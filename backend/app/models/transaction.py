"""
app/models/transaction.py
--------------------------
WHAT IS THIS?
  The Transaction table. Every "send money" or "buy asset" action
  creates one row here with a status that moves through a lifecycle:

    pending → processing → success
                        ↘ failure

WHY ENUM FOR STATUS?
  Instead of storing raw strings like "pending" (easy to typo as "Pending"
  or "PENDING"), we use a Python Enum.
  Python enforces valid values at the code level.
  PostgreSQL enforces them at the database level.
  Both layers protect against invalid data.

WHY str + enum.Enum?
  Makes TransactionStatus.PENDING == "pending" true.
  This means JSON serialization works automatically —
  you don't need to convert it manually.

WHY FOREIGN KEY?
  wallet_id must exist as an id in the wallets table.
  If you try to create a transaction for a wallet that doesn't exist,
  the database rejects it. Data integrity enforced at the DB level.
"""

import enum
from decimal import Decimal
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DECIMAL, ForeignKey, Enum as SAEnum, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TransactionStatus(str, enum.Enum):
    """
    str + enum.Enum means the value IS the string.
    TransactionStatus.PENDING == "pending"  →  True
    This makes JSON serialization automatic — no extra conversion needed.
    """
    PENDING    = "pending"
    PROCESSING = "processing"
    SUCCESS    = "success"
    FAILURE    = "failure"


class TransactionType(str, enum.Enum):
    SEND = "send"   # transfer money to another user
    BUY  = "buy"    # purchase an asset (stock, crypto, etc.)


class Transaction(Base):
    __tablename__ = "transactions"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Which wallet created this transaction
    # ondelete="RESTRICT" means: block deletion of a wallet that has transactions
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # For "send" type — who receives the money (optional for "buy")
    recipient_user_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # For "buy" type — what asset is being purchased (optional for "send")
    asset_symbol: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )

    # The amount — always Decimal, never float
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)

    # SAEnum stores this as a PostgreSQL ENUM column
    # Only "pending", "processing", "success", "failure" are valid at DB level
    status: Mapped[TransactionStatus] = mapped_column(
        SAEnum(TransactionStatus, name="transaction_status"),
        nullable=False,
        default=TransactionStatus.PENDING, #hereno .value needed because default is handled by SQLAlchemy, not the database
        server_default=TransactionStatus.PENDING.value, #.value is needed because server_default expects a string, not an enum
        index=True,
    )

    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, name="transaction_type"),
        nullable=False,
    )

    # Human-readable failure reason e.g. "Insufficient balance"
    # Only set when status=FAILURE
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # created_at is set by DB on insert, indexed for sorting by date
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), index=True
    )

    # processed_at is set by the worker when it finishes processing
    processed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Back-reference to the wallet that owns this transaction
    wallet: Mapped["Wallet"] = relationship(back_populates="transactions")  # noqa: F821

    # Compound index: speeds up "get all transactions for wallet X ordered by date"
    # This is the most common query — combining both columns into one index
    # is much faster than two separate single-column indexes
    __table_args__ = (
        Index("ix_transactions_wallet_created", "wallet_id", "created_at"),#creates a new compound index named "ix_transactions_wallet_created" on the wallet_id and created_at columns
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} "
            f"type={self.transaction_type} "
            f"status={self.status} "
            f"amount={self.amount}>"
        )
