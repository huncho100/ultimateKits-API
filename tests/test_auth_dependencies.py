import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_admin,
    get_current_user,
)
from app.models.user import User
from app.utils.security import create_access_token


# ==========================================
# Test Helpers
# ==========================================

def create_test_user(
    db: Session,
    *,
    role: str = "customer",
    is_active: bool = True,
) -> User:
    """
    Create a temporary user for dependency tests.
    """

    user = User(
        first_name="Dependency",
        last_name="Test",
        email=(
            f"dependency_{uuid.uuid4().hex[:8]}"
            "@example.com"
        ),
        password_hash="test-password-hash",
        role=role,
        is_active=is_active,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def create_user_token(user: User) -> str:
    """
    Create a JWT for a test user.
    """

    return create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }
    )


class Credentials:
    """
    Simple test replacement for
    HTTPAuthorizationCredentials.
    """

    def __init__(self, token: str):
        self.credentials = token


# ==========================================
# Get Current User
# ==========================================

def test_get_current_user_valid_token(db: Session):
    """
    A valid JWT should return the corresponding user.
    """

    user = create_test_user(db)

    token = create_user_token(user)

    result = get_current_user(
        credentials=Credentials(token),
        db=db,
    )

    assert result.id == user.id
    assert result.email == user.email
    assert result.role == "customer"

    print("✓ get_current_user valid token test passed")


# ==========================================
# Invalid Token
# ==========================================

def test_get_current_user_invalid_token(db: Session):
    """
    An invalid JWT should return HTTP 401.
    """

    with pytest.raises(HTTPException) as error:
        get_current_user(
            credentials=Credentials("invalid-token"),
            db=db,
        )

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid or expired token."

    print("✓ get_current_user invalid token test passed")


# ==========================================
# Missing Subject
# ==========================================

def test_get_current_user_missing_subject(db: Session):
    """
    A JWT without a subject should return HTTP 401.
    """

    token = create_access_token(
        {
            "email": "test@example.com",
            "role": "customer",
        }
    )

    with pytest.raises(HTTPException) as error:
        get_current_user(
            credentials=Credentials(token),
            db=db,
        )

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid authentication token."

    print("✓ Missing subject test passed")


# ==========================================
# Invalid User ID
# ==========================================

def test_get_current_user_invalid_user_id(db: Session):
    """
    A JWT with an invalid user ID should return HTTP 401.
    """

    token = create_access_token(
        {
            "sub": "not-an-integer",
            "email": "test@example.com",
            "role": "customer",
        }
    )

    with pytest.raises(HTTPException) as error:
        get_current_user(
            credentials=Credentials(token),
            db=db,
        )

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid authentication token."

    print("✓ Invalid user ID test passed")


# ==========================================
# Nonexistent User
# ==========================================

def test_get_current_user_nonexistent_user(db: Session):
    """
    A JWT containing a nonexistent user ID should
    return HTTP 401.
    """

    token = create_access_token(
        {
            "sub": "999999999",
            "email": "nonexistent@example.com",
            "role": "customer",
        }
    )

    with pytest.raises(HTTPException) as error:
        get_current_user(
            credentials=Credentials(token),
            db=db,
        )

    assert error.value.status_code == 401
    assert error.value.detail == "User no longer exists."

    print("✓ Nonexistent user test passed")


# ==========================================
# Inactive User
# ==========================================

def test_get_current_user_inactive_user(db: Session):
    """
    An inactive user should receive HTTP 403.
    """

    user = create_test_user(
        db,
        is_active=False,
    )

    token = create_user_token(user)

    with pytest.raises(HTTPException) as error:
        get_current_user(
            credentials=Credentials(token),
            db=db,
        )

    assert error.value.status_code == 403
    assert error.value.detail == "User account is inactive."

    print("✓ Inactive user test passed")


# ==========================================
# Admin Authorization
# ==========================================

def test_get_current_admin():
    """
    An admin user should pass the admin dependency.
    """

    admin = User(
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        password_hash="test-password-hash",
        role="admin",
        is_active=True,
    )

    result = get_current_admin(
        current_user=admin,
    )

    assert result is admin
    assert result.role == "admin"

    print("✓ Admin authorization test passed")


# ==========================================
# Customer Cannot Access Admin
# ==========================================

def test_get_current_admin_customer_forbidden():
    """
    A customer should receive HTTP 403 when attempting
    to access an admin-only dependency.
    """

    customer = User(
        first_name="Customer",
        last_name="User",
        email="customer@example.com",
        password_hash="test-password-hash",
        role="customer",
        is_active=True,
    )

    with pytest.raises(HTTPException) as error:
        get_current_admin(
            current_user=customer,
        )

    assert error.value.status_code == 403
    assert error.value.detail == "Administrator access required."

    print("✓ Customer admin restriction test passed")