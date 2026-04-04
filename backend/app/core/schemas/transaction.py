"""
app/schemas/transaction.py
--------------------------
WHAT IS THIS?
  Pydantic schemas for the Transaction API.

KEY CONCEPT — model_validator:
  A validator that runs AFTER all individual fields are validated.
  We use it to enforce rules that span multiple fields:
  - "send" type requires recipient_user_id
  - "buy"  type requires asset_symbol
  This way the API returns a clear error if these rules are broken,
  before any database code runs.

KEY CONCEPT — Optional[str] vs str:
  str           = required, cannot be None
  Optional[str] = can be None (the field can be missing or null)
  We use Optional for recipient_user_id and asset_symbol because
  only one of them is needed depending on transaction_type.
"""

from decimal import Decimal
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.transaction import TransactionStatus, TransactionType


class TransactionCreate(BaseModel):
    """
    What the client sends to CREATE a transaction.
    POST /api/v1/transactions/

    The model_validator enforces cross-field rules:
    - send → must have recipient_user_id
    - buy  → must have asset_symbol
    """
    user_id: str = Field(..., description="The user initiating the transaction")
    transaction_type: TransactionType
    amount: Decimal = Field(..., gt=Decimal("0"), decimal_places=2)
    recipient_user_id: Optional[str] = Field(None, max_length=100)
    asset_symbol: Optional[str] = Field(None, max_length=20)

    @model_validator(mode="after")
    def validate_transaction_fields(self) -> "TransactionCreate":
        """
        Runs after all fields are individually validated.
        Checks cross-field rules.
        """
        if self.transaction_type == TransactionType.SEND and not self.recipient_user_id:
            raise ValueError("recipient_user_id is required for send transactions")
        if self.transaction_type == TransactionType.BUY and not self.asset_symbol:
            raise ValueError("asset_symbol is required for buy transactions")
        return self


class TransactionResponse(BaseModel):
    """
    What the API returns for a transaction.
    GET /api/v1/transactions/{id}
    """
    id: int
    wallet_id: int
    transaction_type: TransactionType
    amount: Decimal
    status: TransactionStatus
    recipient_user_id: Optional[str]
    asset_symbol: Optional[str]
    failure_reason: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TransactionStatusUpdate(BaseModel):
    """
    Used internally by the worker when publishing a status update.
    This is also the shape of the JSON sent over WebSocket to the browser.

    new_balance is included so the frontend can update the wallet balance
    display immediately without making a separate API call.
    """
    transaction_id: int
    status: TransactionStatus
    failure_reason: Optional[str] = None
    new_balance: Optional[Decimal] = None
    processed_at: Optional[datetime] = None
