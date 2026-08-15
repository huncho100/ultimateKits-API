import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.utils.security import decode_access_token


# ==========================================
# HTTP Bearer Authentication
# ==========================================

security = HTTPBearer()


# ==========================================
# Get Current User
# ==========================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the currently authenticated user.

    Extracts the JWT from the Authorization header,
    validates the token, retrieves the user from the
    database, and verifies that the account is active.
    """

    token = credentials.credentials

    # ------------------------------------------
    # Decode JWT
    # ------------------------------------------

    try:
        payload = decode_access_token(token)

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # ------------------------------------------
    # Extract User ID
    # ------------------------------------------

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # ------------------------------------------
    # Convert User ID
    # ------------------------------------------

    try:
        user_id = int(user_id)

    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # ------------------------------------------
    # Find User
    # ------------------------------------------

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    # ------------------------------------------
    # User Doesn't Exist
    # ------------------------------------------

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # ------------------------------------------
    # User Inactive
    # ------------------------------------------

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user