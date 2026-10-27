"""AES-256-GCM: the padlock (TDR section 8).

Every call to encrypt() draws a new random 12-byte nonce. The ciphertext returned by AESGCM
already ends with the 16-byte authentication tag. The AAD binds a ciphertext to its place in
the database: copying it into another row makes decryption fail.
"""

import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_SIZE = 12
KEY_SIZE = 32


class DecryptionError(Exception):
    pass


def new_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def encrypt(key: bytes, plaintext: bytes, aad: str) -> tuple[bytes, bytes]:
    nonce = os.urandom(NONCE_SIZE)
    return AESGCM(key).encrypt(nonce, plaintext, aad.encode()), nonce


def decrypt(key: bytes, ciphertext: bytes, nonce: bytes, aad: str) -> bytes:
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, aad.encode())
    except InvalidTag as exc:
        # Wrong key, modified ciphertext or ciphertext moved to another row.
        raise DecryptionError(aad.split(":")[0]) from exc


def encrypt_text(key: bytes, text: str, aad: str) -> tuple[bytes, bytes]:
    return encrypt(key, text.encode("utf-8"), aad)


def decrypt_text(key: bytes, ciphertext: bytes, nonce: bytes, aad: str) -> str:
    return decrypt(key, ciphertext, nonce, aad).decode("utf-8")
