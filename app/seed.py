"""
seed.py
-------
Development seed data: creates default admin account and sample products.
"""

from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import User, Wallet, WaterProduct
from app.security import hash_password


def utcnow():
    return datetime.now(timezone.utc)


def seed():
    db = SessionLocal()
    try:
        admin_email = "admin@vitasip.com"
        existing = db.query(User).filter(User.email == admin_email).first()
        
        if existing:
            print(f"✅ Admin already exists: {admin_email}")
        else:
            admin = User(
                full_name="Admin User",
                email=admin_email,
                contact_number="09170000001",
                password_hash=hash_password("admin123"),
                role="admin",
                default_address="Peñaranda, Nueva Ecija",
                is_active=True,
                is_verified=True,
            )
            db.add(admin)
            db.flush()
            db.add(Wallet(user_id=admin.id, balance_centavos=0))
            print(f"✅ Created admin: {admin_email} / admin123")

        # ✅ GUMAWA NG SAMPLE PRODUCTS (may 3 prices)
        if db.query(WaterProduct).count() == 0:
            products = [
                WaterProduct(
                    product_name="20L Slim Tap",
                    description="Slim container with tap",
                    category="20L Container",
                    price_centavos=35000,        # NEW: ₱350.00
                    refill_price_centavos=2500,  # REFILL: ₱25.00
                    swap_price_centavos=3500,    # SWAP: ₱35.00
                    stock_quantity=38,
                    is_available=True
                ),
                WaterProduct(
                    product_name="20L Round Dispenser",
                    description="Classic round container",
                    category="20L Container",
                    price_centavos=30000,        # NEW: ₱300.00
                    refill_price_centavos=2500,  # REFILL: ₱25.00
                    swap_price_centavos=3500,    # SWAP: ₱35.00
                    stock_quantity=41,
                    is_available=True
                ),
                WaterProduct(
                    product_name="500ml Bottled Case (24pcs)",
                    description="24 x 500ml",
                    category="Bottled",
                    price_centavos=36000,        # NEW: ₱360.00
                    refill_price_centavos=None,  # Walang refill
                    swap_price_centavos=None,    # Walang swap
                    stock_quantity=6,
                    is_available=True
                ),
            ]
            db.add_all(products)
            print(f"✅ Created {len(products)} sample products.")
        else:
            print("ℹ️ Products already exist.")

        db.commit()
        print("\n🎉 Seeding complete!")
    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()