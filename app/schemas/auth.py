from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ==========================================
# Register
# ==========================================


class RegisterRequest(BaseModel):
    first_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    last_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )

    confirm_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


# ==========================================
# Login
# ==========================================


class LoginRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


# ==========================================
# User Response
# ==========================================


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: str
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# ==========================================
# Authentication Response
# ==========================================


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ==========================================
# Forgot Password
# ==========================================


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


# ==========================================
# Reset Password
# ==========================================


class ResetPasswordRequest(BaseModel):
    token: str

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )

    confirm_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


# ==========================================
# Message Response
# ==========================================


class MessageResponse(BaseModel):
    message: str