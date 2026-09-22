import time
import uuid
from datetime import timedelta

import jwt

from app.core.config import settings
from app.models.user import User
from app.utils.security import TokenType, utc_now_seconds


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


def test_password_recovery_flow(
    client,
    monkeypatch,
):
    email = f"reset_{uuid.uuid4().hex}@example.com"
    original_password = "OriginalPassword123!"
    new_password = "UpdatedPassword123!"
    register_response = client.post(
        "/auth/register",
        json={
            "first_name": "Reset",
            "last_name": "User",
            "email": email,
            "password": original_password,
            "confirm_password": original_password,
        },
    )
    assert register_response.status_code == 201

    sent: dict[str, str] = {}

    def capture_email(
        recipient: str,
        token: str,
    ):
        sent["recipient"] = recipient
        sent["token"] = token

    monkeypatch.setattr(
        (
            "app.routes.auth.EmailService."
            "send_password_reset_email"
        ),
        capture_email,
    )

    forgot_response = client.post(
        "/auth/forgot-password",
        json={"email": email},
    )

    assert forgot_response.status_code == 200
    assert sent["recipient"] == email

    reset_response = client.post(
        "/auth/reset-password",
        json={
            "token": sent["token"],
            "password": new_password,
            "confirm_password": new_password,
        },
    )
    assert reset_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": new_password,
        },
    )
    assert login_response.status_code == 200


def test_forgot_password_does_not_reveal_unknown_email(
    client,
):
    response = client.post(
        "/auth/forgot-password",
        json={
            "email": (
                f"missing_{uuid.uuid4().hex}@example.com"
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["message"].startswith(
        "If an active account exists"
    )


# ==========================================
# Token Scope And Session Revocation
# ==========================================


def _register(client, password="TokenScope123!"):
    """
    Register a fresh user and return its email and the
    access token issued at registration.
    """

    email = f"scope_{uuid.uuid4().hex}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "first_name": "Scope",
            "last_name": "User",
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )

    assert response.status_code == 201

    return email, response.json()["access_token"]


def _request_reset_token(client, monkeypatch, email):
    """
    Trigger a password reset and return the token that
    would have been emailed.
    """

    sent: dict[str, str] = {}

    def capture_email(recipient: str, token: str):
        sent["recipient"] = recipient
        sent["token"] = token

    monkeypatch.setattr(
        (
            "app.routes.auth.EmailService."
            "send_password_reset_email"
        ),
        capture_email,
    )

    response = client.post(
        "/auth/forgot-password",
        json={"email": email},
    )

    assert response.status_code == 200
    assert sent["recipient"] == email

    return sent["token"]


def test_password_reset_token_cannot_authenticate(
    client,
    monkeypatch,
):
    """
    A reset token travels through email, browser history
    and Referer headers. It must not double as a session.
    """

    email, _ = _register(client)

    reset_token = _request_reset_token(
        client,
        monkeypatch,
        email,
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {reset_token}",
        },
    )

    assert response.status_code == 401
    assert (
        response.json()["detail"]
        == "Invalid authentication token."
    )


def test_access_token_cannot_reset_password(
    client,
):
    """
    The inverse: a stolen session must not be usable to
    take ownership of the account by setting a password.
    """

    _, access_token = _register(client)

    response = client.post(
        "/auth/reset-password",
        json={
            "token": access_token,
            "password": "HijackedPassword123!",
            "confirm_password": "HijackedPassword123!",
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Invalid or expired reset token."
    )


def test_password_reset_token_cannot_be_reused(
    client,
    monkeypatch,
):
    """
    A reset link is single use. Anyone who later reads the
    email must not be able to replay it.
    """

    email, _ = _register(client)

    reset_token = _request_reset_token(
        client,
        monkeypatch,
        email,
    )

    first = client.post(
        "/auth/reset-password",
        json={
            "token": reset_token,
            "password": "FirstReset123!",
            "confirm_password": "FirstReset123!",
        },
    )

    assert first.status_code == 200

    second = client.post(
        "/auth/reset-password",
        json={
            "token": reset_token,
            "password": "ReplayedReset123!",
            "confirm_password": "ReplayedReset123!",
        },
    )

    assert second.status_code == 400
    assert (
        second.json()["detail"]
        == "Invalid or expired reset token."
    )

    # The replay must not have taken effect.
    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "ReplayedReset123!",
        },
    )

    assert login.status_code == 401


def test_password_change_revokes_existing_sessions(
    client,
    monkeypatch,
):
    """
    Resetting a password must end every session that was
    already open, otherwise a user whose account has been
    compromised cannot take it back.
    """

    email, access_token = _register(client)

    before = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert before.status_code == 200

    # The JWT "iat" claim has one-second resolution, so the
    # reset has to land in a later whole second than the
    # token for the comparison to be meaningful.
    time.sleep(1.05)

    reset_token = _request_reset_token(
        client,
        monkeypatch,
        email,
    )

    reset = client.post(
        "/auth/reset-password",
        json={
            "token": reset_token,
            "password": "RevokedSession123!",
            "confirm_password": "RevokedSession123!",
        },
    )

    assert reset.status_code == 200

    after = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert after.status_code == 401
    assert "sign in again" in after.json()["detail"]


def test_new_session_after_reset_is_accepted(
    client,
    monkeypatch,
):
    """
    Revocation must not lock the legitimate user out: a
    token minted in the same second as the reset is still
    a valid session.
    """

    email, _ = _register(client)

    reset_token = _request_reset_token(
        client,
        monkeypatch,
        email,
    )

    reset = client.post(
        "/auth/reset-password",
        json={
            "token": reset_token,
            "password": "FreshSession123!",
            "confirm_password": "FreshSession123!",
        },
    )

    assert reset.status_code == 200

    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "FreshSession123!",
        },
    )

    assert login.status_code == 200

    me = client.get(
        "/auth/me",
        headers={
            "Authorization": (
                f"Bearer {login.json()['access_token']}"
            ),
        },
    )

    assert me.status_code == 200
    assert me.json()["email"] == email


def test_token_without_iat_claim_is_rejected_after_reset(
    client,
    db,
):
    """
    Tokens minted before the "iat" claim existed cannot be
    shown to post-date a password change, so they fail
    closed rather than being trusted.
    """

    email, _ = _register(client)

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    assert user is not None

    user.password_changed_at = utc_now_seconds()
    db.commit()

    legacy_token = jwt.encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "type": TokenType.ACCESS,
            "exp": utc_now_seconds() + timedelta(minutes=30),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {legacy_token}",
        },
    )

    assert response.status_code == 401


# ==========================================
# Account Enumeration
# ==========================================


def test_forgot_password_hides_email_delivery_failure(
    client,
    monkeypatch,
):
    """
    A delivery failure must not distinguish a registered
    address from an unregistered one. Both answer 200 with
    an identical body.
    """

    email, _ = _register(client)

    def fail_to_send(recipient: str, token: str):
        raise RuntimeError(
            "Email delivery is not configured."
        )

    monkeypatch.setattr(
        (
            "app.routes.auth.EmailService."
            "send_password_reset_email"
        ),
        fail_to_send,
    )

    known = client.post(
        "/auth/forgot-password",
        json={"email": email},
    )

    unknown = client.post(
        "/auth/forgot-password",
        json={
            "email": (
                f"missing_{uuid.uuid4().hex}@example.com"
            )
        },
    )

    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json() == unknown.json()