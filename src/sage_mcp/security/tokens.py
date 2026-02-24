"""JWT token creation and validation.

Uses python-jose for JWT encoding/decoding. Tokens are signed with the
application SECRET_KEY using HS256.

Two token types:
- **access**: Short-lived (default 30 min), carries user identity and roles.
- **refresh**: Longer-lived (default 7 days), used to obtain new access tokens.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt

from ..config import get_settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"


def create_access_token(
    user_id: str,
    email: str,
    roles: Dict[str, str],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed access token.

    Args:
        user_id: UUID string for the ``sub`` claim.
        email: User email included in payload.
        roles: Mapping of tenant_id (str) to role (str).
        expires_delta: Custom expiry. Falls back to config ``access_token_expire_minutes``.

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    payload: Dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "roles": roles,
        "type": "access",
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed refresh token.

    Args:
        user_id: UUID string for the ``sub`` claim.
        expires_delta: Custom expiry. Falls back to config ``refresh_token_expire_days``.

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(days=settings.refresh_token_expire_days)

    payload: Dict[str, Any] = {
        "sub": user_id,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token.

    Validates signature and expiry. Returns the full payload dict on success.

    Raises:
        JWTError: On invalid signature, expired token, or malformed JWT.
    """
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
