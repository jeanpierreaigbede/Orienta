import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import EmailStr, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import audit
from app.db import get_db
from app.deps import require_role
from app.errors import AppError
from app.models import AuditLog, User, UserRole, UserStatus, VerificationPurpose
from app.modules.auth import service as auth_service
from app.repository import create_user, find_user_by_email, user_public
from app.schemas import CamelModel

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require_role(UserRole.ADMIN)


class AdminUserOut(CamelModel):
    id: uuid.UUID
    role: UserRole
    status: UserStatus
    email: str
    full_name: str
    phone: str | None
    created_at: datetime


class InviteIn(CamelModel):
    email: EmailStr
    full_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
    role: Literal["HEALTH_AGENT", "ADMIN"]


class StatusIn(CamelModel):
    status: Literal["ACTIVE", "DISABLED"]


class AuditLogOut(CamelModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_role: UserRole | None
    action: str
    resource_type: str
    resource_id: uuid.UUID | None
    metadata: dict
    created_at: datetime


@router.get("/users", response_model=list[AdminUserOut])
def list_users(role: UserRole | None = None, admin: User = Depends(admin_only), db: Session = Depends(get_db)) -> list[AdminUserOut]:
    query = select(User)
    if role is not None:
        query = query.where(User.role == role)
    rows = db.scalars(query.order_by(User.created_at.desc()).limit(500)).all()
    return [AdminUserOut(**user_public(db, u)) for u in rows]


@router.post("/users", status_code=201, response_model=AdminUserOut)
def invite_user(body: InviteIn, background: BackgroundTasks, admin: User = Depends(admin_only), db: Session = Depends(get_db)) -> AdminUserOut:
    if find_user_by_email(db, body.email) is not None:
        raise AppError(409, "EMAIL_ALREADY_REGISTERED", "An account already exists for this e-mail address.")
    user = create_user(db, role=UserRole(body.role), email=body.email, full_name=body.full_name, invited_by_id=admin.id)
    code = auth_service.issue_code(db, user, VerificationPurpose.INVITATION, enforce_limits=False)
    audit.record(db, "user.invited", "user", user.id, actor=admin, metadata={"role": body.role})
    db.commit()
    auth_service.send_code_email(background, db, user, VerificationPurpose.INVITATION, code)
    return AdminUserOut(**user_public(db, user))


@router.patch("/users/{user_id}/status", response_model=AdminUserOut)
def change_status(user_id: uuid.UUID, body: StatusIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)) -> AdminUserOut:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "RESOURCE_NOT_FOUND", "User not found.")
    target = UserStatus(body.status)
    if user.status == UserStatus.PENDING_VERIFICATION or user.status == target:
        raise AppError(409, "INVALID_TRANSITION", "This status change is not allowed.")
    if target == UserStatus.DISABLED:
        if user.id == admin.id:
            raise AppError(409, "INVALID_TRANSITION", "You cannot disable your own account.")
        if user.role == UserRole.ADMIN:
            active_admins = db.scalar(
                select(func.count()).select_from(User).where(User.role == UserRole.ADMIN, User.status == UserStatus.ACTIVE)
            )
            if active_admins <= 1:
                raise AppError(409, "INVALID_TRANSITION", "The last active admin cannot be disabled.")
        auth_service.revoke_all_sessions(db, user.id)
    user.status = target
    audit.record(db, f"user.{'disabled' if target == UserStatus.DISABLED else 'enabled'}", "user", user.id, actor=admin)
    db.commit()
    return AdminUserOut(**user_public(db, user))


@router.get("/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(action: str | None = None, limit: int = Query(default=100, ge=1, le=500),
                    admin: User = Depends(admin_only), db: Session = Depends(get_db)) -> list[AuditLogOut]:
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    rows = db.scalars(query.order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [
        AuditLogOut(id=r.id, actor_id=r.actor_id, actor_role=r.actor_role, action=r.action, resource_type=r.resource_type,
                    resource_id=r.resource_id, metadata=r.metadata_ or {}, created_at=r.created_at)
        for r in rows
    ]
