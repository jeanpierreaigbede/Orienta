"""SQLAlchemy models (chatbot-with-encryption).

Every sensitive field is stored as <field>_ciphertext + <field>_nonce (AES-256-GCM, user DEK).
E-mail and phone also get a blind index (HMAC-SHA256) so they can be searched without decryption.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRole(str, enum.Enum):
    PATIENT = "PATIENT"
    HEALTH_AGENT = "HEALTH_AGENT"
    ADMIN = "ADMIN"


class UserStatus(str, enum.Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class VerificationPurpose(str, enum.Enum):
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    INVITATION = "INVITATION"


class ConversationStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    ORIENTED = "ORIENTED"
    ABANDONED = "ABANDONED"


class OrientationLevel(str, enum.Enum):
    EMERGENCY = "EMERGENCY"
    CONSULTATION_48H = "CONSULTATION_48H"
    HOME_CARE = "HOME_CARE"


class MessageSender(str, enum.Enum):
    PATIENT = "PATIENT"
    ASSISTANT = "ASSISTANT"


class UserKeyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DESTROYED = "DESTROYED"


class KekStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class EncryptionMode(str, enum.Enum):
    ENCRYPTED = "ENCRYPTED"
    PLAINTEXT = "PLAINTEXT"


class CallbackStatus(str, enum.Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    COMPLETED = "COMPLETED"
    UNREACHABLE = "UNREACHABLE"


def pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TimestampMixin(IdMixin):
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email_blind_index", name="uq_users_email_blind_index"),
        Index("uq_users_phone_blind_index", "phone_blind_index", unique=True,
              postgresql_where=text("phone_blind_index IS NOT NULL")),
    )

    role: Mapped[UserRole] = mapped_column(pg_enum(UserRole, "user_role"), index=True)
    status: Mapped[UserStatus] = mapped_column(pg_enum(UserStatus, "user_status"), default=UserStatus.PENDING_VERIFICATION)
    email_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    email_nonce: Mapped[bytes] = mapped_column(LargeBinary)
    email_blind_index: Mapped[bytes] = mapped_column(LargeBinary)
    full_name_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    full_name_nonce: Mapped[bytes] = mapped_column(LargeBinary)
    phone_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    phone_nonce: Mapped[bytes | None] = mapped_column(LargeBinary)
    phone_blind_index: Mapped[bytes | None] = mapped_column(LargeBinary)
    password_hash: Mapped[str | None] = mapped_column(Text)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class EmailVerificationCode(TimestampMixin, Base):
    __tablename__ = "email_verification_codes"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[VerificationPurpose] = mapped_column(pg_enum(VerificationPurpose, "verification_purpose"))
    code_hash: Mapped[bytes]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(index=True)
    token_hash: Mapped[bytes] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("refresh_tokens.id"), unique=True)


class Consent(IdMixin, Base):
    __tablename__ = "consents"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    consent_version: Mapped[str] = mapped_column(Text)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[ConversationStatus] = mapped_column(
        pg_enum(ConversationStatus, "conversation_status"), default=ConversationStatus.IN_PROGRESS
    )
    orientation_level: Mapped[OrientationLevel | None] = mapped_column(pg_enum(OrientationLevel, "orientation_level"))
    oriented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    follow_up_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    messages: Mapped[list["Message"]] = relationship(order_by="Message.sequence", lazy="selectin")


class Message(IdMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence"),
        CheckConstraint(
            "(encryption_mode = 'ENCRYPTED' AND content_ciphertext IS NOT NULL AND content_nonce IS NOT NULL AND content_plaintext IS NULL)"
            " OR (encryption_mode = 'PLAINTEXT' AND content_plaintext IS NOT NULL AND content_ciphertext IS NULL)",
            name="ck_messages_encryption_mode",
        ),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    sequence: Mapped[int] = mapped_column(Integer)
    sender: Mapped[MessageSender] = mapped_column(pg_enum(MessageSender, "message_sender"))
    encryption_mode: Mapped[EncryptionMode] = mapped_column(pg_enum(EncryptionMode, "encryption_mode"), default=EncryptionMode.ENCRYPTED)
    content_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    content_nonce: Mapped[bytes | None] = mapped_column(LargeBinary)
    content_plaintext: Mapped[str | None] = mapped_column(Text)  # only when ENCRYPTION_ENABLED=false (demo)


class CallbackRequest(TimestampMixin, Base):
    __tablename__ = "callback_requests"

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"), unique=True)
    status: Mapped[CallbackStatus] = mapped_column(pg_enum(CallbackStatus, "callback_status"), default=CallbackStatus.PENDING)
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome_note_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    outcome_note_nonce: Mapped[bytes | None] = mapped_column(LargeBinary)

    conversation: Mapped[Conversation] = relationship(lazy="joined")


class KeyEncryptionKey(TimestampMixin, Base):
    """Metadata of a master key version. The key itself lives in the KEK_V<version> environment variable."""

    __tablename__ = "key_encryption_keys"
    __table_args__ = (
        Index("uq_key_encryption_keys_active", "status", unique=True, postgresql_where=text("status = 'ACTIVE'")),
    )

    version: Mapped[int] = mapped_column(Integer, unique=True)
    status: Mapped[KekStatus] = mapped_column(pg_enum(KekStatus, "kek_status"))
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserKey(TimestampMixin, Base):
    """One DEK per user, stored wrapped (encrypted) by the active KEK."""

    __tablename__ = "user_keys"
    __table_args__ = (CheckConstraint("status = 'ACTIVE' OR wrapped_dek IS NULL", name="ck_user_keys_destroyed"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    kek_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("key_encryption_keys.id"), index=True)
    wrapped_dek: Mapped[bytes | None] = mapped_column(LargeBinary)
    wrapped_dek_nonce: Mapped[bytes | None] = mapped_column(LargeBinary)
    status: Mapped[UserKeyStatus] = mapped_column(pg_enum(UserKeyStatus, "user_key_status"), default=UserKeyStatus.ACTIVE)
    destroyed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(IdMixin, Base):
    __tablename__ = "audit_logs"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    actor_role: Mapped[UserRole | None] = mapped_column(pg_enum(UserRole, "user_role"))
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
