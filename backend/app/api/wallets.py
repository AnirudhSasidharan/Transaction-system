from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.wallet import WalletCreate, WalletResponse, WalletTopUp
from app.services.auth_service import get_current_user_id
from app.services.wallet_service import WalletService, WalletNotFoundError

router = APIRouter(prefix="/wallets", tags=["wallets"])


def wallet_to_response(wallet) -> WalletResponse:
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
    wallet = await WalletService.create_wallet(db, data)
    return wallet_to_response(wallet)


@router.get("/me", response_model=WalletResponse)
async def get_my_wallet(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    wallet = await WalletService.get_wallet_by_user(db, user_id)
    return wallet_to_response(wallet)


@router.post("/me/topup", response_model=WalletResponse)
async def top_up_my_wallet(
    data: WalletTopUp,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    wallet = await WalletService.add_balance(db, user_id, data.amount)
    return wallet_to_response(wallet)


@router.get("/{user_id}", response_model=WalletResponse)
async def get_wallet(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
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
    try:
        wallet = await WalletService.add_balance(db, user_id, data.amount)
        return wallet_to_response(wallet)
    except WalletNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
