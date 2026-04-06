"""
app/api/wallets.py
------------------
WHAT IS A ROUTER?
  A router is a mini-app that groups related endpoints together.
  The main app mounts it at a prefix — all wallet routes live at /api/v1/wallets/

HTTP METHODS:
  POST   → create something new
  GET    → fetch/read data
  PUT    → update/replace
  DELETE → delete

STATUS CODES:
  201 Created  → successfully created a resource
  200 OK       → request succeeded
  404 Not Found → resource doesn't exist
  422 Unprocessable → validation failed (Pydantic handles this automatically)

Depends(get_db):
  FastAPI's dependency injection.
  FastAPI calls get_db() and passes the result as `db`.
  When the request finishes, FastAPI runs the cleanup code in get_db().
  You never manually open or close sessions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.wallet import WalletCreate, WalletResponse, WalletTopUp
from app.services.wallet_service import WalletService, WalletNotFoundError

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.post("/", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    data: WalletCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new wallet for a user."""
    wallet = await WalletService.create_wallet(db, data)
    return wallet


@router.get("/{user_id}", response_model=WalletResponse)
async def get_wallet(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a wallet and its current balance by user_id."""
    try:
        return await WalletService.get_wallet_by_user(db, user_id)
    except WalletNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{user_id}/topup", response_model=WalletResponse)
async def top_up_wallet(
    user_id: str,
    data: WalletTopUp,
    db: AsyncSession = Depends(get_db),
):
    """Add funds to a wallet. For demo and testing purposes."""
    try:
        return await WalletService.add_balance(db, user_id, data.amount)
    except WalletNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
