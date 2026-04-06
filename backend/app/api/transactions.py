"""
app/api/transactions.py
-----------------------
WHAT IS THIS?
  HTTP routes for creating and querying transactions.

  POST /api/v1/transactions/
    Creates a transaction and returns PENDING immediately.
    The worker processes it in the background.

  GET /api/v1/transactions/{id}
    Fetch a single transaction — use this to poll status if not using WebSocket.

  GET /api/v1/transactions/history/{user_id}
    Paginated transaction history.
    Query params: ?limit=20&offset=0

PAGINATION QUERY PARAMS:
  FastAPI reads these automatically from the URL:
  /history/user_001?limit=10&offset=20
  → limit=10, offset=20

  Query() lets you set defaults and validation:
  Query(default=50, ge=1, le=200) means:
    default value = 50
    minimum = 1
    maximum = 200
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.transaction import TransactionCreate, TransactionResponse
from app.services.transaction_service import TransactionService
from app.services.wallet_service import WalletNotFoundError

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create and enqueue a transaction.

    Returns immediately with status=pending.
    Track real-time progress via WebSocket: ws://localhost:8000/api/v1/ws/{user_id}
    Or poll status via: GET /api/v1/transactions/{id}
    """
    try:
        transaction = await TransactionService.create_transaction(db, data)
        return transaction
    except WalletNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history/{user_id}", response_model=list[TransactionResponse])
async def get_transaction_history(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated transaction history for a user.
    Ordered by newest first.
    """
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
    """Fetch a single transaction by ID."""
    transaction = await TransactionService.get_transaction(db, transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} not found",
        )
    return transaction
