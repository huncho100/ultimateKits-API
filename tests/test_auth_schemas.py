from pydantic import ValidationError

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)


print("=" * 50)
print("AUTH SCHEMA TESTS")
print("=" * 50)


# ==========================================
# 1. Valid Registration
# ==========================================

print("\n1. Testing valid registration...")

try:
    data = RegisterRequest(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="Password123!",
        confirm_password="Password123!",
    )

    print("PASS")
    print(data)

except ValidationError as error:
    print("FAIL")
    print(error)


# ==========================================
# 2. Invalid Email
# ==========================================

print("\n2. Testing invalid email...")

try:
    RegisterRequest(
        first_name="John",
        last_name="Doe",
        email="not-an-email",
        password="Password123!",
        confirm_password="Password123!",
    )

    print("FAIL - Invalid email was accepted.")

except ValidationError:
    print("PASS - Invalid email was rejected.")


# ==========================================
# 3. Short Password
# ==========================================

print("\n3. Testing short password...")

try:
    RegisterRequest(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="123",
        confirm_password="123",
    )

    print("FAIL - Short password was accepted.")

except ValidationError:
    print("PASS - Short password was rejected.")


# ==========================================
# 4. Valid Login
# ==========================================

print("\n4. Testing valid login...")

try:
    data = LoginRequest(
        email="john@example.com",
        password="Password123!",
    )

    print("PASS")
    print(data)

except ValidationError as error:
    print("FAIL")
    print(error)


# ==========================================
# 5. Invalid Login Email
# ==========================================

print("\n5. Testing invalid login email...")

try:
    LoginRequest(
        email="invalid-email",
        password="Password123!",
    )

    print("FAIL - Invalid email was accepted.")

except ValidationError:
    print("PASS - Invalid email was rejected.")


# ==========================================
# 6. Forgot Password
# ==========================================

print("\n6. Testing forgot password schema...")

try:
    data = ForgotPasswordRequest(
        email="john@example.com"
    )

    print("PASS")
    print(data)

except ValidationError as error:
    print("FAIL")
    print(error)


# ==========================================
# 7. Reset Password
# ==========================================

print("\n7. Testing reset password schema...")

try:
    data = ResetPasswordRequest(
        token="test-reset-token",
        password="NewPassword123!",
        confirm_password="NewPassword123!",
    )

    print("PASS")
    print(data)

except ValidationError as error:
    print("FAIL")
    print(error)


print("\n" + "=" * 50)
print("SCHEMA TESTING COMPLETE")
print("=" * 50)