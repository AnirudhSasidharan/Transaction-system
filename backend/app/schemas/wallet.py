from decimal import Decimal
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WalletCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    initial_balance: Decimal = Field(default=Decimal("1000.00"), ge=Decimal("0"))


class WalletResponse(BaseModel):
    id: int
    user_id: str
    balance: str        # return as string to avoid serialization issues
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            user_id=obj.user_id,
            balance=str(obj.balance),
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


class WalletTopUp(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0"))