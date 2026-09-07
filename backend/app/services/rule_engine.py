import datetime
import uuid
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from app.models import (
    DeviceReturn, ReturnedAccessory, ConditionCheck,
    PatientAcknowledgement, CleaningRecord, Rule,
    Recommendation, FollowUpTask, Device, AccessoryCatalog
)
from app.services.audit_service import log_audit

DEFAULT_RULES = [
    {
        "rule_id": "RULE-01",
        "rule_name": "Accessory Reconciliation Rule",
        "condition_expr": "returned_quantity < expected_quantity",
        "recommendation": "Missing accessory detected. Quarantine accessory kit and issue replacement request.",
        "risk_level": "HIGH",
        "required_human_action": "Authorised staff must verify missing items and assign replacement follow-up task.",
        "evidence_description": "One or more expected accessories were not returned with the device."
    },
    {
        "rule_id": "RULE-02",
        "rule_name": "Major Damage Inspection Rule",
        "condition_expr": "exterior == 'Major damage' or screen in ['Cracked', 'Not functioning'] or power == 'Does not power on' or sensors == 'Damaged'",
        "recommendation": "Major hardware damage detected. Quarantine device and send to technical service.",
        "risk_level": "HIGH",
        "required_human_action": "Authorised reviewer must confirm quarantine status and dispatch maintenance ticket.",
        "evidence_description": "Condition assessment identified physical, screen, power, or sensor defect."
    },
    {
        "rule_id": "RULE-03",
        "rule_name": "Cleaning & Sanitisation Rule",
        "condition_expr": "cleaning_status != 'COMPLETED'",
        "recommendation": "Cleaning verification required before re-issue. Device is not sanitised for patient use.",
        "risk_level": "MEDIUM",
        "required_human_action": "Field staff or sanitisation technician must complete sanitisation protocol and confirm.",
        "evidence_description": "Device cleaning status is pending, failed, or uncertain."
    },
    {
        "rule_id": "RULE-04",
        "rule_name": "Patient Acknowledgement Rule",
        "condition_expr": "acknowledgement_status == 'MISSING'",
        "recommendation": "Patient return acknowledgement missing. Conduct verification follow-up.",
        "risk_level": "MEDIUM",
        "required_human_action": "Staff member must obtain verbal or written patient acknowledgement form.",
        "evidence_description": "No patient signature or acknowledgement form attached to return record."
    },
    {
        "rule_id": "RULE-05",
        "rule_name": "Compound Multi-Risk Rule",
        "condition_expr": "total_flagged_issues >= 2",
        "recommendation": "Multiple risk factors present simultaneously. Elevate overall risk to HIGH/CRITICAL.",
        "risk_level": "CRITICAL",
        "required_human_action": "Operations Manager & Clinician review required before clearing device.",
        "evidence_description": "Multiple independent return checklist failures recorded."
    },
    {
        "rule_id": "RULE-06",
        "rule_name": "Safety Precaution Re-issue Blocker",
        "condition_expr": "unresolved_safety_tasks > 0 or device_status != 'READY_FOR_REISSUE'",
        "recommendation": "Do not re-issue device until all safety and physical inspection tasks are resolved.",
        "risk_level": "HIGH",
        "required_human_action": "Review open follow-up tasks and obtain explicit authorised clearance.",
        "evidence_description": "Device has active safety follow-up items or pending physical verification."
    },
    {
        "rule_id": "RULE-07",
        "rule_name": "Mandatory Human-in-the-Loop Confirmation",
        "condition_expr": "risk_level in ['HIGH', 'CRITICAL'] or has_recommendation == True",
        "recommendation": "Authorised staff review strictly required. Final state cannot be determined autonomously.",
        "risk_level": "CRITICAL",
        "required_human_action": "Clinician / Authorised reviewer must explicitly CONFIRM or OVERRIDE (with compulsory reason).",
        "evidence_description": "Healthcare safety protocol prohibits autonomous approval of high-impact device returns."
    }
]

def seed_rules_if_empty(db: Session):
    for r_data in DEFAULT_RULES:
        existing = db.query(Rule).filter(Rule.rule_id == r_data["rule_id"]).first()
        if not existing:
            rule_obj = Rule(**r_data)
            db.add(rule_obj)
    db.commit()

