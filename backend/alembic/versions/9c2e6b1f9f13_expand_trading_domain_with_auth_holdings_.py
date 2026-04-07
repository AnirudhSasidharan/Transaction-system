"""expand trading domain with auth, holdings, ledger, retries

Revision ID: 9c2e6b1f9f13
Revises: 3b709bafb829
Create Date: 2026-04-07 16:20:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c2e6b1f9f13"
down_revision: Union[str, None] = "3b709bafb829"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add SELL enum value for transaction_type (PostgreSQL)
    op.execute("ALTER TYPE transaction_type ADD VALUE IF NOT EXISTS 'sell'")

    # Users table for auth
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_user_id"), "users", ["user_id"], unique=True)

    # Holdings table
    op.create_table(
        "holdings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("asset_symbol", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.DECIMAL(precision=24, scale=8), server_default="0", nullable=False),
        sa.Column("avg_buy_price", sa.DECIMAL(precision=18, scale=2), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_holdings_wallet_asset", "holdings", ["wallet_id", "asset_symbol"], unique=True)

    # Add transaction enrichment fields
    op.add_column("transactions", sa.Column("quantity", sa.DECIMAL(precision=24, scale=8), nullable=True))
    op.add_column("transactions", sa.Column("unit_price", sa.DECIMAL(precision=18, scale=2), nullable=True))
    op.add_column(
        "transactions",
        sa.Column("fee_amount", sa.DECIMAL(precision=18, scale=2), server_default="0.00", nullable=False),
    )
    op.add_column("transactions", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column(
        "transactions",
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "transactions",
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
    )
    op.create_index("ix_transactions_wallet_idempotency", "transactions", ["wallet_id", "idempotency_key"], unique=True)

    # Ledger entries table
    ledger_enum = sa.Enum(
        "debit",
        "credit",
        "buy",
        "sell",
        "fee",
        "topup",
        name="ledger_entry_type",
        create_type=False,
    )
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        sa.Column("entry_type", ledger_enum, nullable=False),
        sa.Column("amount_usd", sa.DECIMAL(precision=18, scale=2), server_default="0.00", nullable=False),
        sa.Column("asset_symbol", sa.String(length=20), nullable=True),
        sa.Column("asset_quantity", sa.DECIMAL(precision=24, scale=8), nullable=True),
        sa.Column("balance_after", sa.DECIMAL(precision=18, scale=2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ledger_entries_wallet_id"), "ledger_entries", ["wallet_id"], unique=False)
    op.create_index(op.f("ix_ledger_entries_transaction_id"), "ledger_entries", ["transaction_id"], unique=False)
    op.create_index(op.f("ix_ledger_entries_created_at"), "ledger_entries", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ledger_entries_created_at"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_transaction_id"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_wallet_id"), table_name="ledger_entries")
    op.drop_table("ledger_entries")

    op.drop_index("ix_transactions_wallet_idempotency", table_name="transactions")
    op.drop_column("transactions", "max_attempts")
    op.drop_column("transactions", "attempt_count")
    op.drop_column("transactions", "idempotency_key")
    op.drop_column("transactions", "fee_amount")
    op.drop_column("transactions", "unit_price")
    op.drop_column("transactions", "quantity")

    op.drop_index("ix_holdings_wallet_asset", table_name="holdings")
    op.drop_table("holdings")

    op.drop_index(op.f("ix_users_user_id"), table_name="users")
    op.drop_table("users")

    # transaction_type enum value 'sell' cannot be removed safely in PostgreSQL downgrade.
