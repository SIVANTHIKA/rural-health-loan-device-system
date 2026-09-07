import datetime
from sqlalchemy.orm import Session
from app.models import FollowUpTask
from app.services.audit_service import log_audit

def check_and_escalate_tasks(db: Session) -> dict:
    """
    Scans open/in-progress follow-up tasks and escalates overdue high/critical items.
    """
    now = datetime.datetime.utcnow()
    tasks = db.query(FollowUpTask).filter(
        FollowUpTask.status.in_(["OPEN", "IN_PROGRESS", "BLOCKED"])
    ).all()

    escalated_count = 0
    escalated_ids = []

    for task in tasks:
        is_overdue = task.due_date < now
        if is_overdue and task.escalation_level == 0:
            if task.priority in ["HIGH", "CRITICAL"]:
                task.status = "ESCALATED"
                task.escalation_level = 1
                task.assigned_to = "Operations Manager (Escalated)"
                escalated_count += 1
                escalated_ids.append(task.task_id)

                log_audit(
                    db=db,
                    action="AUTO_ESCALATE_TASK",
                    entity="FollowUpTask",
                    entity_id=task.task_id,
                    details=f"Task {task.task_id} ({task.issue_type}) priority {task.priority} exceeded due date {task.due_date}. Auto-escalated to Operations Manager."
                )
    
    db.commit()
    return {
        "checked_at": now.isoformat(),
        "total_active_tasks": len(tasks),
        "escalated_count": escalated_count,
        "escalated_task_ids": escalated_ids
    }
