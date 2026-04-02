"""
app/models/wallet.py
--------------------
WHAT IS THIS?
  A SQLAlchemy model = a Python class that maps directly to a database table.
  Every attribute you declare here becomes a column in the 'wallets' table.

WHY DECIMAL AND NOT FLOAT FOR MONEY?
  Float:   0.1 + 0.2 = 0.30000000000000004  ← rounding bug
  Decimal: 0.1 + 0.2 = 0.3                  ← exact
  Never use float for money. Ever.

WHY INDEX ON user_id?
  Without index: finding a wallet by user_id scans EVERY row (slow as data grows)
  With index:    jumps directly to the row like a book's table of contents (fast)

DOUBLE-SPEND PREVENTION (handled in wallet_service.py):
  When deducting balance, we use SELECT FOR UPDATE.
  This locks the row so no other request can read it until we're done.
  Without it: two requests could both see balance=1000, both approve
  a 900 withdrawal, and double-spend 1800 total.
"""

from decimal import Decimal
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DECIMAL, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    # Primary key — auto-increments (1, 2, 3...)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Each wallet belongs to one user, identified by a string ID
    # unique=True ensures one wallet per user
    # index=True speeds up lookups by user_id
    user_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # DECIMAL(18, 2) = up to 18 digits total, 2 decimal places
    # e.g. 9999999999999999.99 is the max
    # server_default sets the value in the DB itself when inserting a new row
    balance: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 2),
        nullable=False,
        server_default="1000.00",
    )

    # Timestamps — the database sets these automatically
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship: one wallet → many transactions
    # lazy="select" means transactions are only loaded when you access .transactions
    # They are NOT loaded automatically with every wallet query (efficient)
    transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        back_populates="wallet",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Wallet user={self.user_id} balance={self.balance}>"
