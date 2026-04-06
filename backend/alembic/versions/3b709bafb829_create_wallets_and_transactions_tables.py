"""create wallets and transactions tables

Revision ID: 3b709bafb829
Revises: 
Create Date: 2026-04-06 12:18:06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '3b709bafb829'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create wallets table
    op.create_table('wallets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('balance', sa.DECIMAL(precision=18, scale=2), server_default='1000.00', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wallets_user_id'), 'wallets', ['user_id'], unique=True)

    # Create transactions table
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('wallet_id', sa.Integer(), nullable=False),
        sa.Column('recipient_user_id', sa.String(length=100), nullable=True),
        sa.Column('asset_symbol', sa.String(length=20), nullable=True),
        sa.Column('amount', sa.DECIMAL(precision=18, scale=2), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'success', 'failure', name='transaction_status'), server_default='pending', nullable=False),
        sa.Column('transaction_type', sa.Enum('send', 'buy', name='transaction_type'), nullable=False),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_created_at'), 'transactions', ['created_at'], unique=False)
    op.create_index(op.f('ix_transactions_status'), 'transactions', ['status'], unique=False)
    op.create_index(op.f('ix_transactions_wallet_id'), 'transactions', ['wallet_id'], unique=False)
    op.create_index('ix_transactions_wallet_created', 'transactions', ['wallet_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_transactions_wallet_created', table_name='transactions')
    op.drop_index(op.f('ix_transactions_wallet_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_status'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_created_at'), table_name='transactions')
    op.drop_table('transactions')
    op.drop_index(op.f('ix_wallets_user_id'), table_name='wallets')
    op.drop_table('wallets')