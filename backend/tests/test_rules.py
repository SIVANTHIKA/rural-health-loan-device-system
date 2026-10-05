import sys
import os
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.database import SessionLocal, engine, Base
from app.models import (
    Device, DeviceReturn, ReturnedAccessory, ConditionCheck,
    PatientAcknowledgement, CleaningRecord, Recommendation, FollowUpTask,
    AccessoryCatalog
)
from app.services.rule_engine import evaluate_device_return, seed_rules_if_empty

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_rules_if_empty(db)
    yield db
    db.close()

def _create_base_return(db, suffix=""):
    uid = f"{uuid.uuid4().hex[:6]}-{suffix}"
    dev_id = f"DEV-R-{uid}"
    ret_id = f"RET-R-{uid}"
    dev = Device(device_id=dev_id, device_type="Pulse Oximeter", serial_number=f"SN-{uid}", status="RETURN_PENDING")
    ret = DeviceReturn(return_id=ret_id, device_id=dev_id, received_by="Tester", status="RETURN_PENDING")
    db.add(dev)
    db.add(ret)
    db.commit()
    return dev_id, ret_id

def test_rule_engine_clean_return(setup_db):
    """Verify clean return produces LOW risk and zero flagged issues."""
    db = setup_db
    dev_id, ret_id = _create_base_return(db, "clean")
    db.add(ConditionCheck(return_id=ret_id, exterior="Good", screen="Good", power="Normal"))
    db.add(PatientAcknowledgement(return_id=ret_id, status="RECEIVED", recorded_by="Tester"))
    db.add(CleaningRecord(return_id=ret_id, status="COMPLETED", completed_by="Tester"))
    db.commit()

    result = evaluate_device_return(db, ret_id)
    assert result["overall_risk_level"] == "LOW"
    assert len(result["flagged_issues"]) == 0

def test_rule_01_critical_accessory_missing(setup_db):
    """RULE-01: Verify missing critical accessory triggers HIGH/CRITICAL risk and quarantine."""
    db = setup_db
    dev_id, ret_id = _create_base_return(db, "r01")
    cat = db.query(AccessoryCatalog).filter(AccessoryCatalog.accessory_id == "ACC-CAT-SPO2").first()
    if not cat:
        db.add(AccessoryCatalog(accessory_id="ACC-CAT-SPO2", accessory_name="SpO2 Sensor Probe", category="Sensor", criticality="CRITICAL"))
        db.commit()

    db.add(ReturnedAccessory(return_id=ret_id, accessory_id="ACC-CAT-SPO2", expected_quantity=1, returned_quantity=0, condition="MISSING"))
    db.add(ConditionCheck(return_id=ret_id, exterior="Good", screen="Good", power="Normal"))
    db.add(PatientAcknowledgement(return_id=ret_id, status="RECEIVED", recorded_by="Tester"))
    db.add(CleaningRecord(return_id=ret_id, status="COMPLETED", completed_by="Tester"))
    db.commit()

    result = evaluate_device_return(db, ret_id)
    assert result["overall_risk_level"] == "HIGH"
    assert "Missing Critical/High-Value Accessories" in result["flagged_issues"]
    rule_ids = [r.rule_id for r in result["recommendations"]]
    assert "RULE-01" in rule_ids

def test_rule_01b_standard_accessory_missing(setup_db):
    """RULE-01B: Verify missing standard accessory triggers non-escalating LOW risk."""
    db = setup_db
    dev_id, ret_id = _create_base_return(db, "r01b")
    cat = db.query(AccessoryCatalog).filter(AccessoryCatalog.accessory_id == "ACC-CAT-POUCH").first()
    if not cat:
        db.add(AccessoryCatalog(accessory_id="ACC-CAT-POUCH", accessory_name="Storage Pouch", category="Storage", criticality="STANDARD"))
        db.commit()

    db.add(ReturnedAccessory(return_id=ret_id, accessory_id="ACC-CAT-POUCH", expected_quantity=1, returned_quantity=0, condition="MISSING"))
    db.add(ConditionCheck(return_id=ret_id, exterior="Good", screen="Good", power="Normal"))
    db.add(PatientAcknowledgement(return_id=ret_id, status="RECEIVED", recorded_by="Tester"))
    db.add(CleaningRecord(return_id=ret_id, status="COMPLETED", completed_by="Tester"))
    db.commit()

    result = evaluate_device_return(db, ret_id)
    assert result["overall_risk_level"] == "LOW"
    assert len(result["flagged_issues"]) == 0
    rule_ids = [r.rule_id for r in result["recommendations"]]
    assert "RULE-01B" in rule_ids

def test_rule_02_major_hardware_damage(setup_db):
    """RULE-02: Verify major damage (cracked screen/exterior damage) triggers HIGH risk quarantine."""
    db = setup_db
    dev_id, ret_id = _create_base_return(db, "r02")
    db.add(ConditionCheck(return_id=ret_id, exterior="Major damage", screen="Cracked", power="Normal"))
    db.add(PatientAcknowledgement(return_id=ret_id, status="RECEIVED", recorded_by="Tester"))
    db.add(CleaningRecord(return_id=ret_id, status="COMPLETED", completed_by="Tester"))
    db.commit()

    result = evaluate_device_return(db, ret_id)
    assert result["overall_risk_level"] == "HIGH"
    assert "Major Physical/Hardware Damage" in result["flagged_issues"]
    rule_ids = [r.rule_id for r in result["recommendations"]]
    assert "RULE-02" in rule_ids

