
"""
routers/admin.py
----------------
Endpoints for administrators.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.dependencies import require_role
from app.models import (
    Voucher, User, Order, WaterProduct, Rider, Wallet, WalletTransaction,
    TopUpRequest as TopUpRequestModel, VoucherUsage, OrderItem
)
from app.security import hash_password

router = APIRouter(prefix="/admin", tags=["Admin"])


# =====================================================================
# SCHEMAS
# =====================================================================

class VoucherCreateRequest(BaseModel):
    voucher_code: str
    description: str
    discount_type: str
    discount_value: int
    minimum_order_amount_centavos: int = 0
    maximum_discount_centavos: int = 0
    usage_limit: int = 100
    start_date: datetime
    expiration_date: datetime
    is_active: bool = True


class ProductCreateRequest(BaseModel):
    product_name: str
    description: str
    category: str
    container_type: Optional[str] = None
    price_centavos: int
    image_url: Optional[str] = None
    stock_quantity: int = 100
    is_available: bool = True


class RiderCreateRequest(BaseModel):
    full_name: str
    contact_number: str


class OrderStatusUpdate(BaseModel):
    status: str


class AssignRiderRequest(BaseModel):
    rider_id: int


class TopUpActionRequest(BaseModel):
    action: str
    admin_notes: Optional[str] = None


class VerifyCustomerRequest(BaseModel):
    is_verified: bool


# =====================================================================
# VOUCHERS
# =====================================================================

@router.get("/vouchers")
def get_all_vouchers(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    return db.query(Voucher).order_by(Voucher.id.desc()).all()


@router.post("/vouchers")
def create_voucher(
    payload: VoucherCreateRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    existing = db.query(Voucher).filter(
        Voucher.voucher_code == payload.voucher_code.upper()
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Voucher code already exists")

    voucher = Voucher(
        voucher_code=payload.voucher_code.upper(),
        description=payload.description,
        discount_type=payload.discount_type,
        discount_value=payload.discount_value,
        minimum_order_amount_centavos=payload.minimum_order_amount_centavos,
        maximum_discount_centavos=payload.maximum_discount_centavos,
        usage_limit=payload.usage_limit,
        usage_count=0,
        start_date=payload.start_date,
        expiration_date=payload.expiration_date,
        is_active=payload.is_active,
    )

    db.add(voucher)
    db.commit()
    db.refresh(voucher)

    return voucher


@router.patch("/vouchers/{voucher_id}")
def update_voucher(
    voucher_id: int,
    payload: dict,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    voucher = db.query(Voucher).filter(
        Voucher.id == voucher_id
    ).first()

    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")

    if "is_active" in payload:
        voucher.is_active = payload["is_active"]

    if "usage_limit" in payload:
        voucher.usage_limit = payload["usage_limit"]

    db.commit()
    db.refresh(voucher)

    return voucher


@router.delete("/vouchers/{voucher_id}")
def delete_voucher(
    voucher_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    voucher = db.query(Voucher).filter(
        Voucher.id == voucher_id
    ).first()

    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")

    used_count = db.query(VoucherUsage).filter(
        VoucherUsage.voucher_id == voucher_id
    ).count()

    if used_count > 0:
        voucher.is_active = False
        db.commit()
        return {"message": f"Voucher deactivated (used {used_count} times)"}

    db.delete(voucher)
    db.commit()

    return {"message": "Voucher deleted"}


# =====================================================================
# PRODUCTS
# =====================================================================

@router.get("/products")
def get_all_products(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    return db.query(WaterProduct).all()


@router.post("/products")
def create_product(
    payload: ProductCreateRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    product = WaterProduct(**payload.dict(), refill_option_supported=True)

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    product = db.query(WaterProduct).filter(
        WaterProduct.id == product_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.query(OrderItem).filter(
        OrderItem.product_id == product_id
    ).delete()

    db.delete(product)
    db.commit()

    return {"message": "Product deleted permanently"}


@router.patch("/products/{product_id}")
def update_product(
    product_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    product = db.query(WaterProduct).filter(
        WaterProduct.id == product_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if "price_centavos" in payload:
        product.price_centavos = payload["price_centavos"]

    if "refill_price_centavos" in payload:
        product.refill_price_centavos = payload["refill_price_centavos"]

    if "swap_price_centavos" in payload:
        product.swap_price_centavos = payload["swap_price_centavos"]

    if "stock_quantity" in payload:
        product.stock_quantity = payload["stock_quantity"]

    if "is_available" in payload:
        product.is_available = payload["is_available"]

    db.commit()
    db.refresh(product)

    return product


# =====================================================================
# RIDERS
# =====================================================================

@router.get("/riders")
def get_all_riders(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    return db.query(Rider).all()


@router.post("/riders")
def create_rider(
    payload: RiderCreateRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    email = f"rider_{payload.contact_number}@vitasip.com"

    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if not existing_user:
        user = User(
            full_name=payload.full_name,
            email=email,
            contact_number=payload.contact_number,
            password_hash=hash_password("rider123"),
            role="rider",
            default_address="N/A",
            is_verified=True
        )

        db.add(user)
        db.flush()
        user_id = user.id
    else:
        user_id = existing_user.id

    rider = Rider(
        user_id=user_id,
        full_name=payload.full_name,
        contact_number=payload.contact_number,
        is_available=True
    )

    db.add(rider)
    db.commit()
    db.refresh(rider)

    return rider


@router.delete("/riders/{rider_id}")
def delete_rider(
    rider_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    rider = db.query(Rider).filter(
        Rider.id == rider_id
    ).first()

    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    if rider.user_id:
        user = db.query(User).filter(
            User.id == rider.user_id
        ).first()

        if user:
            db.delete(user)

    db.delete(rider)
    db.commit()

    return {"message": "Rider removed successfully"}


# =====================================================================
# PENDING RIDERS
# =====================================================================

@router.get("/riders/pending")
def get_pending_riders(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    pending_users = db.query(User).filter(
        User.role == "rider",
        User.is_verified == False
    ).all()

    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "contact_number": u.contact_number,
            "created_at": u.created_at
        }
        for u in pending_users
    ]


@router.patch("/riders/{user_id}/approve")
def approve_rider(
    user_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    rider_user = db.query(User).filter(
        User.id == user_id,
        User.role == "rider"
    ).first()

    if not rider_user:
        raise HTTPException(status_code=404, detail="Rider not found")

    rider_user.is_verified = True
    db.commit()

    return {"message": "Rider approved successfully"}


# =====================================================================
# ORDERS
# =====================================================================

@router.get("/orders")
def get_all_orders(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    orders = db.query(Order).order_by(
        Order.created_at.desc()
    ).all()

    result = []

    for o in orders:
        cust = db.query(User).filter(
            User.id == o.user_id
        ).first()

        rider = None

        if o.assigned_rider_id:
            rider = db.query(Rider).filter(
                Rider.id == o.assigned_rider_id
            ).first()

        result.append({
            "id": o.id,
            "order_number": o.order_number,
            "user_id": o.user_id,

            "customer_name": cust.full_name if cust else "Customer",
            "customer_contact": cust.contact_number if cust else None,

            "delivery_method": o.delivery_method,
            "delivery_address": o.delivery_address,

            "payment_method": o.payment_method,
            "payment_status": o.payment_status,
            "order_status": o.order_status,

            "subtotal_centavos": o.subtotal_centavos,
            "discount_amount_centavos": o.discount_amount_centavos,
            "total_amount_centavos": o.total_amount_centavos,

            "assigned_rider_id": o.assigned_rider_id,
            "rider_name": rider.full_name if rider else None,
            "rider_contact": rider.contact_number if rider else None,

            "created_at": o.created_at,

            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name_snapshot": item.product_name_snapshot,
                    "container_type": item.container_type,
                    "refill_option": item.refill_option,
                    "quantity": item.quantity,
                    "unit_price_centavos": item.unit_price_centavos,
                    "subtotal_centavos": item.subtotal_centavos
                }
                for item in o.items
            ]
        })

    return result


@router.patch("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(
        Order.id == order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.order_status = payload.status
    db.commit()
    db.refresh(order)

    return order


@router.patch("/orders/{order_id}/assign-rider")
def assign_rider_to_order(
    order_id: int,
    payload: AssignRiderRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(
        Order.id == order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    rider = db.query(Rider).filter(
        Rider.id == payload.rider_id
    ).first()

    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    order.assigned_rider_id = rider.id
    order.order_status = "out_for_delivery"

    db.commit()
    db.refresh(order)

    return order


# =====================================================================
# CUSTOMERS
# =====================================================================

@router.get("/customers")
def get_all_customers(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    customers = db.query(User).filter(
        User.role == "customer"
    ).all()

    result = []

    for c in customers:
        wallet = db.query(Wallet).filter(
            Wallet.user_id == c.id
        ).first()

        order_count = db.query(Order).filter(
            Order.user_id == c.id
        ).count()

        result.append({
            "id": c.id,
            "full_name": c.full_name,
            "email": c.email,
            "contact_number": c.contact_number,
            "default_address": c.default_address,
            "wallet_balance_centavos": wallet.balance_centavos if wallet else 0,
            "order_count": order_count,
            "is_verified": c.is_verified,
            "created_at": c.created_at.isoformat() if c.created_at else None
        })

    return result


@router.patch("/customers/{customer_id}/verify")
def verify_customer(
    customer_id: int,
    payload: VerifyCustomerRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    customer = db.query(User).filter(
        User.id == customer_id,
        User.role == "customer"
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer.is_verified = payload.is_verified
    db.commit()
    db.refresh(customer)

    return {
        "message": f"Customer {'verified' if payload.is_verified else 'unverified'}",
        "is_verified": customer.is_verified
    }


# =====================================================================
# TOP-UP REQUESTS
# =====================================================================

@router.get("/topup-requests")
def get_topup_requests(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    requests = db.query(TopUpRequestModel).order_by(
        TopUpRequestModel.created_at.desc()
    ).all()

    result = []

    for r in requests:
        cust = db.query(User).filter(
            User.id == r.user_id
        ).first()

        result.append({
            "id": r.id,
            "user_id": r.user_id,
            "customer_name": cust.full_name if cust else "Unknown",
            "customer_contact": cust.contact_number if cust else "",
            "amount_centavos": r.amount_centavos,
            "payment_method": r.payment_method,
            "reference_number": r.reference_number,
            "proof_image_url": r.proof_image_url,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return result


@router.post("/topup-requests/{request_id}/process")
def process_topup_request(
    request_id: int,
    payload: TopUpActionRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    topup_req = db.query(TopUpRequestModel).filter(
        TopUpRequestModel.id == request_id
    ).first()

    if not topup_req:
        raise HTTPException(status_code=404, detail="Request not found")

    if topup_req.status != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")

    if payload.action == "approve":
        wallet = db.query(Wallet).filter(
            Wallet.user_id == topup_req.user_id
        ).first()

        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")

        balance_before = wallet.balance_centavos
        wallet.balance_centavos += topup_req.amount_centavos
        wallet.updated_at = datetime.now()

        db.add(WalletTransaction(
            wallet_id=wallet.id,
            order_id=None,
            transaction_type="topup",
            amount_centavos=topup_req.amount_centavos,
            balance_before_centavos=balance_before,
            balance_after_centavos=wallet.balance_centavos,
            description=f"Top-up approved (Ref: {topup_req.reference_number})",
        ))

        topup_req.status = "approved"

    elif payload.action == "reject":
        topup_req.status = "rejected"

    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    topup_req.admin_notes = payload.admin_notes
    topup_req.processed_at = datetime.now()

    db.commit()
    db.refresh(topup_req)

    return {
        "message": f"Request {payload.action}d",
        "status": topup_req.status
    }


# =====================================================================
# DELETE CUSTOMER
# =====================================================================

@router.delete("/customers/{customer_id}")
def delete_customer(
    customer_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    customer = db.query(User).filter(
        User.id == customer_id,
        User.role == "customer"
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # 1. Delete related data first to avoid foreign key errors
    db.query(Wallet).filter(
        Wallet.user_id == customer_id
    ).delete()

    db.query(WalletTransaction).filter(
        WalletTransaction.wallet_id.in_(
            db.query(Wallet.id).filter(Wallet.user_id == customer_id)
        )
    ).delete()

    db.query(Order).filter(
        Order.user_id == customer_id
    ).delete()

    db.query(TopUpRequestModel).filter(
        TopUpRequestModel.user_id == customer_id
    ).delete()

    # 2. Delete the user
    db.delete(customer)
    db.commit()

    return {"message": "Customer deleted permanently"}
