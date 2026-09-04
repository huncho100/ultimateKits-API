import uuid

from fastapi.testclient import TestClient

from app.main import app


# ==========================================
# Test Client
# ==========================================

client = TestClient(app)


# ==========================================
# Test Data
# ==========================================

TEST_EMAIL = (
    f"test_{uuid.uuid4().hex[:8]}@example.com"
)

TEST_PASSWORD = "TestPassword123!"


# ==========================================
# Register
# ==========================================

def test_register_user():
    response = client.post(
        "/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data

    assert data["user"]["email"] == TEST_EMAIL
    assert data["user"]["first_name"] == "Test"
    assert data["user"]["last_name"] == "User"

    print("✓ Register test passed")


# ==========================================
# Login
# ==========================================

def test_login_user():
    response = client.post(
        "/auth/login",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"

    assert "user" in data
    assert data["user"]["email"] == TEST_EMAIL

    print("✓ Login test passed")


# ==========================================
# Invalid Login
# ==========================================

def test_invalid_login():
    response = client.post(
        "/auth/login",
        json={
            "email": TEST_EMAIL,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401

    data = response.json()

    assert data["detail"] == "Invalid email or password."

    print("✓ Invalid login test passed")


# ==========================================
# Get Current User
# ==========================================

def test_get_current_user():
    login_response = client.post(
        "/auth/login",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == TEST_EMAIL
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"

    print("✓ Current user test passed")


# ==========================================
# No Authentication Token
# ==========================================

def test_current_user_without_token():
    response = client.get(
        "/auth/me"
    )

    assert response.status_code == 401

    print("✓ Missing token test passed")


# ==========================================
# Invalid Authentication Token
# ==========================================

def test_current_user_with_invalid_token():
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401

    data = response.json()

    assert data["detail"] == "Invalid or expired token."

    print("✓ Invalid token test passed")