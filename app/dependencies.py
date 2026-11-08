"""
dependencies.py
---------------
FastAPI dependencies for authentication & role checks.
"""

from typing import List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_token

# Palitan natin ito para lumabas ang tamang "Value" box sa Swagger
from fastapi.security import HTTPBearer
security_scheme = HTTPBearer(auto_error=False) # <--- Idinagdag ang auto_error=False


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode JWT, load the user from DB, or raise 401."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise credentials_exc

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exc

    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        raise credentials_exc

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exc
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return user


def require_role(*allowed_roles: str):
    """
    Factory that returns a dependency requiring one of the given roles.
    Usage:  user = Depends(require_role("admin", "rider"))
    """
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(allowed_roles)}",
            )
        return current_user
    return checker