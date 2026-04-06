from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.wallet import WalletCreate, WalletResponse, WalletTopUp
from app.services.wallet_service import WalletService, WalletNotFoundError

router = APIRouter(prefix="/wallets", tags=["wallets"])


def wallet_to_response(wallet) -> WalletResponse:
    """Convert a Wallet model to a WalletResponse safely."""
    return WalletResponse(
        id=wallet.id,
        user_id=wallet.user_id,
        balance=str(wallet.balance),
        created_at=wallet.created_at,
        updated_at=wallet.updated_at,
    )


@router.post("/", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    data: WalletCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new wallet for a user."""
    wallet = await WalletService.create_wallet(db, data)
    return wallet_to_response(wallet)


@router.get("/{user_id}", response_model=WalletResponse)
async def get_wallet(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a wallet and its current balance by user_id."""
    try:
        wallet = await WalletService.get_wallet_by_user(db, user_id)
        return wallet_to_response(wallet)
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
        wallet = await WalletService.add_balance(db, user_id, data.amount)
        return wallet_to_response(wallet)
    except WalletNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))