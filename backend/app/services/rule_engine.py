"""
Rule Engine & Clinical Decision Support Service
===============================================
This module implements the core deterministic clinical safety rule engine for
evaluating returned portable medical loan devices in rural healthcare networks.

Clinical Rationale & Regulatory Compliance:
-------------------------------------------
1. Patient Safety First: Medical devices (e.g. pulse oximeters, ECG monitors,
   infusion pumps, nebulizers) operate under stringent safety standards. A missing
   sensor probe, cracked casing, or incomplete decontamination directly jeopardizes
   patient diagnostic accuracy and infection control.
2. Differentiated Risk Thresholds:
   - Critical Accessories (RULE-01): Diagnostic probes, patient leads, and power units
     are mandatory for device function. Missing items immediately quarantine the kit.
   - Standard Accessories (RULE-01B): Documentation, manuals, and carrying cases are
     non-diagnostic. Flagging them as routine restock prevents unneeded device shortages.
3. Mechanical vs Superficial Wear (RULE-02 vs RULE-02B):
   - Superficial cosmetic scuffs occur routinely in rural field visits and do not
     impair electrical isolation or sensor accuracy.
   - Casing breaches, power failures, or sensor faults demand immediate quarantine.
4. Infection Prevention & Decontamination (RULE-03):
   - Devices returned from patient homes carry microbial cross-contamination risks.
   - Unverified sanitisation blocks reissue until cleared by sanitisation staff.
5. Human-in-the-Loop (HITL) Governance (RULE-07):
   - Algorithms never autonomously clear high-risk medical devices for reissue.
   - Clinicians or inventory leads retain ultimate decision authority with mandatory
     override audit justification.
"""

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
        "rule_name": "Critical Accessory Reconciliation Rule",
        "condition_expr": "returned_quantity < expected_quantity and criticality == 'CRITICAL'",
        "recommendation": "Missing critical accessory detected. Quarantine accessory kit and issue urgent replacement request.",
        "risk_level": "HIGH",
        "required_human_action": "Inventory Lead must initiate urgent 24h restock order. Device kit must remain quarantined.",
        "evidence_description": "Critical diagnostic sensor probe, cable harness, or power charger missing or damaged."
    },
    {
        "rule_id": "RULE-01B",
        "rule_name": "Standard Accessory Restock Advisory",
        "condition_expr": "returned_quantity < expected_quantity and criticality == 'STANDARD'",
        "recommendation": "Standard non-critical accessory missing. Issue routine 72h restock advisory. No device quarantine required.",
        "risk_level": "LOW",
        "required_human_action": "Field staff or inventory clerk restock standard accessory item within 72 hours.",
        "evidence_description": "Standard documentation, pouch, or non-diagnostic consumable accessory missing."
    },
    {
        "rule_id": "RULE-02",
        "rule_name": "Major Hardware Damage Escalation Rule",
        "condition_expr": "exterior == 'Major damage' or screen in ['Cracked', 'Not functioning'] or power in ['Does not power on', 'Charging issue'] or sensors == 'Damaged' or ports == 'Damaged'",
        "recommendation": "Major hardware damage detected. Quarantine device and dispatch technical service order.",
        "risk_level": "HIGH",
        "required_human_action": "Authorised reviewer must confirm quarantine status and dispatch biomedical repair ticket.",
        "evidence_description": "Condition assessment identified physical casing breach, display failure, power malfunction, or damaged sensors/ports."
    },
    {
        "rule_id": "RULE-02B",
        "rule_name": "Minor Cosmetic Wear Clearance Rule",
        "condition_expr": "exterior == 'Minor cosmetic wear' and screen == 'Good' and power == 'Normal' and sensors == 'Functional'",
        "recommendation": "Minor cosmetic wear (surface scuffs/scratches) recorded. Non-escalating routine observation. Device safe for clinical clearance.",
        "risk_level": "LOW",
        "required_human_action": "Log cosmetic condition observation in inventory records. Routine clinical release permitted.",
        "evidence_description": "Superficial exterior scuffs or scratches with intact mechanical casing and operational sensors."
    },
    {
        "rule_id": "RULE-02C",
        "rule_name": "Minor Hardware Degradation Inspection Rule",
        "condition_expr": "exterior == 'Minor damage' or buttons == 'Partially functional' or battery == 'Weak'",
        "recommendation": "Minor hardware degradation detected. Routine biomedical inspection scheduled prior to re-issue.",
        "risk_level": "MEDIUM",
        "required_human_action": "Biomedical technician conduct routine inspection or battery replacement within 48h.",
        "evidence_description": "Minor casing damage, partially responsive buttons, or degraded battery capacity."
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
        else:
            existing.rule_name = r_data["rule_name"]
            existing.condition_expr = r_data["condition_expr"]
            existing.recommendation = r_data["recommendation"]
            existing.risk_level = r_data["risk_level"]
            existing.required_human_action = r_data["required_human_action"]
            existing.evidence_description = r_data["evidence_description"]
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

    # 1. Evaluate Accessory Reconciliation: Critical vs Standard
    critical_missing_names = []
    standard_missing_names = []
    excess_acc_names = []

    for item in ret_accs:
        acc_catalog = db.query(AccessoryCatalog).filter(AccessoryCatalog.accessory_id == item.accessory_id).first()
        acc_name = acc_catalog.accessory_name if acc_catalog else item.accessory_id
        is_critical = (acc_catalog.criticality == "CRITICAL") if acc_catalog else False

        if item.returned_quantity < item.expected_quantity or item.condition == "MISSING":
            missing_count = item.expected_quantity - item.returned_quantity
            item_desc = f"{acc_name} (Missing {missing_count})"
            if is_critical:
                critical_missing_names.append(item_desc)
            else:
                standard_missing_names.append(item_desc)
        elif item.condition == "DAMAGED":
            item_desc = f"{acc_name} (Damaged)"
            if is_critical:
                critical_missing_names.append(item_desc)
            else:
                standard_missing_names.append(item_desc)
        elif item.returned_quantity > item.expected_quantity:
            excess_acc_names.append(f"{acc_name} (Excess: {item.returned_quantity} vs expected {item.expected_quantity})")

    # Critical / High-Value Missing Accessory Escalation (RULE-01)
    if critical_missing_names:
        flagged_issues.append("Missing Critical/High-Value Accessories")
        risk = "CRITICAL" if len(critical_missing_names) >= 2 else "HIGH"
        rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
        detail_msg = f"Missing critical accessories detected: {', '.join(critical_missing_names)}. Kit quarantined. Immediate replacement required."
        
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

        task_id = f"TSK-{uuid.uuid4().hex[:8].upper()}"
        task = FollowUpTask(
            task_id=task_id,
            return_id=return_id,
            device_id=device_return.device_id,
            issue_type="Missing Critical Accessory",
            description=detail_msg,
            priority="HIGH",
            assigned_to="Inventory Lead",
            due_date=datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            status="OPEN"
        )
        db.add(task)
        created_tasks.append(task)

    # Standard Accessory Restock Advisory (RULE-01B) - Non-escalating
    if standard_missing_names:
        rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
        detail_msg = f"Non-critical accessory missing/damaged: {', '.join(standard_missing_names)}. Routine 72h restock advisory."
        
        rec = Recommendation(
            recommendation_id=rec_id,
            return_id=return_id,
            rule_id="RULE-01B",
            recommendation=detail_msg,
            risk_level="LOW",
            status="PENDING"
        )
        db.add(rec)
        generated_recs.append(rec)

        task_id = f"TSK-{uuid.uuid4().hex[:8].upper()}"
        task = FollowUpTask(
            task_id=task_id,
            return_id=return_id,
            device_id=device_return.device_id,
            issue_type="Routine Accessory Restock",
            description=detail_msg,
            priority="LOW",
            assigned_to="Inventory Clerk",
            due_date=datetime.datetime.utcnow() + datetime.timedelta(hours=72),
            status="OPEN"
        )
        db.add(task)
        created_tasks.append(task)

    # Excess accessories audit note
    if excess_acc_names:
        task_id = f"TSK-{uuid.uuid4().hex[:8].upper()}"
        task = FollowUpTask(
            task_id=task_id,
            return_id=return_id,
            device_id=device_return.device_id,
            issue_type="Excess Accessory Inventory Audit",
            description=f"Returned excess items: {', '.join(excess_acc_names)}. Log and return to stock.",
            priority="LOW",
            assigned_to="Inventory Clerk",
            due_date=datetime.datetime.utcnow() + datetime.timedelta(hours=72),
            status="OPEN"
        )
        db.add(task)
        created_tasks.append(task)

    # 2. Evaluate Condition Checklist: Major Damage vs Minor Cosmetic Wear vs Minor Degradation
    if cond:
        is_major_damage = (
            cond.exterior == "Major damage" or
            cond.screen in ["Cracked", "Not functioning"] or
            cond.power in ["Does not power on", "Charging issue"] or
            cond.sensors in ["Damaged"] or
            cond.ports in ["Damaged"]
        )
        is_minor_damage = (
            cond.exterior == "Minor damage" or
            cond.buttons in ["Partially functional", "Not functional"] or
            cond.battery in ["Weak", "Unknown"]
        )
        is_minor_cosmetic = (
            cond.exterior == "Minor cosmetic wear" and
            not is_major_damage and
            not is_minor_damage
        )

        if is_major_damage:
            flagged_issues.append("Major Physical/Hardware Damage")
            rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
            damage_details = f"Major hardware damage detected: Exterior ({cond.exterior}), Screen ({cond.screen}), Power ({cond.power}), Sensors ({cond.sensors}), Ports ({cond.ports}). Device quarantined."
            
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

        elif is_minor_damage:
            flagged_issues.append("Minor Hardware Degradation")
            rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
            degradation_details = f"Minor hardware degradation: Exterior ({cond.exterior}), Buttons ({cond.buttons}), Battery ({cond.battery}). Routine maintenance required."
            
            rec = Recommendation(
                recommendation_id=rec_id,
                return_id=return_id,
                rule_id="RULE-02C",
                recommendation=degradation_details,
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
                issue_type="Minor Maintenance - Routine",
                description=degradation_details,
                priority="MEDIUM",
                assigned_to="Biomedical Technician (Routine)",
                due_date=datetime.datetime.utcnow() + datetime.timedelta(hours=48),
                status="OPEN"
            )
            db.add(task)
            created_tasks.append(task)

        elif is_minor_cosmetic:
            rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
            cosmetic_msg = "Minor cosmetic wear (surface scuffs/scratches) recorded on exterior casing. Non-escalating observation. Device safe for clinical clearance pending routine sanitisation."
            rec = Recommendation(
                recommendation_id=rec_id,
                return_id=return_id,
                rule_id="RULE-02B",
                recommendation=cosmetic_msg,
                risk_level="LOW",
                status="PENDING"
            )
            db.add(rec)
            generated_recs.append(rec)
            # Minor cosmetic wear does NOT escalate risk, does NOT add to flagged_issues, and does NOT quarantine the device.

    # 3. Evaluate Cleaning Status
    if cleaning and cleaning.status != "COMPLETED":
        flagged_issues.append("Cleaning Incomplete")
        clean_msg = f"Cleaning status is '{cleaning.status}'. Decontamination protocol must be completed prior to reissue."
        rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
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

    # 6 & 7. Overall Risk & HITL Review Requirement
    overall_risk = "LOW"
    risk_levels = [r.risk_level for r in generated_recs]
    if "CRITICAL" in risk_levels or len(flagged_issues) >= 2:
        overall_risk = "CRITICAL"
    elif "HIGH" in risk_levels or len(critical_missing_names) > 0:
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
        if device:
            device.status = "QUARANTINED"
    elif overall_risk == "MEDIUM":
        device_return.status = "INSPECTION_REQUIRED"
        if device:
            device.status = "INSPECTION_REQUIRED"
    else:
        device_return.status = "IN_REVIEW"
        if device:
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
