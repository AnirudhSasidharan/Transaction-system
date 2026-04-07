from decimal import Decimal

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    auth_error,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
    TokenError,
)
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest
from app.schemas.wallet import WalletCreate
from app.services.wallet_service import WalletService


class AuthError(Exception):
    pass


bearer_scheme = HTTPBearer(auto_error=False)


class AuthService:

    @staticmethod
    async def register(db: AsyncSession, data: RegisterRequest) -> str:
        existing = await db.execute(select(User).where(User.user_id == data.user_id))
        if existing.scalar_one_or_none():
            raise AuthError("User ID already exists")

        user = User(
            user_id=data.user_id,
            password_hash=hash_password(data.password),
        )
        db.add(user)
        await db.flush()

        wallet_data = WalletCreate(
            user_id=data.user_id,
            initial_balance=Decimal(str(data.initial_balance)),
        )
        await WalletService.create_wallet(db, wallet_data)

        return create_access_token(data.user_id)

    @staticmethod
    async def login(db: AsyncSession, data: LoginRequest) -> str:
        result = await db.execute(select(User).where(User.user_id == data.user_id))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(data.password, user.password_hash):
            raise AuthError("Invalid user ID or password")

        return create_access_token(user.user_id)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise auth_error("Missing bearer token")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise auth_error(str(exc)) from exc

    return str(payload["sub"])


async def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str | None:
    if credentials is None:
        return None
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise auth_error(str(exc)) from exc
    return str(payload["sub"])


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise auth_error("User not found")
    return user
