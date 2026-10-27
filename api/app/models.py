"""SQLAlchemy models (chatbot-without-encryption: sensitive fields are stored in plain text)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
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

    role: Mapped[UserRole] = mapped_column(pg_enum(UserRole, "user_role"), index=True)
    status: Mapped[UserStatus] = mapped_column(pg_enum(UserStatus, "user_status"), default=UserStatus.PENDING_VERIFICATION)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(32))
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
    __table_args__ = (UniqueConstraint("conversation_id", "sequence"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    sequence: Mapped[int] = mapped_column(Integer)
    sender: Mapped[MessageSender] = mapped_column(pg_enum(MessageSender, "message_sender"))
    content: Mapped[str] = mapped_column(Text)


class CallbackRequest(TimestampMixin, Base):
    __tablename__ = "callback_requests"

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"), unique=True)
    status: Mapped[CallbackStatus] = mapped_column(pg_enum(CallbackStatus, "callback_status"), default=CallbackStatus.PENDING)
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome_note: Mapped[str | None] = mapped_column(Text)

    conversation: Mapped[Conversation] = relationship(lazy="joined")


class AuditLog(IdMixin, Base):
    __tablename__ = "audit_logs"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    actor_role: Mapped[UserRole | None] = mapped_column(pg_enum(UserRole, "user_role"))
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
