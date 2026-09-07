import datetime
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import FollowUpTask, Device, User
from app.schemas import FollowUpTaskResponse, FollowUpTaskCreate, FollowUpTaskUpdate
from app.auth import get_current_user
from app.services.escalation_service import check_and_escalate_tasks
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/follow-ups", tags=["Follow-up Tasks & Escalation"])

@router.get("", response_model=List[FollowUpTaskResponse])
def get_follow_up_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    escalated_only: Optional[bool] = False,
    db: Session = Depends(get_db)
):
    # First trigger auto-escalation check
    check_and_escalate_tasks(db)

    q = db.query(FollowUpTask)
    if status:
        q = q.filter(FollowUpTask.status == status)
    if priority:
        q = q.filter(FollowUpTask.priority == priority)
    if escalated_only:
        q = q.filter(FollowUpTask.escalation_level > 0)
    
    return q.order_by(FollowUpTask.due_date.asc()).all()

@router.post("", response_model=FollowUpTaskResponse, status_code=status.HTTP_201_CREATED)
def create_follow_up_task(
    task_in: FollowUpTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.device_id == task_in.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{task_in.device_id}' not found.")

    task_id = f"TSK-{uuid.uuid4().hex[:8].upper()}"
    due_date = datetime.datetime.utcnow() + datetime.timedelta(hours=task_in.due_hours)

    task = FollowUpTask(
        task_id=task_id,
        return_id=task_in.return_id,
        device_id=task_in.device_id,
        issue_type=task_in.issue_type,
        description=task_in.description,
        priority=task_in.priority,
        assigned_to=task_in.assigned_to or "Unassigned",
        created_date=datetime.datetime.utcnow(),
        due_date=due_date,
        status="OPEN",
        escalation_level=0
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    log_audit(db, action="CREATE_TASK", entity="FollowUpTask", entity_id=task_id, user=current_user, details=f"Task created: {task_in.issue_type}")
    return task

@router.patch("/{task_id}", response_model=FollowUpTaskResponse)
def update_follow_up_task(
    task_id: str,
    task_up: FollowUpTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(FollowUpTask).filter(FollowUpTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    if task_up.status:
        task.status = task_up.status
        if task_up.status in ["RESOLVED", "CLOSED"]:
            task.resolved_by = current_user.name if current_user else "Staff"
            task.resolved_date = datetime.datetime.utcnow()
    
    if task_up.assigned_to:
        task.assigned_to = task_up.assigned_to
    if task_up.due_date:
        task.due_date = task_up.due_date
    if task_up.resolution:
        task.resolution = task_up.resolution

    db.commit()
    db.refresh(task)

    log_audit(db, action="UPDATE_TASK", entity="FollowUpTask", entity_id=task_id, user=current_user, details=f"Updated status to '{task.status}', assigned to '{task.assigned_to}'")
    return task

@router.post("/{task_id}/escalate", response_model=FollowUpTaskResponse)
def escalate_task_manually(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(FollowUpTask).filter(FollowUpTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    task.escalation_level += 1
    task.status = "ESCALATED"
    task.assigned_to = "Operations Manager (Escalated)"
    db.commit()
    db.refresh(task)

    log_audit(db, action="MANUAL_ESCALATE_TASK", entity="FollowUpTask", entity_id=task_id, user=current_user, details=f"Escalated to level {task.escalation_level}")
    return task