def evaluate_device_return(db: Session, return_id: str) -> Dict:
    """
    Core Rule Engine logic:
    Reads device return, accessories, condition check, patient ack, and cleaning record.
    Evaluates transparent rules, generates explainable recommendations, assigns overall risk score,
    creates necessary follow-up tasks, and updates device/return status.
    """
    seed_rules_if_empty(db)
    
    device_return = db.query(DeviceReturn).filter(DeviceReturn.return_id == return_id).first()
    if not device_return:
        raise ValueError(f"Return record {return_id} not found.")

    device = db.query(Device).filter(Device.device_id == device_return.device_id).first()
    
    # Clean up existing pending recommendations for re-evaluation
    db.query(Recommendation).filter(
        Recommendation.return_id == return_id,
        Recommendation.status == "PENDING"
    ).delete(synchronize_session=False)
    db.commit()

    ret_accs = db.query(ReturnedAccessory).filter(ReturnedAccessory.return_id == return_id).all()
    cond = db.query(ConditionCheck).filter(ConditionCheck.return_id == return_id).first()
    ack = db.query(PatientAcknowledgement).filter(PatientAcknowledgement.return_id == return_id).first()
    cleaning = db.query(CleaningRecord).filter(CleaningRecord.return_id == return_id).first()

    flagged_issues = []
    generated_recs = []
    created_tasks = []

    # 1. Evaluate Accessory Reconciliation
    missing_acc_names = []
    has_critical_missing = False
    for item in ret_accs:
        acc_catalog = db.query(AccessoryCatalog).filter(AccessoryCatalog.accessory_id == item.accessory_id).first()
        acc_name = acc_catalog.accessory_name if acc_catalog else item.accessory_id
        is_critical = (acc_catalog.criticality == "CRITICAL") if acc_catalog else False

        if item.returned_quantity < item.expected_quantity or item.condition == "MISSING":
            missing_count = item.expected_quantity - item.returned_quantity
            missing_acc_names.append(f"{acc_name} (Missing {missing_count})")
            if is_critical:
                has_critical_missing = True
        elif item.condition == "DAMAGED":
            missing_acc_names.append(f"{acc_name} (Damaged)")
        elif item.returned_quantity > item.expected_quantity:
            missing_acc_names.append(f"{acc_name} (Excess quantity: {item.returned_quantity} vs expected {item.expected_quantity})")

    if missing_acc_names:
        flagged_issues.append("Missing/Damaged Accessories")
        rule_obj = db.query(Rule).filter(Rule.rule_id == "RULE-01").first()
        risk = "HIGH" if has_critical_missing else "MEDIUM"
        rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
        detail_msg = f"Missing accessories detected: {', '.join(missing_acc_names)}. Replacement required."
        
        rec = Recommendation(
            recommendation_id=rec_id,
            return_id=return_id,
            rule_id="RULE-01",
            recommendation=detail_msg,
            risk_level=risk,
            status="PENDING"
        )
        db.add(rec)
        generated_recs.append(rec)

        # Create Follow-up Task
        task_id = f"TSK-{uuid.uuid4().hex[:8].upper()}"
        task = FollowUpTask(
            task_id=task_id,
            return_id=return_id,
            device_id=device_return.device_id,
            issue_type="Missing Accessory",
            description=detail_msg,
            priority=risk,
            assigned_to="Inventory Lead",
            due_date=datetime.datetime.utcnow() + datetime.timedelta(hours=24 if risk == "HIGH" else 48),
            status="OPEN"
        )
        db.add(task)
        created_tasks.append(task)

    # 2. Evaluate Condition Checklist
    if cond:
        is_major_damage = (
            cond.exterior == "Major damage" or
            cond.screen in ["Cracked", "Not functioning"] or
            cond.power in ["Does not power on", "Charging issue"] or
            cond.sensors in ["Damaged"] or
            cond.ports in ["Damaged"]
        )
        if is_major_damage:
            flagged_issues.append("Major Physical/Hardware Damage")
            rule_obj = db.query(Rule).filter(Rule.rule_id == "RULE-02").first()
            rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
            damage_details = f"Device condition failure: Exterior ({cond.exterior}), Screen ({cond.screen}), Power ({cond.power}), Sensors ({cond.sensors}). Technical inspection required."
            
            rec = Recommendation(
                recommendation_id=rec_id,
                return_id=return_id,
                rule_id="RULE-02",
                recommendation=damage_details,
                risk_level="HIGH",
                status="PENDING"
            )
            db.add(rec)
            generated_recs.append(rec)

            task_id = f"TSK-{uuid.uuid4().hex[:8].upper()}"
            task = FollowUpTask(
                task_id=task_id,
                return_id=return_id,
                device_id=device_return.device_id,
                issue_type="Major Damage - Technical Service",
                description=damage_details,
                priority="HIGH",
                assigned_to="Biomedical Technician",
                due_date=datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                status="OPEN"
            )
            db.add(task)
            created_tasks.append(task)

    # 3. Evaluate Cleaning Status
    if cleaning and cleaning.status != "COMPLETED":
        flagged_issues.append("Cleaning Incomplete")
        rule_obj = db.query(Rule).filter(Rule.rule_id == "RULE-03").first()
        rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
        clean_msg = f"Cleaning status is '{cleaning.status}'. Decontamination protocol must be completed prior to reissue."
        
        rec = Recommendation(
            recommendation_id=rec_id,
            return_id=return_id,
            rule_id="RULE-03",
            recommendation=clean_msg,
            risk_level="MEDIUM",
            status="PENDING"
        )
        db.add(rec)
        generated_recs.append(rec)

        task_id = f"TSK-{uuid.uuid4().hex[:8].upper()}"
        task = FollowUpTask(
            task_id=task_id,
            return_id=return_id,
            device_id=device_return.device_id,
            issue_type="Cleaning Verification Required",
            description=clean_msg,
            priority="MEDIUM",
            assigned_to="Sanitisation Lead",
            due_date=datetime.datetime.utcnow() + datetime.timedelta(hours=12),
            status="OPEN"
        )
        db.add(task)
        created_tasks.append(task)

    # 4. Evaluate Patient Acknowledgement
    if ack and ack.status == "MISSING":
        flagged_issues.append("Patient Acknowledgement Missing")
        rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
        ack_msg = "Patient acknowledgement form is missing. Follow up with patient or field officer."
        
        rec = Recommendation(
            recommendation_id=rec_id,
            return_id=return_id,
            rule_id="RULE-04",
            recommendation=ack_msg,
            risk_level="MEDIUM",
            status="PENDING"
        )
        db.add(rec)
        generated_recs.append(rec)

        task_id = f"TSK-{uuid.uuid4().hex[:8].upper()}"
        task = FollowUpTask(
            task_id=task_id,
            return_id=return_id,
            device_id=device_return.device_id,
            issue_type="Patient Acknowledgement Missing",
            description=ack_msg,
            priority="MEDIUM",
            assigned_to="Field Care Coordinator",
            due_date=datetime.datetime.utcnow() + datetime.timedelta(hours=48),
            status="OPEN"
        )
        db.add(task)
        created_tasks.append(task)

    # 5. Compound Multi-Risk Assessment
    if len(flagged_issues) >= 2:
        rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
        compound_msg = f"Compound Risk Warning: {len(flagged_issues)} checklist failures ({', '.join(flagged_issues)}). Priority elevated to CRITICAL."
        rec = Recommendation(
            recommendation_id=rec_id,
            return_id=return_id,
            rule_id="RULE-05",
            recommendation=compound_msg,
            risk_level="CRITICAL",
            status="PENDING"
        )
        db.add(rec)
        generated_recs.append(rec)

    # 6 & 7. Safety Re-issue Blocker & HITL Review Requirement
    overall_risk = "LOW"
    risk_levels = [r.risk_level for r in generated_recs]
    if "CRITICAL" in risk_levels or len(flagged_issues) >= 2:
        overall_risk = "CRITICAL"
    elif "HIGH" in risk_levels or has_critical_missing:
        overall_risk = "HIGH"
    elif "MEDIUM" in risk_levels:
        overall_risk = "MEDIUM"

    # Always generate Rule 7 HITL requirement if any issues present or for safety confirmation
    rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
    hitl_msg = f"Safety Protocol: Authorised staff review required. Overall return risk: {overall_risk}. Auto-release blocked."
    rec_hitl = Recommendation(
        recommendation_id=rec_id,
        return_id=return_id,
        rule_id="RULE-07",
        recommendation=hitl_msg,
        risk_level=overall_risk if overall_risk != "LOW" else "LOW",
        status="PENDING"
    )
    db.add(rec_hitl)
    generated_recs.append(rec_hitl)

    # Update Return Status and Device Status
    device_return.overall_risk_level = overall_risk
    if overall_risk in ["HIGH", "CRITICAL"]:
        device_return.status = "QUARANTINED"
        device.status = "QUARANTINED"
    elif overall_risk == "MEDIUM":
        device_return.status = "INSPECTION_REQUIRED"
        device.status = "INSPECTION_REQUIRED"
    else:
        device_return.status = "IN_REVIEW"
        device.status = "RETURNED"

    db.commit()

    log_audit(
        db=db,
        action="EVALUATE_RETURN",
        entity="DeviceReturn",
        entity_id=return_id,
        details=f"Evaluated return. Flagged issues: {len(flagged_issues)}. Risk: {overall_risk}. Recommendations generated: {len(generated_recs)}"
    )

    return {
        "return_id": return_id,
        "overall_risk_level": overall_risk,
        "flagged_issues": flagged_issues,
        "recommendations": generated_recs,
        "tasks_created": created_tasks
    }
