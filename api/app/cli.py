"""Command line tools.

    python -m app.cli create-admin --email admin@orienta.local --name "Admin Orienta"
    python -m app.cli mark-abandoned
    python -m app.cli purge-expired
    python -m app.cli generate-keys
    python -m app.cli keys-status
    python -m app.cli rotate-kek

Key operations are only available here, on the server: never from the web interface.
"""

import argparse
import base64
import getpass
import os
import secrets
from datetime import timedelta

from sqlalchemy import delete, update

from app.config import get_settings
from app.db import SessionLocal
from app.models import Conversation, ConversationStatus, EmailVerificationCode, RefreshToken, UserRole, UserStatus
from app.repository import create_user, find_user_by_email
from app.security import hash_password, now


def create_admin(email: str, name: str, password: str | None) -> None:
    password = password or getpass.getpass("Password (10 characters minimum): ")
    if len(password) < 10:
        raise SystemExit("The password must contain at least 10 characters.")
    with SessionLocal() as db:
        if find_user_by_email(db, email) is not None:
            raise SystemExit("An account already exists for this e-mail address.")
        user = create_user(db, role=UserRole.ADMIN, email=email, full_name=name, password_hash=hash_password(password))
        user.status = UserStatus.ACTIVE
        user.email_verified_at = now()
        db.commit()
        print(f"Admin created: {user.id}")


def mark_abandoned() -> None:
    limit = now() - timedelta(seconds=get_settings().conversations_abandon_after_seconds)
    with SessionLocal() as db:
        result = db.execute(
            update(Conversation)
            .where(Conversation.status == ConversationStatus.IN_PROGRESS, Conversation.last_message_at < limit)
            .values(status=ConversationStatus.ABANDONED)
        )
        db.commit()
        print(f"Conversations marked ABANDONED: {result.rowcount}")


def purge_expired() -> None:
    with SessionLocal() as db:
        codes = db.execute(delete(EmailVerificationCode).where(EmailVerificationCode.expires_at < now() - timedelta(days=1)))
        tokens = db.execute(delete(RefreshToken).where(RefreshToken.expires_at < now() - timedelta(days=1)))
        db.commit()
        print(f"Deleted codes: {codes.rowcount}, refresh tokens: {tokens.rowcount}")


def generate_keys() -> None:
    """Print fresh secrets to paste into api/.env. Run it once; never commit the output."""
    print(f"KEK_V1={base64.b64encode(os.urandom(32)).decode()}")
    print(f"BLIND_INDEX_KEY={base64.b64encode(os.urandom(32)).decode()}")
    print(f"JWT_SECRET={secrets.token_urlsafe(48)}")
    print(f"CODE_HMAC_KEY={secrets.token_urlsafe(32)}")


def keys_status() -> None:
    from sqlalchemy import func, select

    from app.crypto.keys import get_kek_provider
    from app.models import KeyEncryptionKey, UserKey

    with SessionLocal() as db:
        counts = dict(db.execute(select(UserKey.kek_id, func.count()).group_by(UserKey.kek_id)).all())
        print(f"Loaded from the environment: {', '.join(f'KEK_V{v}' for v in get_kek_provider().versions()) or 'none'}")
        for kek in db.scalars(select(KeyEncryptionKey).order_by(KeyEncryptionKey.version)):
            print(f"KEK v{kek.version}: {kek.status.value}, {counts.get(kek.id, 0)} wrapped DEK(s)")


def rotate_kek() -> None:
    from app import audit
    from app.crypto.keys import rotate_kek as rotate
    from app.errors import AppError

    with SessionLocal() as db:
        try:
            result = rotate(db)
        except AppError as exc:
            raise SystemExit(exc.message) from exc
        audit.record(db, "kek.rotated", "key_encryption_key", None, metadata=result)
        db.commit()
    print(f"KEK v{result['fromVersion']} -> v{result['toVersion']}: {result['rewrappedKeys']} DEK(s) re-wrapped. "
          f"Remove KEK_V{result['fromVersion']} from api/.env once you have checked the application.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="create the first admin account")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)
    admin.add_argument("--password", help="omit it to type it without echo")
    sub.add_parser("mark-abandoned", help="close conversations without activity")
    sub.add_parser("purge-expired", help="delete expired codes and refresh tokens")
    sub.add_parser("generate-keys", help="print new secrets for api/.env")
    sub.add_parser("keys-status", help="show the KEK versions and how many DEKs each one protects")
    sub.add_parser("rotate-kek", help="activate the newest KEK_V<n> and re-wrap every DEK with it")
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.email, args.name, args.password)
    elif args.command == "generate-keys":
        generate_keys()
    elif args.command == "keys-status":
        keys_status()
    elif args.command == "rotate-kek":
        rotate_kek()
    elif args.command == "mark-abandoned":
        mark_abandoned()
    else:
        purge_expired()


if __name__ == "__main__":
    main()
