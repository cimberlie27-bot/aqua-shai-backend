"""
routers/vouchers.py
-------------------
Validate discount voucher codes.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Voucher, User

router = APIRouter(prefix="/vouchers", tags=["Vouchers"])


class VoucherValidateRequest(BaseModel):
    voucher_code: str
    order_subtotal_centavos: int = Field(..., ge=0)


class VoucherValidateResponse(BaseModel):
    valid: bool
    voucher_code: str
    description: Optional[str] = None
    discount_amount_centavos: int = 0
    message: str


@router.post("/validate", response_model=VoucherValidateResponse)
def validate_voucher(
    payload: VoucherValidateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Validate a voucher code against a given order subtotal.
    Does NOT consume the voucher — just checks eligibility.
    """
    code = payload.voucher_code.strip().upper()
    subtotal = payload.order_subtotal_centavos

    voucher = db.query(Voucher).filter(Voucher.voucher_code == code).first()

    def _fail(msg: str):
        return VoucherValidateResponse(
            valid=False,
            voucher_code=code,
            discount_amount_centavos=0,
            message=msg,
        )

    if not voucher:
        return _fail("Voucher code not found")
    if not voucher.is_active:
        return _fail("Voucher is inactive")

    # GINAMITAN NG .replace(tzinfo=None) PARA MAIWAYAN ANG ERROR
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    if voucher.start_date and now < voucher.start_date:
        return _fail("Voucher is not yet active")
    if voucher.expiration_date and now > voucher.expiration_date:
        return _fail("Voucher has expired")

    if voucher.usage_limit is not None and voucher.usage_count >= voucher.usage_limit:
        return _fail("Voucher usage limit reached")

    if subtotal < voucher.minimum_order_amount_centavos:
        needed = (voucher.minimum_order_amount_centavos - subtotal) / 100
        return _fail(f"Minimum order not met. Add ₱{needed:.2f} more.")

    # Calculate discount
    if voucher.discount_type == "percentage":
        raw = subtotal * voucher.discount_value // 100
        if voucher.maximum_discount_centavos is not None:
            raw = min(raw, voucher.maximum_discount_centavos)
        discount = raw
    else:  # fixed
        discount = voucher.discount_value

    # Discount cannot exceed subtotal
    discount = min(discount, subtotal)

    return VoucherValidateResponse(
        valid=True,
        voucher_code=code,
        description=voucher.description,
        discount_amount_centavos=discount,
        message="Voucher applied successfully",
    )

"""
routers/vouchers.py
-------------------
Validate discount voucher codes and get active vouchers.
"""

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Voucher, User

router = APIRouter(prefix="/vouchers", tags=["Vouchers"])


class VoucherValidateRequest(BaseModel):
    voucher_code: str
    order_subtotal_centavos: int = Field(..., ge=0)


class VoucherValidateResponse(BaseModel):
    valid: bool
    voucher_code: str
    description: Optional[str] = None
    discount_amount_centavos: int = 0
    message: str


class PublicVoucherResponse(BaseModel):
    id: int
    voucher_code: str
    description: Optional[str] = None
    discount_type: str
    discount_value: int
    minimum_order_amount_centavos: int
    expiration_date: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[PublicVoucherResponse])
def get_active_vouchers(
    db: Session = Depends(get_db)
):
    """
    Return all active and non-expired vouchers for public display.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    vouchers = (
        db.query(Voucher)
        .filter(
            Voucher.is_active == True,
            Voucher.start_date <= now,
            Voucher.expiration_date >= now,
        )
        .all()
    )
    return vouchers


@router.post("/validate", response_model=VoucherValidateResponse)
def validate_voucher(
    payload: VoucherValidateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ... (keep existing code)
    code = payload.voucher_code.strip().upper()
    subtotal = payload.order_subtotal_centavos

    voucher = db.query(Voucher).filter(Voucher.voucher_code == code).first()

    def _fail(msg: str):
        return VoucherValidateResponse(
            valid=False,
            voucher_code=code,
            discount_amount_centavos=0,
            message=msg,
        )

    if not voucher:
        return _fail("Voucher code not found")
    if not voucher.is_active:
        return _fail("Voucher is inactive")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if voucher.start_date and now < voucher.start_date:
        return _fail("Voucher is not yet active")
    if voucher.expiration_date and now > voucher.expiration_date:
        return _fail("Voucher has expired")

    if voucher.usage_limit is not None and voucher.usage_count >= voucher.usage_limit:
        return _fail("Voucher usage limit reached")

    if subtotal < voucher.minimum_order_amount_centavos:
        needed = (voucher.minimum_order_amount_centavos - subtotal) / 100
        return _fail(f"Minimum order not met. Add ₱{needed:.2f} more.")

    if voucher.discount_type == "percentage":
        raw = subtotal * voucher.discount_value // 100
        if voucher.maximum_discount_centavos is not None:
            raw = min(raw, voucher.maximum_discount_centavos)
        discount = raw
    else:
        discount = voucher.discount_value

    discount = min(discount, subtotal)

    return VoucherValidateResponse(
        valid=True,
        voucher_code=code,
        description=voucher.description,
        discount_amount_centavos=discount,
        message="Voucher applied successfully",
    )