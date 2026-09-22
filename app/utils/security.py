from datetime import datetime, timedelta, timezone
from typing import Any, Final

import jwt
from pwdlib import PasswordHash

from app.core.config import settings


# ==========================================
# Token Types
# ==========================================

class TokenType:
    """
    Permitted values for the JWT "type" claim.

    Every token is issued for exactly one purpose and is
    only accepted by the code path that owns that purpose.
    Without this, a password reset token - which travels
    through email, browser history and Referer headers -
    is structurally identical to a login token and can be
    presented as one.
    """

    ACCESS: Final = "access"

    PASSWORD_RESET: Final = "password_reset"


# ==========================================
# Password Hashing
# ==========================================

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using Argon2.
    """

    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a plain-text password against a stored
    Argon2 password hash.
    """

    return password_hash.verify(
        plain_password,
        hashed_password,
    )


# ==========================================
# JWT Authentication
# ==========================================

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    token_type: str = TokenType.ACCESS,
) -> str:
    """
    Create a signed JWT.

    If expires_delta is not provided, the expiration
    configured in the application settings is used.

    Two claims are always added:

    - "type": what the token may be used for. Defaults to
      an access token, so ordinary callers are unaffected.
    - "iat": when the token was issued, truncated to whole
      seconds. This lets tokens minted before a password
      change be rejected afterwards.
    """

    to_encode = data.copy()

    # JWT timestamps have one-second resolution. Truncating
    # here keeps "iat" exact rather than silently floored,
    # so it can be compared against User.password_changed_at
    # without an off-by-a-fraction-of-a-second error.
    issued_at = datetime.now(timezone.utc).replace(
        microsecond=0,
    )

    if expires_delta is not None:
        expire = issued_at + expires_delta
    else:
        expire = issued_at + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update(
        {
            "exp": expire,
            "iat": issued_at,
            "type": token_type,
        }
    )

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(
    token: str,
) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Raises:
        jwt.InvalidTokenError:
            If the token is invalid, expired, malformed,
            or has an invalid signature.
    """

    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


# ==========================================
# Token Freshness
# ==========================================

def utc_now_seconds() -> datetime:
    """
    Current UTC time truncated to whole seconds.

    Matches the resolution of the JWT "iat" claim so the
    two can be compared without sub-second skew.
    """

    return datetime.now(timezone.utc).replace(
        microsecond=0,
    )


def token_predates_password_change(
    payload: dict[str, Any],
    password_changed_at: datetime | None,
    *,
    inclusive: bool = False,
) -> bool:
    """
    Report whether a token was issued before the user's
    password last changed.

    Access tokens use the default strict comparison, so
    signing in during the same second as a reset is not
    rejected.

    Password reset tokens pass inclusive=True, which also
    rejects a token issued in the same second as the reset
    it just performed. That closes the replay window
    completely without locking anyone out of a new session.
    """

    if password_changed_at is None:
        return False

    issued_at = payload.get("iat")

    if issued_at is None:
        # A token with no "iat" cannot be shown to post-date
        # the password change, so it is refused. This only
        # affects tokens minted before this claim existed.
        return True

    if password_changed_at.tzinfo is None:
        # SQLite returns naive datetimes. Stored values are UTC.
        password_changed_at = password_changed_at.replace(
            tzinfo=timezone.utc,
        )

    try:
        issued = datetime.fromtimestamp(
            int(issued_at),
            tz=timezone.utc,
        )
    except (TypeError, ValueError, OSError, OverflowError):
        return True

    if inclusive:
        return issued <= password_changed_at

    return issued < password_changed_at