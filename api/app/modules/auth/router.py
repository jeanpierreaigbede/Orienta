import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Response
from pydantic import EmailStr, Field, StringConstraints
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import audit
from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.mail import send_template
from app.models import Consent, RefreshToken, User, UserRole, UserStatus, VerificationPurpose
from app.modules.auth import service
from app.repository import create_user, find_user_by_email, user_public
from app.schemas import CamelModel
from app.security import hash_password, hash_refresh_token, now, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

Password = Annotated[str, StringConstraints(min_length=10, max_length=128)]
Code = Annotated[str, StringConstraints(pattern=r"^\d{6}$")]


class RegisterIn(CamelModel):
    email: EmailStr
    password: Password
    full_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
    phone: Annotated[str, StringConstraints(pattern=r"^\+?[0-9 ]{8,20}$")] | None = None
    consent_version: Annotated[str, StringConstraints(min_length=1, max_length=50)]


class VerifyIn(CamelModel):
    email: EmailStr
    code: Code


class EmailIn(CamelModel):
    email: EmailStr


class AcceptInvitationIn(CamelModel):
    email: EmailStr
    code: Code
    password: Password


class LoginIn(CamelModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class UserOut(CamelModel):
    id: uuid.UUID
    role: UserRole
    status: UserStatus
    email: str
    full_name: str
    phone: str | None = None
    created_at: datetime


class SessionOut(CamelModel):
    user: UserOut


class AcceptedOut(CamelModel):
    message: str = Field(default="If the address is valid, an e-mail has been sent.")


def _session_out(db: Session, user: User) -> SessionOut:
    return SessionOut(user=UserOut(**user_public(db, user)))


@router.post("/register", status_code=202, response_model=AcceptedOut)
def register(body: RegisterIn, background: BackgroundTasks, db: Session = Depends(get_db)) -> AcceptedOut:
    existing = find_user_by_email(db, body.email)
    if existing is not None:
        # Same answer as a new registration: the route does not reveal which addresses exist.
        if existing.status == UserStatus.PENDING_VERIFICATION and existing.role == UserRole.PATIENT:
            try:
                code = service.issue_code(db, existing, VerificationPurpose.EMAIL_VERIFICATION)
                db.commit()
                service.send_code_email(background, db, existing, VerificationPurpose.EMAIL_VERIFICATION, code)
            except AppError:
                pass
        else:
            background.add_task(send_template, body.email, "already_registered", link=f"{get_settings().frontend_url}/login")
        return AcceptedOut()

    user = create_user(
        db, role=UserRole.PATIENT, email=body.email, full_name=body.full_name, phone=body.phone,
        password_hash=hash_password(body.password),
    )
    db.add(Consent(user_id=user.id, consent_version=body.consent_version))
    code = service.issue_code(db, user, VerificationPurpose.EMAIL_VERIFICATION, enforce_limits=False)
    audit.record(db, "user.registered", "user", user.id, actor=user)
    db.commit()
    service.send_code_email(background, db, user, VerificationPurpose.EMAIL_VERIFICATION, code)
    return AcceptedOut()


@router.post("/verify-email", response_model=SessionOut)
def verify_email(body: VerifyIn, response: Response, db: Session = Depends(get_db)) -> SessionOut:
    user = find_user_by_email(db, body.email)
    if user is None or user.status != UserStatus.PENDING_VERIFICATION or user.password_hash is None:
        raise AppError(422, "VERIFICATION_CODE_INVALID", "The verification code is invalid.")
    service.check_code(db, user, VerificationPurpose.EMAIL_VERIFICATION, body.code)
    user.status = UserStatus.ACTIVE
    user.email_verified_at = now()
    user.last_login_at = now()
    service.open_session(db, response, user)
    audit.record(db, "user.email_verified", "user", user.id, actor=user)
    db.commit()
    return _session_out(db, user)


@router.post("/resend-code", status_code=202, response_model=AcceptedOut)
def resend_code(body: EmailIn, background: BackgroundTasks, db: Session = Depends(get_db)) -> AcceptedOut:
    user = find_user_by_email(db, body.email)
    if user is not None and user.status == UserStatus.PENDING_VERIFICATION:
        purpose = VerificationPurpose.EMAIL_VERIFICATION if user.role == UserRole.PATIENT else VerificationPurpose.INVITATION
        code = service.issue_code(db, user, purpose)  # raises 429 RATE_LIMITED when too soon
        db.commit()
        service.send_code_email(background, db, user, purpose, code)
    return AcceptedOut()


@router.post("/accept-invitation", response_model=SessionOut)
def accept_invitation(body: AcceptInvitationIn, response: Response, db: Session = Depends(get_db)) -> SessionOut:
    user = find_user_by_email(db, body.email)
    if user is None or user.status != UserStatus.PENDING_VERIFICATION or user.role == UserRole.PATIENT:
        raise AppError(422, "VERIFICATION_CODE_INVALID", "The verification code is invalid.")
    service.check_code(db, user, VerificationPurpose.INVITATION, body.code)
    user.password_hash = hash_password(body.password)
    user.status = UserStatus.ACTIVE
    user.email_verified_at = now()
    user.last_login_at = now()
    service.open_session(db, response, user)
    audit.record(db, "user.invitation_accepted", "user", user.id, actor=user)
    db.commit()
    return _session_out(db, user)


@router.post("/login", response_model=SessionOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> SessionOut:
    settings = get_settings()
    user = find_user_by_email(db, body.email)
    if user is None:
        verify_password(None, body.password)  # same duration as a wrong password
        raise AppError(401, "INVALID_CREDENTIALS", "The e-mail or the password is incorrect.")
    if user.locked_until and user.locked_until > now():
        raise AppError(423, "ACCOUNT_LOCKED", "Too many failed attempts. Try again later.")
    if not verify_password(user.password_hash, body.password):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.auth_max_failed_logins:
            user.locked_until = now() + timedelta(seconds=settings.auth_lock_duration_seconds)
            user.failed_login_count = 0
        audit.record(db, "auth.login_failed", "user", user.id)
        db.commit()
        raise AppError(401, "INVALID_CREDENTIALS", "The e-mail or the password is incorrect.")
    if user.status == UserStatus.PENDING_VERIFICATION:
        raise AppError(403, "EMAIL_NOT_VERIFIED", "The e-mail address has not been verified yet.")
    if user.status == UserStatus.DISABLED:
        raise AppError(403, "ACCOUNT_DISABLED", "This account is disabled.")
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now()
    service.open_session(db, response, user)
    audit.record(db, "auth.login", "user", user.id, actor=user)
    db.commit()
    return _session_out(db, user)


@router.post("/refresh", response_model=SessionOut)
def refresh(response: Response, refresh_token: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> SessionOut:
    if not refresh_token:
        raise AppError(401, "UNAUTHENTICATED", "Authentication is required.")
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(refresh_token)).with_for_update())
    if token is None:
        raise AppError(401, "UNAUTHENTICATED", "Authentication is required.")
    if token.revoked_at is not None:
        # A token that was already rotated is being reused: revoke the whole family.
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == token.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now())
        )
        audit.record(db, "auth.refresh_token_reused", "user", token.user_id)
        db.commit()
        service.clear_cookies(response)
        raise AppError(401, "UNAUTHENTICATED", "Authentication is required.")
    user = db.get(User, token.user_id)
    if token.expires_at < now() or user is None or user.status != UserStatus.ACTIVE:
        raise AppError(401, "UNAUTHENTICATED", "Authentication is required.")
    new_token = service.open_session(db, response, user, family_id=token.family_id)
    db.flush()
    token.revoked_at = now()
    token.replaced_by_id = new_token.id
    db.commit()
    return _session_out(db, user)


@router.post("/logout", status_code=204)
def logout(response: Response, refresh_token: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> Response:
    if refresh_token:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == hash_refresh_token(refresh_token), RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now())
        )
        db.commit()
    response.status_code = 204
    service.clear_cookies(response)
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    return UserOut(**user_public(db, user))
