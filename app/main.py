"""
main.py
-------
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine

# Import models so SQLAlchemy knows about them before create_all()
from app import models  # noqa: F401

# Import routers
from app.routers import auth, products, wallet, vouchers, orders, admin, rider, topup

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Aqua Shai Backend", # Pinalitan ang pangalan
    version="0.5.0",
    description="Aqua Shai backend — Water refilling station ordering & delivery.",
)

# CORS - PINAPAYAGAN NA LAHAT NG LOCAL URLS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8100",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8100",
        "http://192.168.100.9:5173",
        "http://192.168.100.9:8100",
        "http://192.168.100.9:8000",
        "*"  # Allow all for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
def read_root():
    return {
        "app": "Aqua Shai",
        "environment": settings.APP_ENV,
        "message": "Aqua Shai backend is running.",
        "docs": "/docs",
    }


@app.get("/health", tags=["Root"])
def health_check():
    return {"status": "ok"}


# =====================================================================
# ROUTERS
# =====================================================================
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(wallet.router)
app.include_router(vouchers.router)
app.include_router(orders.router)
app.include_router(admin.router)
app.include_router(rider.router)
app.include_router(topup.router)