def test_rule_02b_minor_cosmetic_wear(setup_db):
    """RULE-02B: Verify superficial scuffs produce non-escalating LOW risk without quarantine."""
    db = setup_db
    dev_id, ret_id = _create_base_return(db, "r02b")
    db.add(ConditionCheck(return_id=ret_id, exterior="Minor cosmetic wear", screen="Good", power="Normal", sensors="Functional"))
    db.add(PatientAcknowledgement(return_id=ret_id, status="RECEIVED", recorded_by="Tester"))
    db.add(CleaningRecord(return_id=ret_id, status="COMPLETED", completed_by="Tester"))
    db.commit()

    result = evaluate_device_return(db, ret_id)
    assert result["overall_risk_level"] == "LOW"
    assert len(result["flagged_issues"]) == 0
    rule_ids = [r.rule_id for r in result["recommendations"]]
    assert "RULE-02B" in rule_ids

def test_rule_02c_minor_hardware_degradation(setup_db):
    """RULE-02C: Verify weak battery or minor casing damage schedules routine 48h maintenance."""
    db = setup_db
    dev_id, ret_id = _create_base_return(db, "r02c")
    db.add(ConditionCheck(return_id=ret_id, exterior="Minor damage", screen="Good", power="Normal", battery="Weak"))
    db.add(PatientAcknowledgement(return_id=ret_id, status="RECEIVED", recorded_by="Tester"))
    db.add(CleaningRecord(return_id=ret_id, status="COMPLETED", completed_by="Tester"))
    db.commit()

    result = evaluate_device_return(db, ret_id)
    assert result["overall_risk_level"] == "MEDIUM"
    assert "Minor Hardware Degradation" in result["flagged_issues"]
    rule_ids = [r.rule_id for r in result["recommendations"]]
    assert "RULE-02C" in rule_ids

def test_rule_03_cleaning_incomplete(setup_db):
    """RULE-03: Verify incomplete or failed sanitisation sets MEDIUM risk and creates task."""
    db = setup_db
    dev_id, ret_id = _create_base_return(db, "r03")
    db.add(ConditionCheck(return_id=ret_id, exterior="Good", screen="Good", power="Normal"))
    db.add(PatientAcknowledgement(return_id=ret_id, status="RECEIVED", recorded_by="Tester"))
    db.add(CleaningRecord(return_id=ret_id, status="PENDING", completed_by="Tester"))
    db.commit()

    result = evaluate_device_return(db, ret_id)
    assert result["overall_risk_level"] == "MEDIUM"
    assert "Cleaning Incomplete" in result["flagged_issues"]
    rule_ids = [r.rule_id for r in result["recommendations"]]
    assert "RULE-03" in rule_ids

def test_rule_04_patient_acknowledgement_missing(setup_db):
    """RULE-04: Verify missing patient acknowledgement form triggers follow-up task."""
    db = setup_db
    dev_id, ret_id = _create_base_return(db, "r04")
    db.add(ConditionCheck(return_id=ret_id, exterior="Good", screen="Good", power="Normal"))
    db.add(PatientAcknowledgement(return_id=ret_id, status="MISSING", recorded_by="Tester"))
    db.add(CleaningRecord(return_id=ret_id, status="COMPLETED", completed_by="Tester"))
    db.commit()

    result = evaluate_device_return(db, ret_id)
    assert result["overall_risk_level"] == "MEDIUM"
    assert "Patient Acknowledgement Missing" in result["flagged_issues"]
    rule_ids = [r.rule_id for r in result["recommendations"]]
    assert "RULE-04" in rule_ids

def test_rule_05_compound_multi_risk(setup_db):
    """RULE-05: Verify 2 or more checklist failures compound into CRITICAL overall risk."""
    db = setup_db
    dev_id, ret_id = _create_base_return(db, "r05")
    db.add(ConditionCheck(return_id=ret_id, exterior="Major damage", screen="Good", power="Normal"))
    db.add(PatientAcknowledgement(return_id=ret_id, status="MISSING", recorded_by="Tester"))
    db.add(CleaningRecord(return_id=ret_id, status="PENDING", completed_by="Tester"))
    db.commit()

    result = evaluate_device_return(db, ret_id)
    assert result["overall_risk_level"] == "CRITICAL"
    assert len(result["flagged_issues"]) >= 2
    rule_ids = [r.rule_id for r in result["recommendations"]]
    assert "RULE-05" in rule_ids

def test_rule_07_mandatory_hitl_review(setup_db):
    """RULE-07: Verify human-in-the-loop review recommendation is generated for clinical governance."""
    db = setup_db
    dev_id, ret_id = _create_base_return(db, "r07")
    db.add(ConditionCheck(return_id=ret_id, exterior="Good", screen="Good", power="Normal"))
    db.add(PatientAcknowledgement(return_id=ret_id, status="RECEIVED", recorded_by="Tester"))
    db.add(CleaningRecord(return_id=ret_id, status="COMPLETED", completed_by="Tester"))
    db.commit()

    result = evaluate_device_return(db, ret_id)
    rule_ids = [r.rule_id for r in result["recommendations"]]
    assert "RULE-07" in rule_ids
