import sys
import os
import uuid
import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.database import SessionLocal, engine, Base
from app.models import FollowUpTask, Device
from app.services.escalation_service import check_and_escalate_tasks

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()

def test_tasks_before_due_date_not_escalated(setup_db):
    """Verify tasks whose due date is in the future are not escalated."""
    db = setup_db
    uid = uuid.uuid4().hex[:6]
    dev = Device(device_id=f"DEV-ESC-{uid}", device_type="Nebulizer", serial_number=f"SN-ESC-{uid}", status="AVAILABLE")
    db.add(dev)

    future_due = datetime.datetime.utcnow() + datetime.timedelta(hours=48)
    task = FollowUpTask(
        task_id=f"TASK-FUT-{uid}",
        device_id=dev.device_id,
        issue_type="PHYSICAL_DAMAGE",
        description="Minor casing scratch",
        priority="HIGH",
        due_date=future_due,
        status="OPEN",
        escalation_level=0
    )
    db.add(task)
    db.commit()

    result = check_and_escalate_tasks(db)
    db.refresh(task)
    assert task.status == "OPEN"
    assert task.escalation_level == 0
    assert task.task_id not in result["escalated_task_ids"]

def test_overdue_high_priority_task_auto_escalated(setup_db):
    """Verify overdue HIGH and CRITICAL priority tasks are automatically escalated."""
    db = setup_db
    uid = uuid.uuid4().hex[:6]
    dev = Device(device_id=f"DEV-ESC2-{uid}", device_type="Ventilator", serial_number=f"SN-ESC2-{uid}", status="QUARANTINED")
    db.add(dev)

    past_due = datetime.datetime.utcnow() - datetime.timedelta(hours=12)
    task_crit = FollowUpTask(
        task_id=f"TASK-CRIT-{uid}",
        device_id=dev.device_id,
        issue_type="BIOHAZARD",
        description="Contaminated fluid manifold requires HazMat disposal",
        priority="CRITICAL",
        due_date=past_due,
        status="OPEN",
        escalation_level=0
    )
    db.add(task_crit)
    db.commit()

    result = check_and_escalate_tasks(db)
    db.refresh(task_crit)
    assert task_crit.status == "ESCALATED"
    assert task_crit.escalation_level == 1
    assert "Operations Manager" in task_crit.assigned_to
    assert task_crit.task_id in result["escalated_task_ids"]

def test_prevent_duplicate_escalation(setup_db):
    """Verify tasks that were already escalated (level=1) are not escalated again."""
    db = setup_db
    uid = uuid.uuid4().hex[:6]
    dev = Device(device_id=f"DEV-ESC3-{uid}", device_type="CPAP", serial_number=f"SN-ESC3-{uid}", status="QUARANTINED")
    db.add(dev)

    past_due = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    task = FollowUpTask(
        task_id=f"TASK-DUP-{uid}",
        device_id=dev.device_id,
        issue_type="MISSING_CRITICAL",
        description="Missing oxygen hose",
        priority="HIGH",
        due_date=past_due,
        status="ESCALATED",
        escalation_level=1,
        assigned_to="Operations Manager"
    )
    db.add(task)
    db.commit()

    result = check_and_escalate_tasks(db)
    db.refresh(task)
    assert task.task_id not in result["escalated_task_ids"]

def test_resolved_tasks_never_escalated(setup_db):
    """Verify resolved and closed tasks are ignored by the escalation scanner even if overdue."""
    db = setup_db
    uid = uuid.uuid4().hex[:6]
    dev = Device(device_id=f"DEV-ESC4-{uid}", device_type="ECG", serial_number=f"SN-ESC4-{uid}", status="AVAILABLE")
    db.add(dev)

    past_due = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    task_res = FollowUpTask(
        task_id=f"TASK-RES-{uid}",
        device_id=dev.device_id,
        issue_type="BATTERY_DEPLETED",
        description="Battery cell replaced",
        priority="HIGH",
        due_date=past_due,
        status="RESOLVED",
        escalation_level=0,
        resolution="Replaced battery with new pack."
    )
    db.add(task_res)
    db.commit()

    result = check_and_escalate_tasks(db)
    db.refresh(task_res)
    assert task_res.status == "RESOLVED"
    assert task_res.escalation_level == 0
    assert task_res.task_id not in result["escalated_task_ids"]
