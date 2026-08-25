import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log_audit_event(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    event_type: str,
    description: str,
    agent_name: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Append-only audit trail entry. Never log PHI values here — only that
    an access/action happened, by whom, and to what resource type."""
    db.add(
        AuditLog(
            user_id=user_id,
            event_type=event_type,
            agent_name=agent_name,
            description=description,
            event_metadata=metadata or {},
        )
    )
    db.commit()
