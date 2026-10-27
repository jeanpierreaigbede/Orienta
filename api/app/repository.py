"""Reading and writing personal data.

Every module goes through these helpers to read or write a name, an e-mail, a phone number,
a message or an agent note. In this branch the values are stored in plain text; the
chatbot-with-encryption branch changes only this file (and the models) to encrypt them.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CallbackRequest, Conversation, Message, MessageSender, User, UserRole, UserStatus
from app.security import normalize_email


# ---- users -------------------------------------------------------------------------------

def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def create_user(
    db: Session,
    *,
    role: UserRole,
    email: str,
    full_name: str,
    phone: str | None = None,
    password_hash: str | None = None,
    invited_by_id: uuid.UUID | None = None,
) -> User:
    user = User(
        id=uuid.uuid4(),
        role=role,
        status=UserStatus.PENDING_VERIFICATION,
        email=normalize_email(email),
        full_name=full_name.strip(),
        phone=phone,
        password_hash=password_hash,
        invited_by_id=invited_by_id,
        failed_login_count=0,
    )
    db.add(user)
    db.flush()
    return user


def user_email(db: Session, user: User) -> str:
    return user.email


def user_full_name(db: Session, user: User) -> str:
    return user.full_name


def user_phone(db: Session, user: User) -> str | None:
    return user.phone


def user_public(db: Session, user: User) -> dict:
    return {
        "id": user.id,
        "role": user.role,
        "status": user.status,
        "email": user_email(db, user),
        "full_name": user_full_name(db, user),
        "phone": user_phone(db, user),
        "created_at": user.created_at,
    }


# ---- messages ----------------------------------------------------------------------------

def add_message(db: Session, conversation: Conversation, sender: MessageSender, text: str) -> Message:
    sequence = len(conversation.messages) + 1
    message = Message(id=uuid.uuid4(), conversation_id=conversation.id, sequence=sequence, sender=sender, content=text)
    db.add(message)
    conversation.messages.append(message)
    db.flush()
    return message


def message_text(db: Session, conversation: Conversation, message: Message) -> str:
    return message.content


def messages_public(db: Session, conversation: Conversation) -> list[dict]:
    return [
        {"id": m.id, "sequence": m.sequence, "sender": m.sender, "content": message_text(db, conversation, m), "created_at": m.created_at}
        for m in conversation.messages
    ]


# ---- agent notes -------------------------------------------------------------------------

def set_outcome_note(db: Session, callback: CallbackRequest, note: str | None) -> None:
    callback.outcome_note = note


def outcome_note(db: Session, callback: CallbackRequest) -> str | None:
    return callback.outcome_note
