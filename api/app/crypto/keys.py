"""The keyring: one DEK per user, wrapped by the KEK (TDR section 8).

The KEK never lives in the database. Each version is read from an environment variable
KEK_V<version> (32 random bytes, base64). The table key_encryption_keys only says which
version is ACTIVE. Moving the KEK to a secrets vault (M1) means replacing EnvKekProvider.
"""

import base64
import os
import re
import uuid
from functools import lru_cache

from dotenv import dotenv_values
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crypto.envelope import KEY_SIZE, decrypt, encrypt, new_key
from app.errors import AppError
from app.models import KekStatus, KeyEncryptionKey, User, UserKey, UserKeyStatus


class EnvKekProvider:
    def __init__(self) -> None:
        values = {**dotenv_values(".env"), **os.environ}
        self._keys: dict[int, bytes] = {}
        for name, value in values.items():
            match = re.fullmatch(r"KEK_V(\d+)", name)
            if match and value:
                key = base64.b64decode(value)
                if len(key) != KEY_SIZE:
                    raise RuntimeError(f"{name} must be 32 bytes encoded in base64")
                self._keys[int(match.group(1))] = key

    def versions(self) -> list[int]:
        return sorted(self._keys)

    def get(self, version: int) -> bytes:
        if version not in self._keys:
            raise AppError(500, "KEK_NOT_LOADED", f"KEK version {version} is not loaded.")
        return self._keys[version]


@lru_cache
def get_kek_provider() -> EnvKekProvider:
    return EnvKekProvider()


def active_kek(db: Session) -> KeyEncryptionKey:
    kek = db.scalar(select(KeyEncryptionKey).where(KeyEncryptionKey.status == KekStatus.ACTIVE))
    if kek is None:
        raise AppError(500, "KEK_NOT_CONFIGURED", "No active KEK version.")
    return kek


def _wrap_aad(user_id: uuid.UUID, version: int) -> str:
    return f"user_keys:{user_id}:kek:{version}"


def wrap_dek(dek: bytes, user_id: uuid.UUID, kek: KeyEncryptionKey) -> tuple[bytes, bytes]:
    return encrypt(get_kek_provider().get(kek.version), dek, _wrap_aad(user_id, kek.version))


def unwrap_dek(user_key: UserKey, kek: KeyEncryptionKey) -> bytes:
    return decrypt(get_kek_provider().get(kek.version), user_key.wrapped_dek, user_key.wrapped_dek_nonce, _wrap_aad(user_key.user_id, kek.version))


def new_user_dek(db: Session, user_id: uuid.UUID) -> bytes:
    """Generate the DEK of a new user; store_user_key() saves it once the user row exists."""
    dek = new_key()
    _cache(db)[user_id] = dek
    return dek


def store_user_key(db: Session, user_id: uuid.UUID, dek: bytes) -> None:
    """Save the DEK wrapped by the active KEK. Only the wrapped form reaches the database."""
    kek = active_kek(db)
    wrapped, nonce = wrap_dek(dek, user_id, kek)
    db.add(UserKey(user_id=user_id, kek_id=kek.id, wrapped_dek=wrapped, wrapped_dek_nonce=nonce, status=UserKeyStatus.ACTIVE))


def get_dek(db: Session, user_id: uuid.UUID) -> bytes:
    """The DEK in clear, kept only in memory for the current request."""
    cache = _cache(db)
    if user_id not in cache:
        user_key = db.scalar(select(UserKey).where(UserKey.user_id == user_id))
        if user_key is None or user_key.status != UserKeyStatus.ACTIVE:
            raise AppError(500, "DEK_UNAVAILABLE", "The data key of this user is not available.")
        cache[user_id] = unwrap_dek(user_key, db.get(KeyEncryptionKey, user_key.kek_id))
    return cache[user_id]


def dek_for(db: Session, user: User) -> bytes:
    return get_dek(db, user.id)


def _cache(db: Session) -> dict:
    return db.info.setdefault("deks", {})


def rotate_kek(db: Session, batch_size: int = 500) -> dict:
    """Activate the newest loaded KEK version and re-wrap every DEK with it (F12).

    Messages are not touched: only the small wrapped DEKs are re-encrypted.
    """
    from app.security import now

    provider = get_kek_provider()
    old = active_kek(db)
    newest = max(provider.versions(), default=0)
    if newest <= old.version:
        raise AppError(409, "KEK_NOT_PROVISIONED", f"Add KEK_V{old.version + 1} to the environment and restart the API first.")

    old.status = KekStatus.RETIRED
    old.retired_at = now()
    db.flush()
    new = db.scalar(select(KeyEncryptionKey).where(KeyEncryptionKey.version == newest))
    if new is None:
        new = KeyEncryptionKey(version=newest, status=KekStatus.ACTIVE, activated_at=now())
        db.add(new)
    else:
        new.status = KekStatus.ACTIVE
        new.activated_at = now()
        new.retired_at = None
    db.flush()

    rewrapped = 0
    while True:
        batch = db.scalars(
            select(UserKey)
            .where(UserKey.kek_id != new.id, UserKey.status == UserKeyStatus.ACTIVE)
            .limit(batch_size)
            .with_for_update()
        ).all()
        if not batch:
            break
        for user_key in batch:
            dek = unwrap_dek(user_key, db.get(KeyEncryptionKey, user_key.kek_id))
            user_key.wrapped_dek, user_key.wrapped_dek_nonce = wrap_dek(dek, user_key.user_id, new)
            user_key.kek_id = new.id
            rewrapped += 1
        db.flush()
    return {"fromVersion": old.version, "toVersion": new.version, "rewrappedKeys": rewrapped}
