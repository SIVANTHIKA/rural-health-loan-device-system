import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models import AuditLog, User

def log_audit(
    db: Session,
    action: str,
    entity: str,
    entity_id: str,
    user: Optional[User] = None,
    details: Optional[str] = None
):
    user_id = user.id if user else None
    user_name = user.name if user else "System Automated Engine"
    user_role = user.role if user else "System"

    audit_entry = AuditLog(
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        action=action,
        entity=entity,
        entity_id=entity_id,
        timestamp=datetime.datetime.utcnow(),
        details=details
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry
