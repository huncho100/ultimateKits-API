import uuid


TEST_PASSWORD = "TestPassword123!"


def register_user(
    client,
    *,
    email: str | None = None,
):
    user_email = (
        email
        or f"test_{uuid.uuid4().hex[:8]}@example.com"
    )
    response = client.post(
        "/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": user_email,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
        },
    )
    return response, user_email


def test_register_user(client):
    response, email = register_user(client)

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email
    assert data["user"]["first_name"] == "Test"
    assert data["user"]["last_name"] == "User"


def test_login_user(client):
    _, email = register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email


def test_invalid_login(client):
    _, email = register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert (
        response.json()["detail"]
        == "Invalid email or password."
    )


def test_get_current_user(client):
    register_response, email = register_user(client)
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
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"


def test_current_user_without_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_current_user_with_invalid_token(client):
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401
    assert (
        response.json()["detail"]
        == "Invalid or expired token."
    )
