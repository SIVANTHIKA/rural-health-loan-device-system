"""
Clinical Task Escalation & SLA Monitoring Service
=================================================
In resource-constrained rural health settings, loanable medical equipment often
travels long distances between remote outposts and district hubs. When follow-up
tasks (such as biohazard decontamination, missing diagnostic probes, or physical
service) stall, devices risk remaining out of circulation or inadvertently being
re-issued without proper safety clearance.

This service implements automated, deterministic Service Level Agreement (SLA)
monitoring to enforce clinical governance and prevent critical bottlenecks.
"""

import datetime
from sqlalchemy.orm import Session
from app.models import FollowUpTask
from app.services.audit_service import log_audit

def check_and_escalate_tasks(db: Session) -> dict:
    """
    Automated SLA Monitor & Auto-Escalation Engine.
    
    Clinical & Operational Rationale:
    ---------------------------------
    1. Proactive Risk Mitigation: In remote healthcare networks with high staff turnover
       and limited on-site technical supervisors, high-severity issues (biohazards, missing
       critical sensors) cannot rely on passive reminder systems.
    2. Preventing Alert Fatigue: Only 'HIGH' and 'CRITICAL' tasks trigger automatic
       escalation to district operations management. Routine low-priority tasks (e.g.,
       storage pouch replacement) do not interrupt clinical leadership.
    3. Idempotent Escalation Levels: Escalation level 0 -> 1 prevents cyclic or duplicate
       notifications while immutably recording the breach in the regulatory audit trail.
    
    Returns:
        dict: Summary of active tasks scanned, count of newly escalated tasks, and affected IDs.
    """
    now = datetime.datetime.utcnow()
    
    # Query only unresolved tasks (active clinical operational pipeline)
    tasks = db.query(FollowUpTask).filter(
        FollowUpTask.status.in_(["OPEN", "IN_PROGRESS", "BLOCKED"])
    ).all()

    escalated_count = 0
    escalated_ids = []

    for task in tasks:
        is_overdue = task.due_date < now
        
        # Clinical Rule: Only escalate if overdue and not previously escalated (Level 0)
        # Prevents redundant re-escalation loops while ensuring timely intervention
        if is_overdue and task.escalation_level == 0:
            if task.priority in ["HIGH", "CRITICAL"]:
                # Transition status to ESCALATED and re-route ownership to Operations Manager
                task.status = "ESCALATED"
                task.escalation_level = 1
                task.assigned_to = "Operations Manager (Escalated)"
                escalated_count += 1
                escalated_ids.append(task.task_id)

                # Regulatory Audit: Document SLA violation and reassignment for clinical safety compliance
                log_audit(
                    db=db,
                    action="AUTO_ESCALATE_TASK",
                    entity="FollowUpTask",
                    entity_id=task.task_id,
                    details=(
                        f"Task {task.task_id} ({task.issue_type}) priority {task.priority} "
                        f"exceeded due date {task.due_date}. Auto-escalated to Operations Manager."
                    )
                )
    
    db.commit()
    return {
        "checked_at": now.isoformat(),
        "total_active_tasks": len(tasks),
        "escalated_count": escalated_count,
        "escalated_task_ids": escalated_ids
    }
