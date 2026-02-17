"""SQLAlchemy TypeDecorator for transparent field-level encryption of Text columns."""

from typing import Optional

from sqlalchemy import Text, TypeDecorator

from .encryption import encrypt_value, decrypt_value


class EncryptedText(TypeDecorator):
    """Transparently encrypts on write and decrypts on read.

    - ``process_bind_param``: encrypts plaintext before INSERT/UPDATE.
    - ``process_result_value``: decrypts ciphertext after SELECT.
    - Legacy plaintext values are returned as-is (``decrypt_value`` falls back).
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        return encrypt_value(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        return decrypt_value(value)
