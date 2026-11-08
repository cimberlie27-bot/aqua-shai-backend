"""
routers/wallet.py
-----------------
Wallet balance & transaction history.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Wallet, WalletTransaction
from app.schemas import WalletResponse, WalletTransactionResponse

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.get("", response_model=WalletResponse)
def get_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return current user's wallet balance."""
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet


@router.get("/transactions", response_model=List[WalletTransactionResponse])
def get_wallet_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return current user's wallet transaction history."""
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    transactions = (
        db.query(WalletTransaction)
        .filter(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
        .all()
    )
    return transactions