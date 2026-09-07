import datetime
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Device, DeviceReturn, ReturnedAccessory, ConditionCheck,
    PatientAcknowledgement, CleaningRecord, DeviceIssueRecord,
    DeviceAccessory, AccessoryCatalog, Recommendation, FollowUpTask, User
)
from app.schemas import (
    CreateReturnRequest, ReturnedAccessoriesBatchInput,
    ConditionCheckInput, PatientAckInput, CleaningInput
)
from app.auth import get_current_user
from app.services.rule_engine import evaluate_device_return
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/returns", tags=["Device Returns & Checklist"])

@router.post("", status_code=status.HTTP_201_CREATED)
def start_return(ret_in: CreateReturnRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Unknown device check
    device = db.query(Device).filter(Device.device_id == ret_in.device_id).first()
    if not device:
        raise HTTPException(
            status_code=404,
            detail=f"Edge Case Validation Error: Device ID '{ret_in.device_id}' does not exist in inventory."
        )

    # 2. Duplicate return check
    existing_active = db.query(DeviceReturn).filter(
        DeviceReturn.device_id == ret_in.device_id,
        DeviceReturn.status.in_(["RETURN_PENDING", "IN_REVIEW", "QUARANTINED"])
    ).first()
    if existing_active:
        raise HTTPException(
            status_code=400,
            detail=f"Edge Case Validation Error: Duplicate Return Attempt! Return '{existing_active.return_id}' is already in progress for device '{ret_in.device_id}'."
        )

    issue_id = ret_in.issue_id
    if not issue_id:
        active_issue = db.query(DeviceIssueRecord).filter(
            DeviceIssueRecord.device_id == ret_in.device_id,
            DeviceIssueRecord.status == "ISSUED"
        ).order_by(DeviceIssueRecord.issued_date.desc()).first()
        if active_issue:
            issue_id = active_issue.issue_id

    return_id = f"RET-{uuid.uuid4().hex[:8].upper()}"
    new_return = DeviceReturn(
        return_id=return_id,
        device_id=ret_in.device_id,
        issue_id=issue_id,
        returned_date=datetime.datetime.utcnow(),
        received_by=ret_in.received_by,
        status="RETURN_PENDING",
        overall_risk_level="LOW"
    )
    db.add(new_return)
    device.status = "RETURN_PENDING"
    if issue_id:
        iss_rec = db.query(DeviceIssueRecord).filter(DeviceIssueRecord.issue_id == issue_id).first()
        if iss_rec:
            iss_rec.status = "RETURNED"

    # Pre-populate expected accessories based on device accessories catalog
    expected_accs = db.query(DeviceAccessory).filter(DeviceAccessory.device_id == ret_in.device_id).all()
    for exp in expected_accs:
        ret_acc = ReturnedAccessory(
            return_id=return_id,
            accessory_id=exp.accessory_id,
            expected_quantity=exp.expected_quantity,
            returned_quantity=exp.expected_quantity,
            condition="PRESENT"
        )
        db.add(ret_acc)

    db.commit()
    db.refresh(new_return)

    log_audit(db, action="START_RETURN", entity="DeviceReturn", entity_id=return_id, user=current_user)
    return {"return_id": return_id, "device_id": ret_in.device_id, "status": "RETURN_PENDING", "message": "Return check-in initiated successfully."}

@router.get("")
def get_all_returns(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(DeviceReturn)
    if status:
        q = q.filter(DeviceReturn.status == status)
    returns = q.order_by(DeviceReturn.returned_date.desc()).all()
    
    res = []
    for r in returns:
        res.append({
            "return_id": r.return_id,
            "device_id": r.device_id,
            "issue_id": r.issue_id,
            "returned_date": r.returned_date,
            "received_by": r.received_by,
            "status": r.status,
            "overall_risk_level": r.overall_risk_level,
            "recommendations_count": len(r.recommendations),
            "open_tasks_count": len([t for t in r.follow_up_tasks if t.status not in ["RESOLVED", "CLOSED"]])
        })
    return res

@router.get("/{return_id}")
def get_return_details(return_id: str, db: Session = Depends(get_db)):
    ret = db.query(DeviceReturn).filter(DeviceReturn.return_id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail=f"Return '{return_id}' not found.")
    
    device = db.query(Device).filter(Device.device_id == ret.device_id).first()
    issue = db.query(DeviceIssueRecord).filter(DeviceIssueRecord.issue_id == ret.issue_id).first() if ret.issue_id else None

    # Accessory details join
    acc_list = []
    for item in ret.returned_accessories:
        cat = db.query(AccessoryCatalog).filter(AccessoryCatalog.accessory_id == item.accessory_id).first()
        acc_list.append({
            "id": item.id,
            "accessory_id": item.accessory_id,
            "accessory_name": cat.accessory_name if cat else item.accessory_id,
            "category": cat.category if cat else "Standard",
            "criticality": cat.criticality if cat else "STANDARD",
            "expected_quantity": item.expected_quantity,
            "returned_quantity": item.returned_quantity,
            "condition": item.condition
        })

    recs_list = []
    for r in ret.recommendations:
        recs_list.append({
            "recommendation_id": r.recommendation_id,
            "return_id": r.return_id,
            "rule_id": r.rule_id,
            "recommendation": r.recommendation,
            "risk_level": r.risk_level,
            "status": r.status,
            "rule_name": r.rule.rule_name if r.rule else "Safety Policy",
            "required_human_action": r.rule.required_human_action if r.rule else "Authorised confirmation required",
            "decisions": [
                {
                    "decision_id": d.decision_id,
                    "decision": d.decision,
                    "reviewer_id": d.reviewer_id,
                    "override_reason": d.override_reason,
                    "timestamp": d.timestamp
                } for d in r.decisions
            ]
        })

    tasks_list = []
    for t in ret.follow_up_tasks:
        tasks_list.append({
            "task_id": t.task_id,
            "return_id": t.return_id,
            "device_id": t.device_id,
            "issue_type": t.issue_type,
            "description": t.description,
            "priority": t.priority,
            "assigned_to": t.assigned_to,
            "created_date": t.created_date,
            "due_date": t.due_date,
            "status": t.status,
            "escalation_level": t.escalation_level,
            "resolution": t.resolution,
            "resolved_by": t.resolved_by,
            "resolved_date": t.resolved_date
        })

    cond_dict = None
    if ret.condition_check:
        c = ret.condition_check
        cond_dict = {
            "exterior": c.exterior, "screen": c.screen, "buttons": c.buttons,
            "power": c.power, "battery": c.battery, "ports": c.ports,
            "sensors": c.sensors, "physical_cleanliness": c.physical_cleanliness,
            "notes": c.notes, "photo_url": c.photo_url
        }

    ack_dict = None
    if ret.patient_ack:
        a = ret.patient_ack
        ack_dict = {
            "status": a.status, "method": a.method, "recorded_by": a.recorded_by,
            "timestamp": a.timestamp, "notes": a.notes
        }

    clean_dict = None
    if ret.cleaning_record:
        cl = ret.cleaning_record
        clean_dict = {
            "status": cl.status, "completed_by": cl.completed_by,
            "completed_at": cl.completed_at, "notes": cl.notes
        }

    return {
        "return_id": ret.return_id,
        "device_id": ret.device_id,
        "device": {"device_id": device.device_id, "device_type": device.device_type, "serial_number": device.serial_number, "status": device.status, "location": device.location} if device else None,
        "issue_id": ret.issue_id,
        "patient_reference": issue.patient_reference if issue else "Unknown",
        "returned_date": ret.returned_date,
        "received_by": ret.received_by,
        "status": ret.status,
        "overall_risk_level": ret.overall_risk_level,
        "returned_accessories": acc_list,
        "condition_check": cond_dict,
        "patient_ack": ack_dict,
        "cleaning_record": clean_dict,
        "recommendations": recs_list,
        "follow_up_tasks": tasks_list
    }

@router.post("/{return_id}/accessories")
def save_returned_accessories(return_id: str, batch: ReturnedAccessoriesBatchInput, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ret = db.query(DeviceReturn).filter(DeviceReturn.return_id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail=f"Return '{return_id}' not found.")

    for item in batch.items:
        existing = db.query(ReturnedAccessory).filter(
            ReturnedAccessory.return_id == return_id,
            ReturnedAccessory.accessory_id == item.accessory_id
        ).first()
        if existing:
            existing.expected_quantity = item.expected_quantity
            existing.returned_quantity = item.returned_quantity
            existing.condition = item.condition
        else:
            new_acc = ReturnedAccessory(
                return_id=return_id,
                accessory_id=item.accessory_id,
                expected_quantity=item.expected_quantity,
                returned_quantity=item.returned_quantity,
                condition=item.condition
            )
            db.add(new_acc)

    db.commit()
    log_audit(db, action="SAVE_ACCESSORIES", entity="DeviceReturn", entity_id=return_id, user=current_user)
    return {"message": "Returned accessories recorded successfully."}

@router.post("/{return_id}/condition")
def save_condition_check(return_id: str, cond_in: ConditionCheckInput, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ret = db.query(DeviceReturn).filter(DeviceReturn.return_id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail=f"Return '{return_id}' not found.")

    cond = db.query(ConditionCheck).filter(ConditionCheck.return_id == return_id).first()
    if cond:
        cond.exterior = cond_in.exterior
        cond.screen = cond_in.screen
        cond.buttons = cond_in.buttons
        cond.power = cond_in.power
        cond.battery = cond_in.battery
        cond.ports = cond_in.ports
        cond.sensors = cond_in.sensors
        cond.physical_cleanliness = cond_in.physical_cleanliness
        cond.notes = cond_in.notes
        cond.photo_url = cond_in.photo_url
    else:
        cond = ConditionCheck(
            return_id=return_id,
            exterior=cond_in.exterior,
            screen=cond_in.screen,
            buttons=cond_in.buttons,
            power=cond_in.power,
            battery=cond_in.battery,
            ports=cond_in.ports,
            sensors=cond_in.sensors,
            physical_cleanliness=cond_in.physical_cleanliness,
            notes=cond_in.notes,
            photo_url=cond_in.photo_url
        )
        db.add(cond)

    db.commit()
    log_audit(db, action="SAVE_CONDITION", entity="ConditionCheck", entity_id=return_id, user=current_user)
    return {"message": "Condition checklist recorded successfully."}

@router.post("/{return_id}/acknowledgement")
def save_patient_ack(return_id: str, ack_in: PatientAckInput, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ret = db.query(DeviceReturn).filter(DeviceReturn.return_id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail=f"Return '{return_id}' not found.")

    ack = db.query(PatientAcknowledgement).filter(PatientAcknowledgement.return_id == return_id).first()
    user_name = current_user.name if current_user else "Field Staff"
    if ack:
        ack.status = ack_in.status
        ack.method = ack_in.method
        ack.notes = ack_in.notes
        ack.recorded_by = user_name
        ack.timestamp = datetime.datetime.utcnow()
    else:
        ack = PatientAcknowledgement(
            return_id=return_id,
            status=ack_in.status,
            method=ack_in.method,
            notes=ack_in.notes,
            recorded_by=user_name,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(ack)

    db.commit()
    log_audit(db, action="SAVE_ACKNOWLEDGEMENT", entity="PatientAcknowledgement", entity_id=return_id, user=current_user)
    return {"message": "Patient acknowledgement recorded successfully."}

@router.post("/{return_id}/cleaning")
def save_cleaning_record(return_id: str, clean_in: CleaningInput, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ret = db.query(DeviceReturn).filter(DeviceReturn.return_id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail=f"Return '{return_id}' not found.")

    cl = db.query(CleaningRecord).filter(CleaningRecord.return_id == return_id).first()
    user_name = current_user.name if current_user else "Sanitisation Staff"
    if cl:
        cl.status = clean_in.status
        cl.notes = clean_in.notes
        cl.completed_by = user_name
        cl.completed_at = datetime.datetime.utcnow()
    else:
        cl = CleaningRecord(
            return_id=return_id,
            status=clean_in.status,
            completed_by=user_name,
            completed_at=datetime.datetime.utcnow(),
            notes=clean_in.notes
        )
        db.add(cl)

    db.commit()
    log_audit(db, action="SAVE_CLEANING", entity="CleaningRecord", entity_id=return_id, user=current_user)
    return {"message": "Cleaning record saved successfully."}

@router.post("/{return_id}/evaluate")
def run_evaluation(return_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        eval_result = evaluate_device_return(db, return_id)
        return eval_result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
