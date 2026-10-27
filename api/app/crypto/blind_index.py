"""Blind index: find a row by e-mail or phone without storing the value in clear (HMAC-SHA256)."""

import base64
import hashlib
import hmac
import re

from app.config import get_settings


def _key() -> bytes:
    return base64.b64decode(get_settings().blind_index_key)


def email_index(email: str) -> bytes:
    return hmac.new(_key(), email.strip().lower().encode(), hashlib.sha256).digest()


def phone_index(phone: str) -> bytes:
    digits = re.sub(r"\D", "", phone)
    return hmac.new(_key(), digits.encode(), hashlib.sha256).digest()
