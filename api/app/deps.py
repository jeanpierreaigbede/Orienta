import uuid

import jwt
from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import User, UserRole, UserStatus
from app.security import decode_access_token


def get_current_user(access_token: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> User:
    if not access_token:
        raise AppError(401, "UNAUTHENTICATED", "Authentication is required.")
    try:
        claims = decode_access_token(access_token)
    except jwt.ExpiredSignatureError as exc:
        raise AppError(401, "TOKEN_EXPIRED", "The access token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise AppError(401, "UNAUTHENTICATED", "The access token is invalid.") from exc
    user = db.get(User, uuid.UUID(claims["sub"]))
    if user is None:
        raise AppError(401, "UNAUTHENTICATED", "The access token is invalid.")
    if user.status == UserStatus.DISABLED:
        raise AppError(403, "ACCOUNT_DISABLED", "This account is disabled.")
    return user


def require_role(*roles: UserRole):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise AppError(403, "FORBIDDEN_ROLE", "This route is not available for your role.")
        return user

    return checker
