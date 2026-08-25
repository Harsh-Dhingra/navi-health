"""Field-level encryption for PHI columns.

Disk/volume encryption from the hosting provider protects data at rest from
physical media theft, but not from a database dump or misconfigured backup.
Columns holding PHI (member IDs, clinical notes, medication details, etc.)
are additionally encrypted at the application layer with Fernet (AES-128-CBC
+ HMAC), so the plaintext never reaches disk.

The encryption key must come from a secrets manager in production (Render's
environment groups, or a dedicated KMS) — never commit it. Losing the key
means losing access to encrypted data; back it up in your secrets manager's
own backup mechanism, not in this repo.
"""

import json

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy import String, Text
from sqlalchemy.types import TypeDecorator

from app.core.config import get_settings


def _build_fernet() -> MultiFernet:
    settings = get_settings()
    keys = [k.strip() for k in settings.field_encryption_keys.split(",") if k.strip()]
    if not keys:
        raise RuntimeError(
            "FIELD_ENCRYPTION_KEYS is not set. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return MultiFernet([Fernet(k.encode()) for k in keys])


class EncryptedString(TypeDecorator):
    """A String column whose value is encrypted at rest with Fernet.

    Supports key rotation: pass multiple comma-separated keys in
    FIELD_ENCRYPTION_KEYS, newest first. New writes use the first key;
    reads try all of them, so old rows stay readable until re-encrypted.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return _build_fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return _build_fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Not encrypted (e.g. legacy row) or wrong key — surface plainly
            # rather than silently returning ciphertext as if it were data.
            raise ValueError("Unable to decrypt field — check FIELD_ENCRYPTION_KEYS") from None


class EncryptedText(EncryptedString):
    """Same as EncryptedString but backed by an unbounded Text column, for
    long free-text PHI (OCR'd document contents, clinical notes)."""

    impl = Text


class EncryptedJSON(TypeDecorator):
    """A JSON-serializable dict/list, encrypted at rest as an unbounded Text column."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return _build_fernet().encrypt(json.dumps(value).encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return json.loads(_build_fernet().decrypt(value.encode()).decode())
        except InvalidToken:
            raise ValueError("Unable to decrypt field — check FIELD_ENCRYPTION_KEYS") from None
