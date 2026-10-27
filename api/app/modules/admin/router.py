"""Administration (/oriadmin): overview, patients, team, orientations, audit log.

Admins see who was oriented and at which level, never the content of a conversation.
"""

import uuid
from datetime import datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import EmailStr, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import audit
from app.db import get_db
from app.deps import require_role
from app.errors import AppError
from app.models import (
    AuditLog,
    CallbackRequest,
    CallbackStatus,
    Conversation,
    ConversationStatus,
    OrientationLevel,
    User,
    UserRole,
    UserStatus,
    VerificationPurpose,
)
from app.modules.auth import service as auth_service
from app.repository import create_user, find_user_by_email, user_email, user_full_name, user_phone, user_public
from app.schemas import CamelModel
from app.security import now

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require_role(UserRole.ADMIN)
TEAM_ROLES = (UserRole.HEALTH_AGENT, UserRole.ADMIN)


def mask_phone(phone: str | None) -> str | None:
    """Admins see a masked number: the agent who handles a callback sees the full one."""
    if not phone:
        return None
    digits = [c for c in phone if c.isdigit()]
    if len(digits) < 6:
        return "•" * len(digits)
    return phone[: len(phone) - 6] + " •• " + "".join(digits[-2:])


def minutes_since(moment: datetime | None) -> int | None:
    return int((now() - moment).total_seconds() // 60) if moment else None


# ---- schemas -----------------------------------------------------------------------------

class UrgentItem(CamelModel):
    callback_id: uuid.UUID
    patient_name: str
    oriented_at: datetime | None
    waiting_minutes: int | None
    status: CallbackStatus
    agent_name: str | None


class OverviewOut(CamelModel):
    patients: int
    patients_this_week: int
    active_agents: int
    pending_invitations: int
    conversations_in_progress: int
    urgent_waiting: int
    oldest_urgent_minutes: int | None
    urgent: list[UrgentItem]


class PatientOut(CamelModel):
    id: uuid.UUID
    status: UserStatus
    email: str
    full_name: str
    phone_masked: str | None
    conversations: int
    created_at: datetime


class PatientPage(CamelModel):
    items: list[PatientOut]
    counts: dict[str, int]


class TeamMemberOut(CamelModel):
    id: uuid.UUID
    role: UserRole
    status: UserStatus
    email: str
    full_name: str
    callbacks_in_progress: int
    callbacks_closed_30_days: int
    last_login_at: datetime | None
    created_at: datetime


class TeamPage(CamelModel):
    items: list[TeamMemberOut]
    counts: dict[str, int]


class InviteIn(CamelModel):
    email: EmailStr
    full_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
    role: Literal["HEALTH_AGENT", "ADMIN"]


class StatusIn(CamelModel):
    status: Literal["ACTIVE", "DISABLED"]


class UserOut(CamelModel):
    id: uuid.UUID
    role: UserRole
    status: UserStatus
    email: str
    full_name: str
    phone: str | None
    created_at: datetime


class CallbackSummary(CamelModel):
    status: CallbackStatus
    agent_name: str | None
    waiting_minutes: int | None


class OrientationItem(CamelModel):
    id: uuid.UUID
    created_at: datetime
    patient_name: str
    status: ConversationStatus
    orientation_level: OrientationLevel | None
    follow_up_count: int
    callback: CallbackSummary | None


class OrientationStats(CamelModel):
    in_progress: int
    urgent_waiting: int
    average_callback_delay_minutes: int | None
    average_questions: float | None


class OrientationPage(CamelModel):
    stats: OrientationStats
    counts: dict[str, int]
    items: list[OrientationItem]


class AuditLogOut(CamelModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_name: str | None
    actor_role: UserRole | None
    action: str
    resource_type: str
    resource_id: uuid.UUID | None
    metadata: dict
    created_at: datetime


AUDIT_CATEGORIES = {"auth": "auth.", "accounts": "user.", "conversations": "conversation.", "callbacks": "callback."}


# ---- helpers -----------------------------------------------------------------------------

def _count(db: Session, query) -> int:
    return db.scalar(select(func.count()).select_from(query.subquery())) or 0


def _name_cache(db: Session):
    cache: dict[uuid.UUID, str] = {}

    def name(user_id: uuid.UUID | None) -> str | None:
        if user_id is None:
            return None
        if user_id not in cache:
            user = db.get(User, user_id)
            cache[user_id] = user_full_name(db, user) if user else None
        return cache[user_id]

    return name


# ---- overview ----------------------------------------------------------------------------

@router.get("/overview", response_model=OverviewOut)
def overview(admin: User = Depends(admin_only), db: Session = Depends(get_db)) -> OverviewOut:
    name = _name_cache(db)
    patients = select(User).where(User.role == UserRole.PATIENT)
    open_callbacks = db.scalars(
        select(CallbackRequest)
        .where(CallbackRequest.status.in_([CallbackStatus.PENDING, CallbackStatus.ASSIGNED]))
        .order_by(CallbackRequest.created_at.asc())
        .limit(20)
    ).all()
    waiting = [c for c in open_callbacks if c.status == CallbackStatus.PENDING]
    return OverviewOut(
        patients=_count(db, patients),
        patients_this_week=_count(db, patients.where(User.created_at > now() - timedelta(days=7))),
        active_agents=_count(db, select(User).where(User.role == UserRole.HEALTH_AGENT, User.status == UserStatus.ACTIVE)),
        pending_invitations=_count(db, select(User).where(User.role.in_(TEAM_ROLES), User.status == UserStatus.PENDING_VERIFICATION)),
        conversations_in_progress=_count(db, select(Conversation).where(Conversation.status == ConversationStatus.IN_PROGRESS)),
        urgent_waiting=len(waiting),
        oldest_urgent_minutes=minutes_since(waiting[0].created_at) if waiting else None,
        urgent=[
            UrgentItem(
                callback_id=c.id, patient_name=name(c.conversation.patient_id) or "", oriented_at=c.conversation.oriented_at,
                waiting_minutes=minutes_since(c.created_at) if c.status == CallbackStatus.PENDING else None,
                status=c.status, agent_name=name(c.assigned_agent_id),
            )
            for c in open_callbacks
        ],
    )


# ---- patients ----------------------------------------------------------------------------

@router.get("/patients", response_model=PatientPage)
def list_patients(status: UserStatus | None = None, q: str | None = Query(default=None, max_length=100),
                  admin: User = Depends(admin_only), db: Session = Depends(get_db)) -> PatientPage:
    base = select(User).where(User.role == UserRole.PATIENT)
    counts = {"ALL": _count(db, base)} | {s.value: _count(db, base.where(User.status == s)) for s in UserStatus}
    query = base if status is None else base.where(User.status == status)
    rows = db.scalars(query.order_by(User.created_at.desc()).limit(500)).all()
    conversations = dict(db.execute(select(Conversation.patient_id, func.count()).group_by(Conversation.patient_id)).all())
    items = []
    for u in rows:
        email, full_name = user_email(db, u), user_full_name(db, u)
        # Names and e-mails may be encrypted in the database: the search runs after reading them.
        if q and q.lower() not in f"{full_name} {email}".lower():
            continue
        items.append(PatientOut(id=u.id, status=u.status, email=email, full_name=full_name,
                                phone_masked=mask_phone(user_phone(db, u)), conversations=conversations.get(u.id, 0),
                                created_at=u.created_at))
    return PatientPage(items=items[:100], counts=counts)


# ---- team (health agents and admins) -----------------------------------------------------

@router.get("/team", response_model=TeamPage)
def list_team(role: Literal["HEALTH_AGENT", "ADMIN"] | None = None, admin: User = Depends(admin_only),
              db: Session = Depends(get_db)) -> TeamPage:
    base = select(User).where(User.role.in_(TEAM_ROLES))
    counts = {"ALL": _count(db, base), "HEALTH_AGENT": _count(db, base.where(User.role == UserRole.HEALTH_AGENT)),
              "ADMIN": _count(db, base.where(User.role == UserRole.ADMIN))}
    query = base if role is None else base.where(User.role == UserRole(role))
    rows = db.scalars(query.order_by(User.role, User.created_at)).all()
    in_progress = dict(db.execute(
        select(CallbackRequest.assigned_agent_id, func.count())
        .where(CallbackRequest.status == CallbackStatus.ASSIGNED).group_by(CallbackRequest.assigned_agent_id)
    ).all())
    closed = dict(db.execute(
        select(CallbackRequest.assigned_agent_id, func.count())
        .where(CallbackRequest.status.in_([CallbackStatus.COMPLETED, CallbackStatus.UNREACHABLE]),
               CallbackRequest.closed_at > now() - timedelta(days=30))
        .group_by(CallbackRequest.assigned_agent_id)
    ).all())
    items = [
        TeamMemberOut(id=u.id, role=u.role, status=u.status, email=user_email(db, u), full_name=user_full_name(db, u),
                      callbacks_in_progress=in_progress.get(u.id, 0), callbacks_closed_30_days=closed.get(u.id, 0),
                      last_login_at=u.last_login_at, created_at=u.created_at)
        for u in rows
    ]
    return TeamPage(items=items, counts=counts)


@router.post("/team", status_code=201, response_model=UserOut)
def invite_member(body: InviteIn, background: BackgroundTasks, admin: User = Depends(admin_only),
                  db: Session = Depends(get_db)) -> UserOut:
    if find_user_by_email(db, body.email) is not None:
        raise AppError(409, "EMAIL_ALREADY_REGISTERED", "An account already exists for this e-mail address.")
    user = create_user(db, role=UserRole(body.role), email=body.email, full_name=body.full_name, invited_by_id=admin.id)
    code = auth_service.issue_code(db, user, VerificationPurpose.INVITATION, enforce_limits=False)
    audit.record(db, "user.invited", "user", user.id, actor=admin, metadata={"role": body.role})
    db.commit()
    auth_service.send_code_email(background, db, user, VerificationPurpose.INVITATION, code)
    return UserOut(**user_public(db, user))


@router.post("/team/{user_id}/resend-invitation", status_code=202)
def resend_invitation(user_id: uuid.UUID, background: BackgroundTasks, admin: User = Depends(admin_only),
                      db: Session = Depends(get_db)) -> dict:
    user = db.get(User, user_id)
    if user is None or user.role not in TEAM_ROLES:
        raise AppError(404, "RESOURCE_NOT_FOUND", "User not found.")
    if user.status != UserStatus.PENDING_VERIFICATION:
        raise AppError(409, "INVALID_TRANSITION", "This invitation has already been accepted.")
    code = auth_service.issue_code(db, user, VerificationPurpose.INVITATION)  # 429 RATE_LIMITED when too soon
    audit.record(db, "user.invitation_resent", "user", user.id, actor=admin)
    db.commit()
    auth_service.send_code_email(background, db, user, VerificationPurpose.INVITATION, code)
    return {"status": "sent"}


@router.patch("/users/{user_id}/status", response_model=UserOut)
def change_status(user_id: uuid.UUID, body: StatusIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)) -> UserOut:
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
            active_admins = _count(db, select(User).where(User.role == UserRole.ADMIN, User.status == UserStatus.ACTIVE))
            if active_admins <= 1:
                raise AppError(409, "INVALID_TRANSITION", "The last active admin cannot be disabled.")
        auth_service.revoke_all_sessions(db, user.id)
    user.status = target
    audit.record(db, f"user.{'disabled' if target == UserStatus.DISABLED else 'enabled'}", "user", user.id, actor=admin)
    db.commit()
    return UserOut(**user_public(db, user))


# ---- orientations ------------------------------------------------------------------------

@router.get("/orientations", response_model=OrientationPage)
def list_orientations(status: ConversationStatus | None = None, level: OrientationLevel | None = None,
                      admin: User = Depends(admin_only), db: Session = Depends(get_db)) -> OrientationPage:
    name = _name_cache(db)
    counts = {"ALL": _count(db, select(Conversation))} | {
        s.value: _count(db, select(Conversation).where(Conversation.status == s)) for s in ConversationStatus
    }
    query = select(Conversation)
    if status is not None:
        query = query.where(Conversation.status == status)
    if level is not None:
        query = query.where(Conversation.orientation_level == level)
    rows = db.scalars(query.order_by(Conversation.created_at.desc()).limit(200)).all()
    callbacks = {c.conversation_id: c for c in db.scalars(
        select(CallbackRequest).where(CallbackRequest.conversation_id.in_([r.id for r in rows]))
    ).all()} if rows else {}

    month = now() - timedelta(days=30)
    assigned = db.scalars(select(CallbackRequest).where(CallbackRequest.assigned_at.is_not(None), CallbackRequest.created_at > month)).all()
    delays = [(c.assigned_at - c.created_at).total_seconds() / 60 for c in assigned]
    oriented = db.scalars(select(Conversation.follow_up_count).where(Conversation.status == ConversationStatus.ORIENTED,
                                                                    Conversation.created_at > month)).all()
    stats = OrientationStats(
        in_progress=counts[ConversationStatus.IN_PROGRESS.value],
        urgent_waiting=_count(db, select(CallbackRequest).where(CallbackRequest.status == CallbackStatus.PENDING)),
        average_callback_delay_minutes=round(sum(delays) / len(delays)) if delays else None,
        average_questions=round(sum(oriented) / len(oriented), 1) if oriented else None,
    )
    items = []
    for c in rows:
        cb = callbacks.get(c.id)
        items.append(OrientationItem(
            id=c.id, created_at=c.created_at, patient_name=name(c.patient_id) or "", status=c.status,
            orientation_level=c.orientation_level, follow_up_count=c.follow_up_count,
            callback=CallbackSummary(status=cb.status, agent_name=name(cb.assigned_agent_id),
                                     waiting_minutes=minutes_since(cb.created_at) if cb.status == CallbackStatus.PENDING else None)
            if cb else None,
        ))
    return OrientationPage(stats=stats, counts=counts, items=items)


# ---- audit log ---------------------------------------------------------------------------

@router.get("/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(category: Literal["auth", "accounts", "conversations", "callbacks"] | None = None,
                    action: str | None = Query(default=None, max_length=100), limit: int = Query(default=100, ge=1, le=500),
                    admin: User = Depends(admin_only), db: Session = Depends(get_db)) -> list[AuditLogOut]:
    name = _name_cache(db)
    query = select(AuditLog)
    if category:
        query = query.where(AuditLog.action.startswith(AUDIT_CATEGORIES[category]))
    if action:
        query = query.where(AuditLog.action.contains(action))
    rows = db.scalars(query.order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [
        AuditLogOut(id=r.id, actor_id=r.actor_id, actor_name=name(r.actor_id), actor_role=r.actor_role, action=r.action,
                    resource_type=r.resource_type, resource_id=r.resource_id, metadata=r.metadata_ or {}, created_at=r.created_at)
        for r in rows
    ]
