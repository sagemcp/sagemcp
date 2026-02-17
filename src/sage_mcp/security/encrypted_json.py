"""SQLAlchemy TypeDecorator for transparent encryption of JSON columns.

Serialises a dict to JSON, encrypts the entire blob, and stores as Text.
On read, decrypts and deserialises back to a dict.
"""

import json
from typing import Any, Dict, Optional

from sqlalchemy import Text, TypeDecorator

from .encryption import encrypt_value, decrypt_value


class EncryptedJSON(TypeDecorator):
    """Encrypt-on-write / decrypt-on-read for JSON dict columns.

    Storage format: Fernet(json.dumps(value)).
    Legacy plaintext JSON strings are handled gracefully by ``decrypt_value``.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[Dict[str, Any]], dialect) -> Optional[str]:
        if value is None:
            return None
        json_str = json.dumps(value)
        return encrypt_value(json_str)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        decrypted = decrypt_value(value)
        return json.loads(decrypted)
