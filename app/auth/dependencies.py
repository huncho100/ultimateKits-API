from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.service import AuthService
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
    decodes the JWT, retrieves the user from the
    database, and verifies that the account is active.
    """

    token = credentials.credentials

    # ------------------------------------------
    # Decode JWT
    # ------------------------------------------

    try:
        payload = decode_access_token(token)

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
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