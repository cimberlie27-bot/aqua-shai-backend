"""
models.py
---------
Lahat ng database tables para sa Aqua Shai.

IMPORTANTE: Lahat ng pera (presyo, balance, total) ay naka-store
as INTEGER CENTAVOS. Halimbawa: ₱25.50 = 2550 centavos.
NEVER use float para sa pera!
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Numeric
)
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


# =====================================================================
# USERS
# =====================================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    contact_number = Column(String(20), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    default_address = Column(Text, nullable=True)
    role = Column(String(20), nullable=False, default="customer")  # customer / admin / rider
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", foreign_keys="Order.user_id")
    saved_addresses = relationship("SavedAddress", back_populates="user", cascade="all, delete-orphan")


# =====================================================================
# WALLETS & WALLET_TRANSACTIONS
# =====================================================================
class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance_centavos = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    transaction_type = Column(String(30), nullable=False)  # topup / deduction / refund / adjustment
    amount_centavos = Column(Integer, nullable=False)
    balance_before_centavos = Column(Integer, nullable=False)
    balance_after_centavos = Column(Integer, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    wallet = relationship("Wallet", back_populates="transactions")


# =====================================================================
# WATER_PRODUCTS
# =====================================================================
class WaterProduct(Base):
    __tablename__ = "water_products"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)
    container_type = Column(String(50), nullable=True)
    refill_option_supported = Column(Boolean, default=True, nullable=False)
    
    # ✅ TATLONG PRESYO
    price_centavos = Column(Integer, nullable=False)           # NEW container price
    refill_price_centavos = Column(Integer, nullable=True)     # REFILL price
    swap_price_centavos = Column(Integer, nullable=True)       # SWAP price
    
    image_url = Column(String(255), nullable=True)
    stock_quantity = Column(Integer, default=0, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


# =====================================================================
# VOUCHERS & VOUCHER_USAGES
# =====================================================================
class Voucher(Base):
    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, index=True)
    voucher_code = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    discount_type = Column(String(20), nullable=False)
    discount_value = Column(Integer, nullable=False)
    minimum_order_amount_centavos = Column(Integer, default=0, nullable=False)
    maximum_discount_centavos = Column(Integer, nullable=True)
    usage_limit = Column(Integer, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    expiration_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class VoucherUsage(Base):
    __tablename__ = "voucher_usages"

    id = Column(Integer, primary_key=True, index=True)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    used_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


# =====================================================================
# RIDERS
# =====================================================================
class Rider(Base):
    __tablename__ = "riders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String(120), nullable=False)
    contact_number = Column(String(20), nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)


# =====================================================================
# ORDERS & ORDER_ITEMS
# =====================================================================
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(30), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    delivery_method = Column(String(20), nullable=False)
    delivery_address = Column(Text, nullable=True)
    payment_method = Column(String(20), nullable=False)
    payment_status = Column(String(20), default="pending", nullable=False)
    order_status = Column(String(30), default="confirmed", nullable=False)
    subtotal_centavos = Column(Integer, nullable=False, default=0)
    discount_amount_centavos = Column(Integer, nullable=False, default=0)
    total_amount_centavos = Column(Integer, nullable=False, default=0)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=True)
    assigned_rider_id = Column(Integer, ForeignKey("riders.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="orders", foreign_keys=[user_id])
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship("DeliveryStatusHistory", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("water_products.id"), nullable=False)
    product_name_snapshot = Column(String(120), nullable=False)
    container_type = Column(String(50), nullable=True)
    refill_option = Column(String(30), nullable=True)
    quantity = Column(Integer, nullable=False)
    unit_price_centavos = Column(Integer, nullable=False)
    subtotal_centavos = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")


# =====================================================================
# DELIVERY STATUS HISTORY
# =====================================================================
class DeliveryStatusHistory(Base):
    __tablename__ = "delivery_status_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    status = Column(String(30), nullable=False)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    order = relationship("Order", back_populates="status_history")


# =====================================================================
# SAVED ADDRESSES
# =====================================================================
class SavedAddress(Base):
    __tablename__ = "saved_addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    label = Column(String(50), nullable=True)
    address = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="saved_addresses")


# =====================================================================
# TOP-UP REQUESTS
# =====================================================================
class TopUpRequest(Base):
    __tablename__ = "topup_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_centavos = Column(Integer, nullable=False)
    payment_method = Column(String(50), nullable=False)
    reference_number = Column(String(100), nullable=True)
    proof_image_url = Column(String(500), nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    admin_notes = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)