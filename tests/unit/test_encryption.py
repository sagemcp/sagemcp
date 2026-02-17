"""Tests for field-level encryption (Phase 1)."""

import json
import os

import pytest

# Ensure test env vars are set before any sage_mcp imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

from sage_mcp.security.encryption import (
    encrypt_value,
    decrypt_value,
    is_encrypted,
    get_fernet,
    FERNET_PREFIX,
    _derive_key,
)
from sage_mcp.security.types import EncryptedText
from sage_mcp.security.encrypted_json import EncryptedJSON


class TestEncryptDecrypt:
    """Basic encrypt/decrypt roundtrip."""

    def test_roundtrip_simple_string(self):
        plaintext = "ghp_ABCDEFghijklmnop1234567890"
        encrypted = encrypt_value(plaintext)
        assert encrypted != plaintext
        assert is_encrypted(encrypted)
        assert decrypt_value(encrypted) == plaintext

    def test_roundtrip_empty_string(self):
        encrypted = encrypt_value("")
        assert is_encrypted(encrypted)
        assert decrypt_value(encrypted) == ""

    def test_roundtrip_unicode(self):
        plaintext = "secret_key_\u00e9\u00e8\u00ea"
        encrypted = encrypt_value(plaintext)
        assert decrypt_value(encrypted) == plaintext

    def test_roundtrip_long_value(self):
        plaintext = "x" * 10_000
        encrypted = encrypt_value(plaintext)
        assert decrypt_value(encrypted) == plaintext

    def test_different_encryptions_produce_different_tokens(self):
        """Fernet uses a random IV, so same plaintext -> different ciphertext."""
        a = encrypt_value("same")
        b = encrypt_value("same")
        assert a != b
        assert decrypt_value(a) == decrypt_value(b) == "same"


class TestIsEncrypted:
    """Fernet prefix detection."""

    def test_encrypted_value(self):
        encrypted = encrypt_value("test")
        assert is_encrypted(encrypted)

    def test_plaintext_value(self):
        assert not is_encrypted("just-plaintext")

    def test_none_value(self):
        assert not is_encrypted(None)

    def test_empty_string(self):
        assert not is_encrypted("")

    def test_prefix_constant(self):
        assert FERNET_PREFIX == "gAAAAA"


class TestLegacyPlaintextFallback:
    """decrypt_value must return raw value when it's not a Fernet token."""

    def test_plaintext_passthrough(self):
        raw = "ghp_1234567890abcdef"
        assert decrypt_value(raw) == raw

    def test_none_passthrough(self):
        assert decrypt_value(None) is None

    def test_empty_passthrough(self):
        assert decrypt_value("") == ""

    def test_json_plaintext_passthrough(self):
        raw = '{"api_key": "sk-test-123"}'
        assert decrypt_value(raw) == raw


class TestKeyDerivation:
    """PBKDF2 key derivation from SECRET_KEY."""

    def test_deterministic(self):
        key_a = _derive_key("my-secret")
        key_b = _derive_key("my-secret")
        assert key_a == key_b

    def test_different_secrets_different_keys(self):
        key_a = _derive_key("secret-one")
        key_b = _derive_key("secret-two")
        assert key_a != key_b

    def test_get_fernet_returns_cached_instance(self):
        f1 = get_fernet()
        f2 = get_fernet()
        assert f1 is f2


class TestEncryptedTextTypeDecorator:
    """EncryptedText SQLAlchemy TypeDecorator."""

    def setup_method(self):
        self.type_decorator = EncryptedText()

    def test_bind_param_encrypts(self):
        result = self.type_decorator.process_bind_param("secret", None)
        assert result is not None
        assert is_encrypted(result)

    def test_bind_param_none(self):
        result = self.type_decorator.process_bind_param(None, None)
        assert result is None

    def test_result_value_decrypts(self):
        encrypted = encrypt_value("secret")
        result = self.type_decorator.process_result_value(encrypted, None)
        assert result == "secret"

    def test_result_value_none(self):
        result = self.type_decorator.process_result_value(None, None)
        assert result is None

    def test_result_value_legacy_plaintext(self):
        result = self.type_decorator.process_result_value("legacy-plaintext", None)
        assert result == "legacy-plaintext"


class TestEncryptedJSONTypeDecorator:
    """EncryptedJSON SQLAlchemy TypeDecorator."""

    def setup_method(self):
        self.type_decorator = EncryptedJSON()

    def test_bind_param_encrypts_dict(self):
        data = {"api_key": "sk-test", "nested": {"deep": True}}
        result = self.type_decorator.process_bind_param(data, None)
        assert result is not None
        assert is_encrypted(result)

    def test_bind_param_none(self):
        result = self.type_decorator.process_bind_param(None, None)
        assert result is None

    def test_result_value_decrypts_to_dict(self):
        data = {"api_key": "sk-test", "list": [1, 2, 3]}
        encrypted = encrypt_value(json.dumps(data))
        result = self.type_decorator.process_result_value(encrypted, None)
        assert result == data

    def test_result_value_none(self):
        result = self.type_decorator.process_result_value(None, None)
        assert result is None

    def test_result_value_legacy_plaintext_json(self):
        """Legacy plaintext JSON string should be parsed correctly."""
        data = {"old_key": "old_value"}
        raw_json = json.dumps(data)
        result = self.type_decorator.process_result_value(raw_json, None)
        assert result == data

    def test_roundtrip(self):
        data = {"token": "ghp_abc123", "env": {"DB_URL": "postgres://..."}}
        encrypted = self.type_decorator.process_bind_param(data, None)
        decrypted = self.type_decorator.process_result_value(encrypted, None)
        assert decrypted == data

    def test_corrupt_ciphertext_returns_none(self):
        """EncryptedJSON.process_result_value returns None on corrupt/non-JSON ciphertext."""
        # "not-valid-json" is not a Fernet token, so decrypt_value returns it as-is.
        # json.loads("not-valid-json") raises JSONDecodeError -> returns None.
        result = self.type_decorator.process_result_value("not-valid-json", None)
        assert result is None

    def test_legacy_plaintext_json_parses_correctly(self):
        """Legacy unencrypted JSON strings should still parse correctly."""
        raw_json = '{"legacy": true, "count": 42}'
        result = self.type_decorator.process_result_value(raw_json, None)
        assert result == {"legacy": True, "count": 42}


class TestDecryptValueEdgeCases:
    """Edge cases for decrypt_value error propagation."""

    def test_non_invalid_token_exceptions_propagate(self):
        """Exceptions other than InvalidToken should propagate, not be swallowed."""
        from unittest.mock import patch, MagicMock
        from cryptography.fernet import Fernet

        # Patch get_fernet to return a Fernet instance whose .decrypt raises TypeError
        mock_fernet = MagicMock(spec=Fernet)
        mock_fernet.decrypt.side_effect = TypeError("unexpected error")

        with patch("sage_mcp.security.encryption.get_fernet", return_value=mock_fernet):
            with pytest.raises(TypeError, match="unexpected error"):
                decrypt_value("some-ciphertext")
