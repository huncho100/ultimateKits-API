import uuid

from app.models.user import User


# ==========================================
# Registration
# ==========================================


def test_register_user_success(client):
    email = f"register_{uuid.uuid4().hex}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": email,
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email
    assert data["user"]["first_name"] == "Test"
    assert data["user"]["last_name"] == "User"
    assert data["user"]["role"] == "customer"
    assert data["user"]["is_active"] is True


def test_register_user_duplicate_email(client):
    email = f"duplicate_{uuid.uuid4().hex}@example.com"

    payload = {
        "first_name": "Duplicate",
        "last_name": "User",
        "email": email,
        "password": "TestPassword123!",
        "confirm_password": "TestPassword123!",
    }

    first_response = client.post(
        "/auth/register",
        json=payload,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/auth/register",
        json=payload,
    )

    assert second_response.status_code == 409
    assert "already exists" in second_response.json()["detail"]


def test_register_user_password_mismatch(client):
    email = f"mismatch_{uuid.uuid4().hex}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": email,
            "password": "TestPassword123!",
            "confirm_password": "DifferentPassword123!",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Passwords do not match."


def test_register_user_invalid_email(client):
    response = client.post(
        "/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": "not-an-email",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
        },
    )

    assert response.status_code == 422


def test_register_user_short_password(client):
    email = f"shortpass_{uuid.uuid4().hex}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": email,
            "password": "short",
            "confirm_password": "short",
        },
    )

    assert response.status_code == 422


# ==========================================
# Login
# ==========================================


def test_login_success(client):
    email = f"login_{uuid.uuid4().hex}@example.com"
    password = "LoginPassword123!"

    register_response = client.post(
        "/auth/register",
        json={
            "first_name": "Login",
            "last_name": "User",
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )

    assert register_response.status_code == 201

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email


def test_login_wrong_password(client):
    email = f"wrongpass_{uuid.uuid4().hex}@example.com"
    password = "CorrectPassword123!"

    register_response = client.post(
        "/auth/register",
        json={
            "first_name": "Wrong",
            "last_name": "Password",
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )

    assert register_response.status_code == 201

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_nonexistent_user(client):
    response = client.post(
        "/auth/login",
        json={
            "email": f"missing_{uuid.uuid4().hex}@example.com",
            "password": "SomePassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


# ==========================================
# /auth/me
# ==========================================


def test_get_current_user_success(client):
    email = f"me_{uuid.uuid4().hex}@example.com"
    password = "MePassword123!"

    register_response = client.post(
        "/auth/register",
        json={
            "first_name": "Current",
            "last_name": "User",
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )

    assert register_response.status_code == 201

    token = register_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == email
    assert data["first_name"] == "Current"
    assert data["last_name"] == "User"


def test_get_current_user_without_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_get_current_user_invalid_token(client):
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer invalid.token.here",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token."


# ==========================================
# Inactive User
# ==========================================


def test_inactive_user_cannot_login(client, db):
    email = f"inactive_{uuid.uuid4().hex}@example.com"
    password = "InactivePassword123!"

    register_response = client.post(
        "/auth/register",
        json={
            "first_name": "Inactive",
            "last_name": "User",
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )

    assert register_response.status_code == 201

    created_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    assert created_user is not None

    created_user.is_active = False
    db.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."