"""Reading and writing personal data.

Every module goes through these helpers to read or write a name, an e-mail, a phone number,
a message or an agent note. In this branch every value is encrypted with the DEK of the user
it belongs to (AES-256-GCM) before it reaches the database, and decrypted after it is read.
Compare with the chatbot-without-encryption branch: the function signatures are identical.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crypto.blind_index import email_index, phone_index
from app.crypto.envelope import decrypt_text, encrypt_text
from app.crypto.keys import get_dek, new_user_dek, store_user_key
from app.models import (
    CallbackRequest,
    Conversation,
    EncryptionMode,
    Message,
    MessageSender,
    User,
    UserRole,
    UserStatus,
)
from app.config import get_settings


def _aad(user: User, field: str) -> str:
    return f"users:{user.id}:{field}"


# ---- users -------------------------------------------------------------------------------

def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email_blind_index == email_index(email)))


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
    user_id = uuid.uuid4()
    user = User(id=user_id, role=role, status=UserStatus.PENDING_VERIFICATION, password_hash=password_hash,
                invited_by_id=invited_by_id, failed_login_count=0)
    dek = new_user_dek(db, user_id)
    user.email_ciphertext, user.email_nonce = encrypt_text(dek, email.strip().lower(), _aad(user, "email"))
    user.email_blind_index = email_index(email)
    user.full_name_ciphertext, user.full_name_nonce = encrypt_text(dek, full_name.strip(), _aad(user, "full_name"))
    if phone:
        user.phone_ciphertext, user.phone_nonce = encrypt_text(dek, phone, _aad(user, "phone"))
        user.phone_blind_index = phone_index(phone)
    db.add(user)
    db.flush()  # the user row must exist before its key (user_keys.user_id is a foreign key)
    store_user_key(db, user_id, dek)
    db.flush()
    return user


def user_email(db: Session, user: User) -> str:
    return decrypt_text(get_dek(db, user.id), user.email_ciphertext, user.email_nonce, _aad(user, "email"))


def user_full_name(db: Session, user: User) -> str:
    return decrypt_text(get_dek(db, user.id), user.full_name_ciphertext, user.full_name_nonce, _aad(user, "full_name"))


def user_phone(db: Session, user: User) -> str | None:
    if user.phone_ciphertext is None:
        return None
    return decrypt_text(get_dek(db, user.id), user.phone_ciphertext, user.phone_nonce, _aad(user, "phone"))


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

def _message_aad(conversation: Conversation, sequence: int) -> str:
    return f"messages:{conversation.id}:{sequence}"


def add_message(db: Session, conversation: Conversation, sender: MessageSender, text: str) -> Message:
    sequence = len(conversation.messages) + 1
    message = Message(id=uuid.uuid4(), conversation_id=conversation.id, sequence=sequence, sender=sender)
    # ENCRYPTION_ENABLED in api/.env decides how NEW messages are stored; existing rows stay readable either way.
    mode = EncryptionMode.ENCRYPTED if get_settings().encryption_enabled else EncryptionMode.PLAINTEXT
    message.encryption_mode = mode
    if mode == EncryptionMode.ENCRYPTED:
        # The patient's DEK encrypts every message of the conversation, with a new nonce each time.
        dek = get_dek(db, conversation.patient_id)
        message.content_ciphertext, message.content_nonce = encrypt_text(dek, text, _message_aad(conversation, sequence))
    else:
        message.content_plaintext = text
    db.add(message)
    conversation.messages.append(message)
    db.flush()
    return message


def message_text(db: Session, conversation: Conversation, message: Message) -> str:
    if message.encryption_mode == EncryptionMode.PLAINTEXT:
        return message.content_plaintext or ""
    dek = get_dek(db, conversation.patient_id)
    return decrypt_text(dek, message.content_ciphertext, message.content_nonce, _message_aad(conversation, message.sequence))


def messages_public(db: Session, conversation: Conversation) -> list[dict]:
    return [
        {"id": m.id, "sequence": m.sequence, "sender": m.sender, "content": message_text(db, conversation, m), "created_at": m.created_at}
        for m in conversation.messages
    ]


# ---- agent notes -------------------------------------------------------------------------

def _note_aad(callback: CallbackRequest) -> str:
    return f"callback_requests:{callback.id}:outcome_note"


def set_outcome_note(db: Session, callback: CallbackRequest, note: str | None) -> None:
    if not note:
        callback.outcome_note_ciphertext = callback.outcome_note_nonce = None
        return
    dek = get_dek(db, callback.conversation.patient_id)  # the note is about the patient: the patient's DEK
    callback.outcome_note_ciphertext, callback.outcome_note_nonce = encrypt_text(dek, note, _note_aad(callback))


def outcome_note(db: Session, callback: CallbackRequest) -> str | None:
    if callback.outcome_note_ciphertext is None:
        return None
    dek = get_dek(db, callback.conversation.patient_id)
    return decrypt_text(dek, callback.outcome_note_ciphertext, callback.outcome_note_nonce, _note_aad(callback))
