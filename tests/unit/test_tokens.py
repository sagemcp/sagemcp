"""Tests for JWT token creation and validation."""

import os
import uuid
from datetime import timedelta

import pytest
from jose import jwt, JWTError

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

from sage_mcp.security.tokens import (
    ALGORITHM,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from sage_mcp.config import get_settings


class TestCreateAccessToken:
    """Access token encoding and claims."""

    def test_returns_string(self):
        token = create_access_token(
            user_id=str(uuid.uuid4()), email="a@b.com", roles={}
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_contains_expected_claims(self):
        uid = str(uuid.uuid4())
        roles = {"tenant-1": "tenant_admin", "tenant-2": "tenant_viewer"}
        token = create_access_token(user_id=uid, email="a@b.com", roles=roles)

        payload = decode_token(token)
        assert payload["sub"] == uid
        assert payload["email"] == "a@b.com"
        assert payload["roles"] == roles
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "exp" in payload

    def test_custom_expiry(self):
        token = create_access_token(
            user_id="u1",
            email="a@b.com",
            roles={},
            expires_delta=timedelta(minutes=5),
        )
        payload = decode_token(token)
        assert payload["exp"] - payload["iat"] == 300  # 5 minutes

    def test_default_expiry_matches_settings(self):
        settings = get_settings()
        token = create_access_token(user_id="u1", email="a@b.com", roles={})
        payload = decode_token(token)
        expected_seconds = settings.access_token_expire_minutes * 60
        assert payload["exp"] - payload["iat"] == expected_seconds

    def test_empty_roles(self):
        token = create_access_token(user_id="u1", email="a@b.com", roles={})
        payload = decode_token(token)
        assert payload["roles"] == {}


class TestCreateRefreshToken:
    """Refresh token encoding and claims."""

    def test_returns_string(self):
        token = create_refresh_token(user_id=str(uuid.uuid4()))
        assert isinstance(token, str)

    def test_contains_expected_claims(self):
        uid = str(uuid.uuid4())
        token = create_refresh_token(user_id=uid)

        payload = decode_token(token)
        assert payload["sub"] == uid
        assert payload["type"] == "refresh"
        assert "iat" in payload
        assert "exp" in payload
        assert "email" not in payload
        assert "roles" not in payload

    def test_custom_expiry(self):
        token = create_refresh_token(
            user_id="u1", expires_delta=timedelta(days=1)
        )
        payload = decode_token(token)
        assert payload["exp"] - payload["iat"] == 86400  # 1 day

    def test_default_expiry_matches_settings(self):
        settings = get_settings()
        token = create_refresh_token(user_id="u1")
        payload = decode_token(token)
        expected_seconds = settings.refresh_token_expire_days * 86400
        assert payload["exp"] - payload["iat"] == expected_seconds


class TestDecodeToken:
    """Token decoding, validation, and error handling."""

    def test_valid_access_token(self):
        token = create_access_token(user_id="u1", email="a@b.com", roles={})
        payload = decode_token(token)
        assert payload["sub"] == "u1"

    def test_valid_refresh_token(self):
        token = create_refresh_token(user_id="u1")
        payload = decode_token(token)
        assert payload["sub"] == "u1"

    def test_expired_token_raises(self):
        token = create_access_token(
            user_id="u1",
            email="a@b.com",
            roles={},
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(JWTError):
            decode_token(token)

    def test_invalid_signature_raises(self):
        settings = get_settings()
        payload = {"sub": "u1", "type": "access"}
        token = jwt.encode(payload, "wrong-secret-key", algorithm=ALGORITHM)
        with pytest.raises(JWTError):
            decode_token(token)

    def test_malformed_token_raises(self):
        with pytest.raises(JWTError):
            decode_token("not.a.valid.jwt")

    def test_empty_token_raises(self):
        with pytest.raises(JWTError):
            decode_token("")

    def test_tampered_payload_raises(self):
        """Modify the payload segment — signature check should fail."""
        token = create_access_token(user_id="u1", email="a@b.com", roles={})
        parts = token.split(".")
        # Flip a character in the payload
        payload_bytes = bytearray(parts[1].encode())
        payload_bytes[0] = (payload_bytes[0] + 1) % 128
        parts[1] = payload_bytes.decode()
        tampered = ".".join(parts)
        with pytest.raises(JWTError):
            decode_token(tampered)


class TestTokenTypeDiscrimination:
    """Ensure access vs refresh tokens are distinguishable by 'type' claim."""

    def test_access_type(self):
        token = create_access_token(user_id="u1", email="a@b.com", roles={})
        assert decode_token(token)["type"] == "access"

    def test_refresh_type(self):
        token = create_refresh_token(user_id="u1")
        assert decode_token(token)["type"] == "refresh"

    def test_different_tokens_for_same_user(self):
        access = create_access_token(user_id="u1", email="a@b.com", roles={})
        refresh = create_refresh_token(user_id="u1")
        assert access != refresh
