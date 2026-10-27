import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import StringConstraints
from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app import audit
from app.db import get_db
from app.deps import require_role
from app.errors import AppError
from app.llm import ChatModel, get_chat_model
from app.models import Conversation, ConversationStatus, MessageSender, OrientationLevel, User, UserRole
from app.modules.conversations.triage import process_patient_message
from app.repository import messages_public
from app.schemas import CamelModel

router = APIRouter(prefix="/conversations", tags=["conversations"])
patient_only = require_role(UserRole.PATIENT)

MessageText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class MessageIn(CamelModel):
    content: MessageText


class MessageOut(CamelModel):
    id: uuid.UUID
    sequence: int
    sender: MessageSender
    content: str
    created_at: datetime


class ConversationSummary(CamelModel):
    id: uuid.UUID
    status: ConversationStatus
    orientation_level: OrientationLevel | None
    created_at: datetime
    last_message_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageOut]


class ConversationPage(CamelModel):
    items: list[ConversationSummary]
    next_cursor: str | None


def get_model() -> ChatModel:
    return get_chat_model()


def _owned(db: Session, conversation_id: uuid.UUID, patient: User) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.patient_id != patient.id:
        raise AppError(404, "RESOURCE_NOT_FOUND", "Conversation not found.")
    return conversation


def _detail(db: Session, conversation: Conversation) -> ConversationDetail:
    return ConversationDetail(
        id=conversation.id, status=conversation.status, orientation_level=conversation.orientation_level,
        created_at=conversation.created_at, last_message_at=conversation.last_message_at,
        messages=[MessageOut(**m) for m in messages_public(db, conversation)],
    )


@router.post("", status_code=201, response_model=ConversationDetail)
def start_conversation(body: MessageIn, patient: User = Depends(patient_only), db: Session = Depends(get_db),
                       model: ChatModel = Depends(get_model)) -> ConversationDetail:
    conversation = Conversation(id=uuid.uuid4(), patient_id=patient.id, follow_up_count=0)
    db.add(conversation)
    db.flush()
    audit.record(db, "conversation.started", "conversation", conversation.id, actor=patient)
    process_patient_message(db, model, conversation, patient, body.content)
    db.refresh(conversation)
    return _detail(db, conversation)


@router.get("", response_model=ConversationPage)
def list_conversations(cursor: uuid.UUID | None = None, limit: int = Query(default=20, ge=1, le=50),
                       patient: User = Depends(patient_only), db: Session = Depends(get_db)) -> ConversationPage:
    query = select(Conversation).where(Conversation.patient_id == patient.id)
    if cursor is not None:
        anchor = _owned(db, cursor, patient)
        query = query.where(tuple_(Conversation.created_at, Conversation.id) < (anchor.created_at, anchor.id))
    rows = db.scalars(query.order_by(Conversation.created_at.desc(), Conversation.id.desc()).limit(limit + 1)).all()
    items = [ConversationSummary.model_validate(c) for c in rows[:limit]]
    return ConversationPage(items=items, next_cursor=str(rows[limit - 1].id) if len(rows) > limit else None)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: uuid.UUID, patient: User = Depends(patient_only), db: Session = Depends(get_db)) -> ConversationDetail:
    return _detail(db, _owned(db, conversation_id, patient))


@router.post("/{conversation_id}/messages", response_model=ConversationDetail)
def send_message(conversation_id: uuid.UUID, body: MessageIn, patient: User = Depends(patient_only),
                 db: Session = Depends(get_db), model: ChatModel = Depends(get_model)) -> ConversationDetail:
    conversation = _owned(db, conversation_id, patient)
    process_patient_message(db, model, conversation, patient, body.content)
    db.refresh(conversation)
    return _detail(db, conversation)
