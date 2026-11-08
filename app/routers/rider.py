"""
routers/rider.py
----------------
Endpoints for riders to view their assigned orders and update status.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.dependencies import require_role
from app.models import User, Order, Rider, Wallet
from app.routers.orders import OrderResponse
from app.security import hash_password

router = APIRouter(prefix="/rider", tags=["Rider"])


class RiderStatusUpdate(BaseModel):
    status: str


# ✅ BAGONG SCHEMA PARA SA RIDER REGISTRATION
class RiderRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    contact_number: str
    password: str
    default_address: str


# ✅ BAGONG ENDPOINT: Rider Registration
@router.post("/register", status_code=201)
def register_rider(payload: RiderRegisterRequest, db: Session = Depends(get_db)):
    # 1. Check kung existing na
    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_contact = db.query(User).filter(User.contact_number == payload.contact_number).first()
    if existing_contact:
        raise HTTPException(status_code=400, detail="Contact number already registered")

    # 2. Gawa ng bagong User
    new_user = User(
        full_name=payload.full_name.strip(),
        email=payload.email.lower().strip(),
        contact_number=payload.contact_number.strip(),
        password_hash=hash_password(payload.password),
        default_address=payload.default_address.strip(),
        role="rider",           # ✅ Rider agad
        is_active=True,
        is_verified=False       # ✅ Pending approval
    )
    db.add(new_user)
    db.flush()  # get id without commit yet

    # 3. Auto-create wallet
    wallet = Wallet(user_id=new_user.id, balance_centavos=0)
    db.add(wallet)

    # 4. Auto-create Rider profile
    new_rider = Rider(
        user_id=new_user.id,
        full_name=new_user.full_name,
        contact_number=new_user.contact_number,
        is_available=True
    )
    db.add(new_rider)

    db.commit()
    db.refresh(new_user)

    return {
        "message": "Rider registered successfully. Please wait for admin approval.",
        "user_id": new_user.id
    }


# ✅ KUNIN ANG MGA ASSIGNED ORDERS
@router.get("/orders", response_model=List[OrderResponse])
def get_assigned_orders(
    current_user: User = Depends(require_role("rider")),
    db: Session = Depends(get_db)
):
    rider = db.query(Rider).filter(Rider.user_id == current_user.id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider profile not found")

    orders = (
        db.query(Order)
        .filter(
            Order.assigned_rider_id == rider.id,
            Order.order_status.in_(["preparing", "out_for_delivery"]) 
        )
        .order_by(Order.created_at.desc())
        .all()
    )
    
    for o in orders:
        if o.user_id:
            cust = db.query(User).filter(User.id == o.user_id).first()
            if cust:
                o.customer_name = cust.full_name

    return orders


# ✅ UPDATE ORDER STATUS
@router.patch("/orders/{order_id}/status")
def update_status(
    order_id: int,
    payload: RiderStatusUpdate,
    current_user: User = Depends(require_role("rider")),
    db: Session = Depends(get_db)
):
    rider = db.query(Rider).filter(Rider.user_id == current_user.id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider profile not found")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.assigned_rider_id != rider.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this order")

    order.order_status = payload.status
    db.commit()
    db.refresh(order)
    return order