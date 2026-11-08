
"""
routers/products.py
-------------------
Public endpoints para sa mga water products.
"""

from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import WaterProduct

router = APIRouter(prefix="/products", tags=["Products"])


# ============================================================
# PRODUCT RESPONSE
# ============================================================

class ProductResponse(BaseModel):
    id: int
    product_name: str
    description: Optional[str] = None
    category: str
    container_type: Optional[str] = None

    refill_option_supported: bool

    # PRODUCT PRICES
    price_centavos: int
    refill_price_centavos: Optional[int] = None
    swap_price_centavos: Optional[int] = None

    image_url: Optional[str] = None
    stock_quantity: int
    is_available: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# GET ALL PRODUCTS
# ============================================================

@router.get("", response_model=List[ProductResponse])
def list_products(
    category: Optional[str] = Query(
        None,
        description="Filter by category"
    ),
    available_only: bool = Query(
        True,
        description="Show only available products"
    ),
    db: Session = Depends(get_db),
):
    """
    Return all water products.

    Includes:
    - Unique product ID
    - New price
    - Refill price
    - Swap price
    - Stock quantity
    - Availability
    """

    query = db.query(WaterProduct)

    if category:
        query = query.filter(
            WaterProduct.category == category
        )

    if available_only:
        query = query.filter(
            WaterProduct.is_available == True
        )

    products = query.order_by(
        WaterProduct.id
    ).all()

    return products


# ============================================================
# GET SINGLE PRODUCT
# ============================================================

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Return a single product using its unique database ID.
    """

    product = (
        db.query(WaterProduct)
        .filter(WaterProduct.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product
