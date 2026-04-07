from datetime import datetime

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    user_id: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    initial_balance: float = Field(default=1000.0, ge=0)


class LoginRequest(BaseModel):
    user_id: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
