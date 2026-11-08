"""
routers/orders.py
-----------------
Place orders, view history, track status.
"""

import secrets
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import (
    User, Order, OrderItem, WaterProduct, Voucher, VoucherUsage,
    Wallet, WalletTransaction, DeliveryStatusHistory, Rider
)

router = APIRouter(prefix="/orders", tags=["Orders"])


# =====================================================================
# SCHEMAS
# =====================================================================
class OrderItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1)
    container_type: Optional[str] = None
    refill_option: Optional[str] = None


class PlaceOrderRequest(BaseModel):
    items: List[OrderItemRequest] = Field(..., min_length=1)
    delivery_method: str
    delivery_address: Optional[str] = None
    payment_method: str
    voucher_code: Optional[str] = None


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name_snapshot: str
    container_type: Optional[str]
    refill_option: Optional[str]
    quantity: int
    unit_price_centavos: int
    subtotal_centavos: int

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    order_number: str
    delivery_method: str
    delivery_address: Optional[str]
    payment_method: str
    payment_status: str
    order_status: str
    subtotal_centavos: int
    discount_amount_centavos: int
    total_amount_centavos: int
    assigned_rider_id: Optional[int] = None
    created_at: datetime
    items: List[OrderItemResponse]

    customer_name: Optional[str] = None
    rider_name: Optional[str] = None
    rider_contact: Optional[str] = None

    class Config:
        from_attributes = True


class TrackingStep(BaseModel):
    status: str
    notes: Optional[str]
    created_at: datetime


class TrackingResponse(BaseModel):
    order_number: str
    order_status: str
    delivery_method: str
    steps: List[TrackingStep]


# =====================================================================
# HELPERS
# =====================================================================
def generate_order_number() -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    rand = secrets.token_hex(3).upper()
    return f"VS-{today}-{rand}"


def calculate_totals(db: Session, items: List[OrderItemRequest], voucher_code: Optional[str]):
    subtotal = 0
    items_snapshot = []

    for item in items:
        product = db.query(WaterProduct).filter(
            WaterProduct.id == item.product_id,
            WaterProduct.is_available == True,
        ).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not found or unavailable")
        if product.stock_quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.product_name}")
        
        line_total = product.price_centavos * item.quantity
        subtotal += line_total

        items_snapshot.append({
            "product": product,
            "quantity": item.quantity,
            "unit_price": product.price_centavos,
            "subtotal": line_total,
            "container_type": item.container_type or product.container_type,
            "refill_option": item.refill_option,
        })

    discount = 0
    voucher_obj = None
    if voucher_code:
        code = voucher_code.strip().upper()
        voucher_obj = db.query(Voucher).filter(Voucher.voucher_code == code).first()
        if not voucher_obj or not voucher_obj.is_active:
            raise HTTPException(status_code=400, detail="Invalid voucher")
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        if voucher_obj.expiration_date and now > voucher_obj.expiration_date:
            raise HTTPException(status_code=400, detail="Voucher expired")
        if voucher_obj.usage_limit is not None and voucher_obj.usage_count >= voucher_obj.usage_limit:
            raise HTTPException(status_code=400, detail="Voucher usage limit reached")
        if subtotal < voucher_obj.minimum_order_amount_centavos:
            raise HTTPException(status_code=400, detail="Minimum order amount not met for voucher")

        if voucher_obj.discount_type == "percentage":
            raw = subtotal * voucher_obj.discount_value // 100
            if voucher_obj.maximum_discount_centavos:
                raw = min(raw, voucher_obj.maximum_discount_centavos)
            discount = raw
        else:
            discount = voucher_obj.discount_value

        discount = min(discount, subtotal)

    return items_snapshot, subtotal, discount, voucher_obj


