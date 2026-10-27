"""Command line tools.

    python -m app.cli create-admin --email admin@orienta.local --name "Admin Orienta"
    python -m app.cli mark-abandoned
    python -m app.cli purge-expired
"""

import argparse
import getpass
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


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="create the first admin account")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)
    admin.add_argument("--password", help="omit it to type it without echo")
    sub.add_parser("mark-abandoned", help="close conversations without activity")
    sub.add_parser("purge-expired", help="delete expired codes and refresh tokens")
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.email, args.name, args.password)
    elif args.command == "mark-abandoned":
        mark_abandoned()
    else:
        purge_expired()


if __name__ == "__main__":
    main()
