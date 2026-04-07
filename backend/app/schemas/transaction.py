from decimal import Decimal
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.transaction import TransactionStatus, TransactionType


class TransactionCreate(BaseModel):
    user_id: Optional[str] = Field(default=None, description="Optional when using auth token")
    transaction_type: TransactionType
    amount: Decimal = Field(..., gt=Decimal("0"), decimal_places=2)
    recipient_user_id: Optional[str] = Field(None, max_length=100)
    asset_symbol: Optional[str] = Field(None, max_length=20)

    @model_validator(mode="after")
    def validate_transaction_fields(self) -> "TransactionCreate":
        if self.transaction_type == TransactionType.SEND and not self.recipient_user_id:
            raise ValueError("recipient_user_id is required for send transactions")
        if self.transaction_type in {TransactionType.BUY, TransactionType.SELL} and not self.asset_symbol:
            raise ValueError("asset_symbol is required for buy/sell transactions")
        return self


class TransactionResponse(BaseModel):
    id: int
    wallet_id: int
    transaction_type: TransactionType
    amount: Decimal
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    fee_amount: Decimal
    status: TransactionStatus
    recipient_user_id: Optional[str]
    asset_symbol: Optional[str]
    idempotency_key: Optional[str] = None
    attempt_count: int
    max_attempts: int
    failure_reason: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TransactionStatusUpdate(BaseModel):
    transaction_id: int
    status: TransactionStatus
    failure_reason: Optional[str] = None
    new_balance: Optional[Decimal] = None
    processed_at: Optional[datetime] = None
    attempt_count: Optional[int] = None
