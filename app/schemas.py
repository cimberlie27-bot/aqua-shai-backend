"""
schemas.py
----------
Pydantic schemas for request validation & response serialization.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator


# =====================================================================
# USER / AUTH
# =====================================================================
class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    contact_number: str = Field(..., min_length=7, max_length=20)
    default_address: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6, max_length=128)
    
    # ✅ BAGONG FIELD: role (default: customer)
    role: str = "customer"

    @field_validator("contact_number")
    @classmethod
    def clean_contact(cls, v: str) -> str:
        v = v.strip()
        if not v.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise ValueError("Contact number must contain only digits, +, -, or spaces")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        # ✅ Bawal mag-register as admin via public API
        allowed = ["customer", "rider"]
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    contact_number: str
    default_address: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# =====================================================================
# WALLET
# =====================================================================
class WalletResponse(BaseModel):
    balance_centavos: int
    updated_at: datetime

    class Config:
        from_attributes = True


class WalletTransactionResponse(BaseModel):
    id: int
    order_id: Optional[int] = None
    transaction_type: str
    amount_centavos: int
    balance_before_centavos: int
    balance_after_centavos: int
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================================================
# ORDER SCHEMAS
# =====================================================================
class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name_snapshot: str
    container_type: Optional[str] = None
    refill_option: Optional[str] = None
    quantity: int
    unit_price_centavos: int
    subtotal_centavos: int

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    order_number: str
    delivery_method: str
    delivery_address: Optional[str] = None
    payment_method: str
    payment_status: str
    order_status: str
    subtotal_centavos: int
    discount_amount_centavos: int
    total_amount_centavos: int
    assigned_rider_id: Optional[int] = None
    created_at: datetime
    items: List[OrderItemResponse] = []

    # Customer & Rider details
    customer_name: Optional[str] = None
    rider_name: Optional[str] = None
    rider_contact: Optional[str] = None

    class Config:
        from_attributes = True