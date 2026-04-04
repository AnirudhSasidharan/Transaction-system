"""
app/schemas/wallet.py
---------------------
WHAT IS THIS?
  Schemas define what the API accepts (input) and returns (output).
  They are completely separate from models on purpose.

  Model  = what the DATABASE looks like
  Schema = what the API's JSON looks like

  Example of why they're separate:
  - You store passwords hashed in the DB but never return them in the API
  - You accept a plain string from JSON but store it as a specific type
  - You might return extra computed fields not stored in the DB

KEY CONCEPT — Pydantic validation:
  Pydantic checks every field automatically.
  If a request sends the wrong type, a missing field, or a value
  out of range — it raises a clear HTTP 422 error BEFORE your
  code even runs. You never write manual validation.

  Field(gt=0)        means: must be greater than 0
  Field(ge=0)        means: must be greater than or equal to 0
  Field(min_length=1) means: string must have at least 1 character
"""

from decimal import Decimal
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WalletCreate(BaseModel):
    """
    What the client sends to CREATE a wallet.
    POST /api/v1/wallets/
    """
    user_id: str = Field(
        ...,               # ... means required — no default, must be provided
        min_length=1,
        max_length=100,
        description="Unique user identifier",
    )
    initial_balance: Decimal = Field(
        default=Decimal("1000.00"),
        ge=Decimal("0"),          # cannot start with negative balance
        decimal_places=2,
    )


class WalletResponse(BaseModel):
    """
    What the API returns when you request wallet data.
    GET /api/v1/wallets/{user_id}
    """
    id: int
    user_id: str
    balance: Decimal
    created_at: datetime
    updated_at: Optional[datetime]

    # from_attributes=True lets Pydantic read data directly from
    # SQLAlchemy model objects (not just plain dicts)
    model_config = {"from_attributes": True}


class WalletTopUp(BaseModel):
    """
    What the client sends to add funds to a wallet.
    POST /api/v1/wallets/{user_id}/topup
    """
    amount: Decimal = Field(
        ...,
        gt=Decimal("0"),    # must be positive — can't top up by 0 or negative
        decimal_places=2,
    )
