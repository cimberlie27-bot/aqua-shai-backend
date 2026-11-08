"""
routers/auth.py
---------------
Authentication endpoints: register, login, me.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Wallet, Rider
from app.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
)
from app.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Create a new account (customer OR rider).
    - Reject duplicate email or contact_number.
    - Auto-create a wallet with 0 balance.
    - LAHAT ay pending (is_verified = False) hangga't hindi ina-approve ng admin.
    """
    # Check duplicates
    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_contact = db.query(User).filter(User.contact_number == payload.contact_number).first()
    if existing_contact:
        raise HTTPException(status_code=400, detail="Contact number already registered")

    is_rider = payload.role == "rider"
    
    # ✅ PALITAN NATIN ITO: Lahat ng bagong register (customer o rider) ay False muna.
    is_verified_status = False 

    # Create user
    user = User(
        full_name=payload.full_name.strip(),
        email=payload.email.lower().strip(),
        contact_number=payload.contact_number.strip(),
        password_hash=hash_password(payload.password),
        default_address=payload.default_address.strip(),
        role=payload.role,
        is_active=True,
        is_verified=is_verified_status, # ✅ False para lahat pending
    )
    db.add(user)
    db.flush()

    # Create wallet
    wallet = Wallet(user_id=user.id, balance_centavos=0)
    db.add(wallet)

    # Kung rider, gawa rin tayo ng entry sa Rider table
    if is_rider:
        new_rider = Rider(
            user_id=user.id,
            full_name=user.full_name,
            contact_number=user.contact_number,
            is_available=True
        )
        db.add(new_rider)

    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id), role=user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Login with email OR contact number + password.
    """
    identifier = payload.email.strip().lower()

    user = db.query(User).filter(
        (User.email == identifier) | (User.contact_number == payload.email.strip())
    ).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # ✅ CHECK: Lahat ng hindi pa verified (customer man o rider), i-block.
    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Your account is pending admin approval. Please wait."
        )

    token = create_access_token(subject=str(user.id), role=user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the currently logged-in user's profile."""
    return current_user