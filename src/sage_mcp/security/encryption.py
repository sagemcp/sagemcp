"""Fernet encryption utilities for field-level encryption at rest.

Key is derived from SECRET_KEY via PBKDF2 (480K iterations) and cached per-process.
All encrypted values are Fernet tokens (base64, prefixed with ``gAAAAB``).
"""

import base64
import hashlib
import logging
import os
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

logger = logging.getLogger(__name__)

# Stable salt so the same SECRET_KEY always derives the same Fernet key.
# Changing this invalidates all encrypted data — treat it like part of the key.
_KDF_SALT = b"sagemcp-field-encryption-v1"
_KDF_ITERATIONS = 480_000

# Fernet token prefix (base64-encoded version byte 0x80 = "gA")
FERNET_PREFIX = "gAAAAA"


def _derive_key(secret: str) -> bytes:
    """Derive a 32-byte Fernet key from *secret* using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_KDF_SALT,
        iterations=_KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode("utf-8")))


# NOTE: lru_cache(maxsize=1) means key rotation requires a process restart
# to pick up a new SECRET_KEY value.
@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    """Return a process-cached Fernet instance keyed from SECRET_KEY."""
    from ..config import get_settings

    settings = get_settings()
    key = _derive_key(settings.secret_key)
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt *plaintext* and return the Fernet token as a UTF-8 string."""
    f = get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt *ciphertext*. If it's not a valid Fernet token, return as-is (legacy plaintext fallback)."""
    if not ciphertext:
        return ciphertext
    f = get_fernet()
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Legacy plaintext — return raw value so existing data keeps working.
        logger.debug("decrypt_value: value is not a valid Fernet token, returning as plaintext")
        return ciphertext


def is_encrypted(value: Optional[str]) -> bool:
    """Check whether *value* looks like a Fernet token."""
    if not value:
        return False
    return value.startswith(FERNET_PREFIX)