# =====================================================================
# PLACE ORDER
# =====================================================================
@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def place_order(
    payload: PlaceOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # VERIFICATION CHECK - DAPAT VERIFIED ANG CUSTOMER
    if not current_user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Your account is not yet verified. Please wait for admin approval before placing orders."
        )

    if payload.delivery_method not in ("delivery", "pickup"):
        raise HTTPException(status_code=400, detail="Invalid delivery_method")
    if payload.payment_method not in ("wallet", "cod"):
        raise HTTPException(status_code=400, detail="Invalid payment_method")
    if payload.delivery_method == "delivery" and not payload.delivery_address:
        raise HTTPException(status_code=400, detail="delivery_address required for delivery")

    items_snapshot, subtotal, discount, voucher_obj = calculate_totals(
        db, payload.items, payload.voucher_code
    )
    total = subtotal - discount

    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(status_code=400, detail="Wallet not found")

    if payload.payment_method == "wallet":
        if wallet.balance_centavos < total:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient wallet balance. Need ₱{total/100:.2f}, have ₱{wallet.balance_centavos/100:.2f}",
            )

    order_number = generate_order_number()
    initial_status = "confirmed"
    order = Order(
        order_number=order_number,
        user_id=current_user.id,
        delivery_method=payload.delivery_method,
        delivery_address=payload.delivery_address if payload.delivery_method == "delivery" else None,
        payment_method=payload.payment_method,
        payment_status="paid" if payload.payment_method == "wallet" else "pending",
        order_status=initial_status,
        subtotal_centavos=subtotal,
        discount_amount_centavos=discount,
        total_amount_centavos=total,
        voucher_id=voucher_obj.id if voucher_obj else None,
    )
    db.add(order)
    db.flush()

    for snap in items_snapshot:
        db.add(OrderItem(
            order_id=order.id,
            product_id=snap["product"].id,
            product_name_snapshot=snap["product"].product_name,
            container_type=snap["container_type"],
            refill_option=snap["refill_option"],
            quantity=snap["quantity"],
            unit_price_centavos=snap["unit_price"],
            subtotal_centavos=snap["subtotal"],
        ))
        snap["product"].stock_quantity -= snap["quantity"]

    if payload.payment_method == "wallet":
        balance_before = wallet.balance_centavos
        wallet.balance_centavos -= total
        wallet.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(WalletTransaction(
            wallet_id=wallet.id,
            order_id=order.id,
            transaction_type="deduction",
            amount_centavos=total,
            balance_before_centavos=balance_before,
            balance_after_centavos=wallet.balance_centavos,
            description=f"Payment for order {order_number}",
        ))

    if voucher_obj:
        voucher_obj.usage_count += 1
        db.add(VoucherUsage(
            voucher_id=voucher_obj.id,
            user_id=current_user.id,
            order_id=order.id,
        ))

    db.add(DeliveryStatusHistory(
        order_id=order.id,
        status=initial_status,
        notes="Order has been confirmed",
    ))

    db.commit()
    db.refresh(order)
    return order


# =====================================================================
# LIST MY ORDERS
# =====================================================================
@router.get("", response_model=List[OrderResponse])
def list_my_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    orders = (
        db.query(Order)
        .filter(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    for o in orders:
        if o.user_id:
            cust = db.query(User).filter(User.id == o.user_id).first()
            if cust:
                o.customer_name = cust.full_name
        if o.assigned_rider_id:
            rider = db.query(Rider).filter(Rider.id == o.assigned_rider_id).first()
            if rider:
                o.rider_name = rider.full_name
                o.rider_contact = rider.contact_number
    return orders


# =====================================================================
# GET ONE ORDER
# =====================================================================
@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != current_user.id and current_user.role not in ("admin", "rider"):
        raise HTTPException(status_code=403, detail="Not allowed")
    
    if order.user_id:
        cust = db.query(User).filter(User.id == order.user_id).first()
        if cust:
            order.customer_name = cust.full_name
    if order.assigned_rider_id:
        rider = db.query(Rider).filter(Rider.id == order.assigned_rider_id).first()
        if rider:
            order.rider_name = rider.full_name
            order.rider_contact = rider.contact_number

    return order


# =====================================================================
# TRACKING
# =====================================================================
@router.get("/{order_id}/tracking", response_model=TrackingResponse)
def track_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != current_user.id and current_user.role not in ("admin", "rider"):
        raise HTTPException(status_code=403, detail="Not allowed")

    steps = (
        db.query(DeliveryStatusHistory)
        .filter(DeliveryStatusHistory.order_id == order.id)
        .order_by(DeliveryStatusHistory.created_at.asc())
        .all()
    )
    return TrackingResponse(
        order_number=order.order_number,
        order_status=order.order_status,
        delivery_method=order.delivery_method,
        steps=[TrackingStep(status=s.status, notes=s.notes, created_at=s.created_at) for s in steps],
    )