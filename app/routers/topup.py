"""
routers/topup.py
----------------
Customer-side endpoints for requesting wallet top-ups.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, TopUpRequest as TopUpRequestModel, Wallet

router = APIRouter(prefix="/topup", tags=["Top-Up (Customer)"])


class TopUpRequestCreate(BaseModel):
    amount_centavos: int
    payment_method: str  # "gcash", "maya", "bank"
    reference_number: Optional[str] = None
    proof_image_url: Optional[str] = None


@router.post("/request")
def create_topup_request(
    payload: TopUpRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if payload.amount_centavos <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if payload.payment_method not in ("gcash", "maya", "bank"):
        raise HTTPException(status_code=400, detail="Invalid payment method")

    new_request = TopUpRequestModel(
        user_id=current_user.id,
        amount_centavos=payload.amount_centavos,
        payment_method=payload.payment_method,
        reference_number=payload.reference_number,
        proof_image_url=payload.proof_image_url,
        status="pending",
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return {"message": "Top-up request submitted", "id": new_request.id, "status": new_request.status}


@router.get("/my-requests")
def get_my_topup_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    requests = (
        db.query(TopUpRequestModel)
        .filter(TopUpRequestModel.user_id == current_user.id)
        .order_by(TopUpRequestModel.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "amount_centavos": r.amount_centavos,
            "payment_method": r.payment_method,
            "reference_number": r.reference_number,
            "status": r.status,
            "admin_notes": r.admin_notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in requests
    ]


@router.get("/notifications")
def get_topup_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # I-return ang mga requests na na-approve o na-reject recently
    requests = (
        db.query(TopUpRequestModel)
        .filter(
            TopUpRequestModel.user_id == current_user.id,
            TopUpRequestModel.status.in_(["approved", "rejected"])
        )
        .order_by(TopUpRequestModel.processed_at.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "id": r.id,
            "status": r.status,
            "amount_centavos": r.amount_centavos,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            "message": f"Your ₱{r.amount_centavos/100:.2f} top-up was {r.status}",
        }
        for r in requests
    ]