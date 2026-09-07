import datetime
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Recommendation, ReviewDecision, DeviceReturn, Device, User
)
from app.schemas import (
    ConfirmRecommendationInput, OverrideRecommendationInput, ReviewDecisionResponse
)
from app.auth import get_current_user, require_roles
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/recommendations", tags=["Human-in-the-Loop Review"])

@router.get("/pending")
def get_pending_reviews(db: Session = Depends(get_db)):
    recs = db.query(Recommendation).filter(Recommendation.status == "PENDING").all()
    res = []
    for r in recs:
        ret = db.query(DeviceReturn).filter(DeviceReturn.return_id == r.return_id).first()
        dev = db.query(Device).filter(Device.device_id == ret.device_id).first() if ret else None
        res.append({
            "recommendation_id": r.recommendation_id,
            "return_id": r.return_id,
            "device_id": ret.device_id if ret else "Unknown",
            "device_type": dev.device_type if dev else "Unknown Device",
            "rule_id": r.rule_id,
            "recommendation": r.recommendation,
            "risk_level": r.risk_level,
            "status": r.status,
            "rule_name": r.rule.rule_name if r.rule else "Safety Policy",
            "required_human_action": r.rule.required_human_action if r.rule else "Authorised sign-off",
            "evidence_description": r.rule.evidence_description if r.rule else "Checklist findings require human verification."
        })
    return res

@router.post("/{recommendation_id}/confirm", response_model=ReviewDecisionResponse)
def confirm_recommendation(
    recommendation_id: str,
    confirm_in: ConfirmRecommendationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["clinician", "ops_manager", "admin"]))
):
    rec = db.query(Recommendation).filter(Recommendation.recommendation_id == recommendation_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation '{recommendation_id}' not found.")
    
    if rec.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Recommendation '{recommendation_id}' is already '{rec.status}'.")

    rec.status = "CONFIRMED"
    
    decision_id = f"DEC-{uuid.uuid4().hex[:8].upper()}"
    decision = ReviewDecision(
        decision_id=decision_id,
        recommendation_id=recommendation_id,
        reviewer_id=current_user.id,
        decision="CONFIRM",
        override_reason=confirm_in.notes or "Clinician confirmed system safety recommendation.",
        timestamp=datetime.datetime.utcnow()
    )
    db.add(decision)

    # Update return & device status based on confirmed recommendation
    ret = db.query(DeviceReturn).filter(DeviceReturn.return_id == rec.return_id).first()
    if ret:
        device = db.query(Device).filter(Device.device_id == ret.device_id).first()
        # If all recommendations for this return are handled
        other_pending = db.query(Recommendation).filter(
            Recommendation.return_id == ret.return_id,
            Recommendation.status == "PENDING",
            Recommendation.recommendation_id != recommendation_id
        ).count()

        if other_pending == 0:
            if rec.risk_level in ["HIGH", "CRITICAL"]:
                ret.status = "QUARANTINED"
                if device:
                    device.status = "QUARANTINED"
            elif rec.risk_level == "LOW":
                ret.status = "COMPLETED"
                if device:
                    device.status = "READY_FOR_REISSUE"

    db.commit()
    db.refresh(decision)

    log_audit(
        db=db,
        action="CONFIRM_RECOMMENDATION",
        entity="Recommendation",
        entity_id=recommendation_id,
        user=current_user,
        details=f"Clinician '{current_user.name}' CONFIRMED recommendation '{recommendation_id}'. Risk level: '{rec.risk_level}'."
    )
    return decision

@router.post("/{recommendation_id}/override", response_model=ReviewDecisionResponse)
def override_recommendation(
    recommendation_id: str,
    override_in: OverrideRecommendationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["clinician", "ops_manager", "admin"]))
):
    # Edge case 9 enforcement: Compulsory non-empty override reason
    if not override_in.override_reason or not override_in.override_reason.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Edge Case Validation Error: Override rejected! Healthcare safety policy requires a non-empty, detailed justification reason for overriding system recommendations."
        )

    rec = db.query(Recommendation).filter(Recommendation.recommendation_id == recommendation_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation '{recommendation_id}' not found.")

    if rec.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Recommendation '{recommendation_id}' is already '{rec.status}'.")

    rec.status = "OVERRIDDEN"

    decision_id = f"DEC-{uuid.uuid4().hex[:8].upper()}"
    decision = ReviewDecision(
        decision_id=decision_id,
        recommendation_id=recommendation_id,
        reviewer_id=current_user.id,
        decision="OVERRIDE",
        override_reason=override_in.override_reason.strip(),
        timestamp=datetime.datetime.utcnow()
    )
    db.add(decision)

    ret = db.query(DeviceReturn).filter(DeviceReturn.return_id == rec.return_id).first()
    if ret:
        device = db.query(Device).filter(Device.device_id == ret.device_id).first()
        ret.status = "COMPLETED"
        if device:
            device.status = "READY_FOR_REISSUE"

    db.commit()
    db.refresh(decision)

    log_audit(
        db=db,
        action="OVERRIDE_RECOMMENDATION",
        entity="Recommendation",
        entity_id=recommendation_id,
        user=current_user,
        details=f"Clinician '{current_user.name}' OVERRODE recommendation '{recommendation_id}'. Override Reason: '{override_in.override_reason.strip()}'."
    )
    return decision
