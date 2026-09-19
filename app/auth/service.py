from datetime import timedelta

import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


class AuthService:
    """
    Handles authentication-related business logic.
    """

    # ==========================================
    # Find User
    # ==========================================

    @staticmethod
    def get_user_by_email(
        db: Session,
        email: str,
    ) -> User | None:
        """
        Find a user by email address.
        """

        return (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

    # ==========================================
    # Register User
    # ==========================================

    @staticmethod
    def register_user(
        db: Session,
        *,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
    ) -> User:
        """
        Create a new user.
        """

        existing_user = AuthService.get_user_by_email(
            db,
            email,
        )

        if existing_user:
            raise ValueError(
                "An account with this email already exists."
            )

        hashed_password = hash_password(password)

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=hashed_password,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    # ==========================================
    # Authenticate User
    # ==========================================

    @staticmethod
    def authenticate_user(
        db: Session,
        *,
        email: str,
        password: str,
    ) -> User | None:
        """
        Verify user credentials.

        Returns the user when credentials are valid.
        Returns None when authentication fails.
        """

        user = AuthService.get_user_by_email(
            db,
            email,
        )

        if not user:
            return None

        if not user.is_active:
            return None

        if not verify_password(
            password,
            user.password_hash,
        ):
            return None

        return user

    # ==========================================
    # Create Access Token
    # ==========================================

    @staticmethod
    def create_user_access_token(
        user: User,
    ) -> str:
        """
        Create a JWT access token for a user.
        """

        return create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
            }
        )

    # ==========================================
    # Password Recovery
    # ==========================================

    @staticmethod
    def create_password_reset_token(
        user: User,
    ) -> str:
        return create_access_token(
            {
                "sub": str(user.id),
                "purpose": "password_reset",
            },
            expires_delta=timedelta(
                minutes=(
                    settings.PASSWORD_RESET_EXPIRE_MINUTES
                ),
            ),
        )

    @staticmethod
    def reset_password(
        db: Session,
        token: str,
        password: str,
    ) -> User:
        try:
            payload = decode_access_token(token)
            user_id = int(payload["sub"])
        except (
            jwt.InvalidTokenError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                "Invalid or expired reset token."
            ) from error

        if payload.get("purpose") != "password_reset":
            raise ValueError(
                "Invalid or expired reset token."
            )

        user = db.get(User, user_id)

        if user is None or not user.is_active:
            raise ValueError(
                "Invalid or expired reset token."
            )

        user.password_hash = hash_password(password)
        db.commit()
        db.refresh(user)
        return user