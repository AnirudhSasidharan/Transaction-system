from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.transaction import TransactionCreate, TransactionResponse
from app.services.auth_service import get_optional_user_id
from app.services.transaction_service import TransactionService
from app.services.wallet_service import WalletNotFoundError

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    data: TransactionCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor_user_id: str | None = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        transaction = await TransactionService.create_transaction(
            db,
            data,
            idempotency_key=idempotency_key,
            actor_user_id=actor_user_id,
        )
        return transaction
    except WalletNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history/me", response_model=list[TransactionResponse])
async def get_my_transaction_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    transactions = await TransactionService.get_user_transactions(
        db,
        user_id,
        limit=limit,
        offset=offset,
    )
    return transactions


@router.get("/history/{user_id}", response_model=list[TransactionResponse])
async def get_transaction_history(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    try:
        transactions = await TransactionService.get_user_transactions(
            db, user_id, limit=limit, offset=offset
        )
        return transactions
    except WalletNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
):
    transaction = await TransactionService.get_transaction(db, transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} not found",
        )
    return transaction
