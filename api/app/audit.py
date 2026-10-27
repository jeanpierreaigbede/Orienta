import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
    actor: User | None = None,
    metadata: dict | None = None,
) -> None:
    """Append an audit entry. Never put personal data or message content in metadata."""
    db.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            actor_role=actor.role if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_=metadata or {},
        )
    )
