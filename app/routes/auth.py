import smtplib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.service import AuthService
from app.database.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
)
from app.services.email_service import EmailService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ==========================================
# Register
# ==========================================

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new user and return an access token.
    """

    # ------------------------------------------
    # Verify passwords match
    # ------------------------------------------

    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    # ------------------------------------------
    # Create user
    # ------------------------------------------

    try:
        user = AuthService.register_user(
            db,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password=data.password,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    # ------------------------------------------
    # Create JWT
    # ------------------------------------------

    access_token = AuthService.create_user_access_token(
        user
    )

    # ------------------------------------------
    # Return response
    # ------------------------------------------

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ==========================================
# Login
# ==========================================

@router.post(
    "/login",
    response_model=AuthResponse,
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate an existing user and return
    an access token.
    """

    # ------------------------------------------
    # Authenticate user
    # ------------------------------------------

    user = AuthService.authenticate_user(
        db,
        email=data.email,
        password=data.password,
    )

    # ------------------------------------------
    # Invalid credentials
    # ------------------------------------------

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # ------------------------------------------
    # Create JWT
    # ------------------------------------------

    access_token = AuthService.create_user_access_token(
        user
    )

    # ------------------------------------------
    # Return response
    # ------------------------------------------

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ==========================================
# Current User
# ==========================================

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Return the currently authenticated user's profile.
    """

    return UserResponse.model_validate(current_user)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
)
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    user = AuthService.get_user_by_email(
        db,
        str(data.email),
    )

    if user is not None and user.is_active:
        token = AuthService.create_password_reset_token(
            user
        )

        try:
            EmailService.send_password_reset_email(
                user.email,
                token,
            )
        except (OSError, RuntimeError, smtplib.SMTPException) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to send password reset email.",
            ) from error

    return MessageResponse(
        message=(
            "If an active account exists for that email, "
            "a password reset link has been sent."
        )
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
)
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    try:
        AuthService.reset_password(
            db,
            data.token,
            data.password,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return MessageResponse(
        message="Password reset successfully."
    )