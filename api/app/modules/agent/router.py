import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import StringConstraints
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import audit
from app.db import get_db
from app.deps import require_role
from app.errors import AppError
from app.models import CallbackRequest, CallbackStatus, Conversation, OrientationLevel, User, UserRole
from app.modules.conversations.router import ConversationDetail, _detail
from app.repository import outcome_note, set_outcome_note, user_full_name, user_phone
from app.schemas import CamelModel
from app.security import now

router = APIRouter(prefix="/agent", tags=["agent"])
agent_only = require_role(UserRole.HEALTH_AGENT)


class CallbackOut(CamelModel):
    id: uuid.UUID
    status: CallbackStatus
    conversation_id: uuid.UUID
    orientation_level: OrientationLevel | None
    patient_name: str
    patient_phone: str | None
    assigned_to_me: bool
    created_at: datetime
    closed_at: datetime | None
    outcome_note: str | None


class CloseIn(CamelModel):
    outcome: Literal["COMPLETED", "UNREACHABLE"]
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


def _out(db: Session, callback: CallbackRequest, agent: User) -> CallbackOut:
    patient = db.get(User, callback.conversation.patient_id)
    return CallbackOut(
        id=callback.id, status=callback.status, conversation_id=callback.conversation_id,
        orientation_level=callback.conversation.orientation_level,
        patient_name=user_full_name(db, patient), patient_phone=user_phone(db, patient),
        assigned_to_me=callback.assigned_agent_id == agent.id, created_at=callback.created_at,
        closed_at=callback.closed_at,
        outcome_note=outcome_note(db, callback) if callback.assigned_agent_id == agent.id else None,
    )


def _mine(db: Session, callback_id: uuid.UUID, agent: User) -> CallbackRequest:
    callback = db.get(CallbackRequest, callback_id)
    if callback is None:
        raise AppError(404, "RESOURCE_NOT_FOUND", "Callback not found.")
    if callback.assigned_agent_id != agent.id or callback.status != CallbackStatus.ASSIGNED:
        raise AppError(409, "INVALID_TRANSITION", "This callback is not assigned to you.")
    return callback


@router.get("/callbacks", response_model=list[CallbackOut])
def list_callbacks(status: CallbackStatus | None = None, agent: User = Depends(agent_only), db: Session = Depends(get_db)) -> list[CallbackOut]:
    query = select(CallbackRequest)
    if status is not None:
        query = query.where(CallbackRequest.status == status)
    else:
        # Default view: what still needs to be done (waiting, or handled by this agent).
        query = query.where(
            (CallbackRequest.status == CallbackStatus.PENDING)
            | ((CallbackRequest.status == CallbackStatus.ASSIGNED) & (CallbackRequest.assigned_agent_id == agent.id))
        )
    rows = db.scalars(query.order_by(CallbackRequest.created_at.asc()).limit(200)).all()
    return [_out(db, c, agent) for c in rows]


@router.post("/callbacks/{callback_id}/assign", response_model=CallbackOut)
def assign(callback_id: uuid.UUID, agent: User = Depends(agent_only), db: Session = Depends(get_db)) -> CallbackOut:
    result = db.execute(
        update(CallbackRequest)
        .where(CallbackRequest.id == callback_id, CallbackRequest.status == CallbackStatus.PENDING)
        .values(status=CallbackStatus.ASSIGNED, assigned_agent_id=agent.id, assigned_at=now())
    )
    if result.rowcount == 0:
        if db.get(CallbackRequest, callback_id) is None:
            raise AppError(404, "RESOURCE_NOT_FOUND", "Callback not found.")
        raise AppError(409, "CALLBACK_ALREADY_ASSIGNED", "This callback is already handled by another agent.")
    audit.record(db, "callback.assigned", "callback_request", callback_id, actor=agent)
    db.commit()
    callback = db.get(CallbackRequest, callback_id)
    db.refresh(callback)
    return _out(db, callback, agent)


@router.post("/callbacks/{callback_id}/release", response_model=CallbackOut)
def release(callback_id: uuid.UUID, agent: User = Depends(agent_only), db: Session = Depends(get_db)) -> CallbackOut:
    callback = _mine(db, callback_id, agent)
    callback.status = CallbackStatus.PENDING
    callback.assigned_agent_id = None
    callback.assigned_at = None
    audit.record(db, "callback.released", "callback_request", callback_id, actor=agent)
    db.commit()
    return _out(db, callback, agent)


@router.post("/callbacks/{callback_id}/close", response_model=CallbackOut)
def close(callback_id: uuid.UUID, body: CloseIn, agent: User = Depends(agent_only), db: Session = Depends(get_db)) -> CallbackOut:
    callback = _mine(db, callback_id, agent)
    callback.status = CallbackStatus(body.outcome)
    callback.closed_at = now()
    set_outcome_note(db, callback, body.note or None)
    audit.record(db, "callback.closed", "callback_request", callback_id, actor=agent, metadata={"outcome": body.outcome})
    db.commit()
    return _out(db, callback, agent)


@router.get("/callbacks/{callback_id}/conversation", response_model=ConversationDetail)
def read_conversation(callback_id: uuid.UUID, agent: User = Depends(agent_only), db: Session = Depends(get_db)) -> ConversationDetail:
    callback = db.get(CallbackRequest, callback_id)
    if callback is None or callback.assigned_agent_id != agent.id:
        raise AppError(404, "RESOURCE_NOT_FOUND", "Callback not found.")
    conversation = db.get(Conversation, callback.conversation_id)
    audit.record(db, "conversation.read", "conversation", conversation.id, actor=agent, metadata={"callbackId": str(callback.id)})
    db.commit()
    return _detail(db, conversation)
