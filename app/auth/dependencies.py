import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.utils.security import (
    TokenType,
    decode_access_token,
    token_predates_password_change,
)


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
    decodes the JWT, retrieves the user from the
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
    # Reject tokens issued for another purpose
    # ------------------------------------------

    # A password reset token is a valid signature over the
    # same user id. Without this check it authenticates as
    # a full session, which defeats the point of scoping it
    # to a reset. Absence of the claim fails closed.

    if payload.get("type") != TokenType.ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # ------------------------------------------
    # Extract user ID
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
    # Convert user ID
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
    # Find user
    # ------------------------------------------

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    # ------------------------------------------
    # User doesn't exist
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
    # Token predates the last password change
    # ------------------------------------------

    # Changing a password must end every session that was
    # open at the time, otherwise a user whose account is
    # compromised cannot take it back.

    if token_predates_password_change(
        payload,
        user.password_changed_at,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Session is no longer valid. "
                "Please sign in again."
            ),
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # ------------------------------------------
    # User inactive
    # ------------------------------------------

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user


# ==========================================
# Get Current Admin
# ==========================================

def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the currently authenticated administrator.

    Requires:
    - A valid JWT
    - An existing user
    - An active account
    - The 'admin' role
    """

    # ------------------------------------------
    # Verify admin role
    # ------------------------------------------

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )

    return current_user