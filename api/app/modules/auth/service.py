import uuid
from datetime import timedelta

from fastapi import BackgroundTasks, Response
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import AppError
from app.mail import ROLE_LABELS_FR, send_template
from app.models import EmailVerificationCode, RefreshToken, User, VerificationPurpose
from app.repository import user_email, user_full_name
from app.security import code_matches, create_access_token, generate_code, hash_code, new_refresh_token, now

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


# ---- verification codes ------------------------------------------------------------------

def issue_code(db: Session, user: User, purpose: VerificationPurpose, enforce_limits: bool = True) -> str:
    settings = get_settings()
    current = now()
    if enforce_limits:
        last = db.scalar(
            select(EmailVerificationCode.created_at)
            .where(EmailVerificationCode.user_id == user.id, EmailVerificationCode.purpose == purpose)
            .order_by(EmailVerificationCode.created_at.desc())
            .limit(1)
        )
        if last and (current - last).total_seconds() < settings.verification_resend_cooldown_seconds:
            raise AppError(429, "RATE_LIMITED", "Please wait before requesting a new code.")
        sent_last_hour = db.scalar(
            select(func.count())
            .select_from(EmailVerificationCode)
            .where(
                EmailVerificationCode.user_id == user.id,
                EmailVerificationCode.created_at > current - timedelta(hours=1),
            )
        )
        if sent_last_hour >= settings.verification_max_resends_per_hour:
            raise AppError(429, "RATE_LIMITED", "Too many codes requested. Try again later.")

    # A new code always invalidates the previous one.
    db.execute(
        update(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.purpose == purpose,
            EmailVerificationCode.consumed_at.is_(None),
        )
        .values(consumed_at=current)
    )
    code = generate_code()
    db.add(
        EmailVerificationCode(
            id=uuid.uuid4(),
            user_id=user.id,
            purpose=purpose,
            code_hash=hash_code(code),
            expires_at=current + timedelta(seconds=settings.verification_code_ttl_seconds),
            attempt_count=0,
        )
    )
    return code


def check_code(db: Session, user: User, purpose: VerificationPurpose, code: str) -> None:
    settings = get_settings()
    row = db.scalar(
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.purpose == purpose,
            EmailVerificationCode.consumed_at.is_(None),
        )
        .with_for_update()
    )
    if row is None:
        raise AppError(422, "VERIFICATION_CODE_INVALID", "The verification code is invalid.")
    if row.expires_at < now():
        raise AppError(422, "VERIFICATION_CODE_EXPIRED", "The verification code has expired.")
    if not code_matches(code, row.code_hash):
        row.attempt_count += 1
        attempts_left = settings.verification_max_attempts - row.attempt_count
        if attempts_left <= 0:
            row.consumed_at = now()
        db.commit()
        raise AppError(
            422, "VERIFICATION_CODE_INVALID", "The verification code is invalid.", {"attemptsLeft": max(attempts_left, 0)}
        )
    row.consumed_at = now()


def send_code_email(background: BackgroundTasks, db: Session, user: User, purpose: VerificationPurpose, code: str) -> None:
    settings = get_settings()
    minutes = settings.verification_code_ttl_seconds // 60
    email = user_email(db, user)
    name = user_full_name(db, user)
    if purpose == VerificationPurpose.EMAIL_VERIFICATION:
        background.add_task(send_template, email, "verification_code", name=name, code=code, minutes=minutes)
    else:
        link = f"{settings.frontend_url}/accept-invitation?email={email}"
        background.add_task(
            send_template, email, "invitation", name=name, code=code, minutes=minutes,
            role_label=ROLE_LABELS_FR.get(user.role.value, ""), link=link,
        )


# ---- sessions ----------------------------------------------------------------------------

def _set_cookies(response: Response, access: str, refresh: str) -> None:
    settings = get_settings()
    response.set_cookie(
        ACCESS_COOKIE, access, max_age=settings.access_token_ttl_seconds, httponly=True,
        secure=settings.cookie_secure, samesite="lax", path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh, max_age=settings.refresh_token_ttl_seconds, httponly=True,
        secure=settings.cookie_secure, samesite="lax", path=REFRESH_COOKIE_PATH,
    )


def clear_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


def open_session(db: Session, response: Response, user: User, family_id: uuid.UUID | None = None) -> RefreshToken:
    settings = get_settings()
    raw, token_hash = new_refresh_token()
    token = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        family_id=family_id or uuid.uuid4(),
        token_hash=token_hash,
        expires_at=now() + timedelta(seconds=settings.refresh_token_ttl_seconds),
    )
    db.add(token)
    _set_cookies(response, create_access_token(user.id, user.role.value), raw)
    return token


def revoke_all_sessions(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now())
    )
