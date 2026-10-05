import sys
import os
import uuid
import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, engine, Base
from app.models import (
    Device, AccessoryCatalog, DeviceAccessory, DeviceReturn,
    ReturnedAccessory, ConditionCheck, PatientAcknowledgement,
    CleaningRecord, FollowUpTask, User, Recommendation
)
from app.auth import get_current_user
from app.services.rule_engine import seed_rules_if_empty
from app.services.escalation_service import check_and_escalate_tasks

client = TestClient(app)

def mock_staff_user():
    return User(id=101, username="staff_e2e", name="Staff E2E", role="field_staff")

def mock_clinician_user():
    return User(id=102, username="clinician_e2e", name="Dr. Clinician E2E", role="clinician")

@pytest.fixture(scope="module")
def setup_environment():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_rules_if_empty(db)

    # Seed test accessories: 1 critical, 1 standard
    acc_crit = db.query(AccessoryCatalog).filter(AccessoryCatalog.accessory_id == "ACC-TEST-CRIT").first()
    if not acc_crit:
        acc_crit = AccessoryCatalog(
            accessory_id="ACC-TEST-CRIT",
            accessory_name="Test Critical Pulse Sensor",
            category="Sensor",
            criticality="CRITICAL"
        )
        db.add(acc_crit)

    acc_std = db.query(AccessoryCatalog).filter(AccessoryCatalog.accessory_id == "ACC-TEST-STD").first()
    if not acc_std:
        acc_std = AccessoryCatalog(
            accessory_id="ACC-TEST-STD",
            accessory_name="Test Standard User Manual",
            category="Documentation",
            criticality="STANDARD"
        )
        db.add(acc_std)

    db.commit()
    yield db
    db.close()

def create_test_device(db, uid_suffix: str):
    dev_id = f"DEV-E2E-{uid_suffix}"
    dev = Device(
        device_id=dev_id,
        device_type="Portable Pulse Oximeter",
        serial_number=f"SN-E2E-{uid_suffix}",
        status="ISSUED",
        location="Highland Clinic"
    )
    db.add(dev)
    # Link expected accessories
    db.add(DeviceAccessory(device_id=dev_id, accessory_id="ACC-TEST-CRIT", expected_quantity=1))
    db.add(DeviceAccessory(device_id=dev_id, accessory_id="ACC-TEST-STD", expected_quantity=1))
    db.commit()
    return dev_id


# =========================================================================
# TEST 1: Missing Critical/High-Value Accessory vs. Standard Accessory
# =========================================================================
def test_e2e_missing_critical_vs_standard_accessory(setup_environment):
    """
    Verifies that missing critical accessories trigger HIGH risk and device quarantine,
    whereas missing only standard non-critical accessories triggers LOW risk advisory
    without quarantining the healthy device.
    """
    db = setup_environment
    app.dependency_overrides[get_current_user] = mock_staff_user

    # Case A: Missing Critical Accessory
    dev_id_a = create_test_device(db, uuid.uuid4().hex[:6])
    res_start_a = client.post("/api/returns", json={"device_id": dev_id_a, "received_by": "Nurse Kelly"})
    assert res_start_a.status_code == 201
    ret_id_a = res_start_a.json()["return_id"]

    # Submit accessories with critical sensor missing
    client.post(f"/api/returns/{ret_id_a}/accessories", json={"items": [
        {"accessory_id": "ACC-TEST-CRIT", "expected_quantity": 1, "returned_quantity": 0, "condition": "MISSING"},
        {"accessory_id": "ACC-TEST-STD", "expected_quantity": 1, "returned_quantity": 1, "condition": "PRESENT"}
    ]})
    client.post(f"/api/returns/{ret_id_a}/condition", json={"exterior": "Good", "screen": "Good", "power": "Normal", "sensors": "Functional"})
    client.post(f"/api/returns/{ret_id_a}/acknowledgement", json={"status": "RECEIVED", "method": "Signed Paper Form"})
    client.post(f"/api/returns/{ret_id_a}/cleaning", json={"status": "COMPLETED"})

    res_eval_a = client.post(f"/api/returns/{ret_id_a}/evaluate")
    assert res_eval_a.status_code == 200
    data_a = res_eval_a.json()
    assert data_a["overall_risk_level"] == "HIGH"
    assert "Missing Critical/High-Value Accessories" in data_a["flagged_issues"]

    # Verify device status is quarantined
    db.expire_all()
    dev_a = db.query(Device).filter(Device.device_id == dev_id_a).first()
    assert dev_a.status == "QUARANTINED"

    # Verify 24h SLA task created for Inventory Lead
    urgent_task = db.query(FollowUpTask).filter(
        FollowUpTask.return_id == ret_id_a,
        FollowUpTask.issue_type == "Missing Critical Accessory"
    ).first()
    assert urgent_task is not None
    assert urgent_task.priority == "HIGH"
    assert urgent_task.assigned_to == "Inventory Lead"

    # Case B: Missing Standard Accessory Only (e.g. User Manual)
    dev_id_b = create_test_device(db, uuid.uuid4().hex[:6])
    res_start_b = client.post("/api/returns", json={"device_id": dev_id_b, "received_by": "Nurse Kelly"})
    ret_id_b = res_start_b.json()["return_id"]

    client.post(f"/api/returns/{ret_id_b}/accessories", json={"items": [
        {"accessory_id": "ACC-TEST-CRIT", "expected_quantity": 1, "returned_quantity": 1, "condition": "PRESENT"},
        {"accessory_id": "ACC-TEST-STD", "expected_quantity": 1, "returned_quantity": 0, "condition": "MISSING"}
    ]})
    client.post(f"/api/returns/{ret_id_b}/condition", json={"exterior": "Good", "screen": "Good", "power": "Normal", "sensors": "Functional"})
    client.post(f"/api/returns/{ret_id_b}/acknowledgement", json={"status": "RECEIVED", "method": "Signed Paper Form"})
    client.post(f"/api/returns/{ret_id_b}/cleaning", json={"status": "COMPLETED"})

    res_eval_b = client.post(f"/api/returns/{ret_id_b}/evaluate")
    assert res_eval_b.status_code == 200
    data_b = res_eval_b.json()
    assert data_b["overall_risk_level"] == "LOW"
    assert len(data_b["flagged_issues"]) == 0

    # Device is NOT quarantined
    db.expire_all()
    dev_b = db.query(Device).filter(Device.device_id == dev_id_b).first()
    assert dev_b.status == "RETURNED"

    # Routine 72h task created
    std_task = db.query(FollowUpTask).filter(
        FollowUpTask.return_id == ret_id_b,
        FollowUpTask.issue_type == "Routine Accessory Restock"
    ).first()
    assert std_task is not None
    assert std_task.priority == "LOW"

    app.dependency_overrides.clear()


# =========================================================================
# TEST 2: Major Hardware Damage vs. Minor Cosmetic Wear
# =========================================================================
def test_e2e_major_damage_vs_minor_cosmetic_wear(setup_environment):
    """
    Verifies that major hardware damage triggers HIGH risk and quarantine,
    while minor cosmetic wear (surface scuffs/scratches) is classified as LOW risk,
    allowing clinical clearance without emergency escalation.
    """
    db = setup_environment
    app.dependency_overrides[get_current_user] = mock_staff_user

    # Case A: Major Damage (Cracked screen & does not power on)
    dev_id_major = create_test_device(db, uuid.uuid4().hex[:6])
    res_start = client.post("/api/returns", json={"device_id": dev_id_major, "received_by": "Staff"})
    ret_id_major = res_start.json()["return_id"]

    client.post(f"/api/returns/{ret_id_major}/accessories", json={"items": [
        {"accessory_id": "ACC-TEST-CRIT", "expected_quantity": 1, "returned_quantity": 1, "condition": "PRESENT"},
        {"accessory_id": "ACC-TEST-STD", "expected_quantity": 1, "returned_quantity": 1, "condition": "PRESENT"}
    ]})
    client.post(f"/api/returns/{ret_id_major}/condition", json={
        "exterior": "Major damage", "screen": "Cracked", "power": "Does not power on", "sensors": "Damaged"
    })
    client.post(f"/api/returns/{ret_id_major}/acknowledgement", json={"status": "RECEIVED", "method": "Signed Paper Form"})
    client.post(f"/api/returns/{ret_id_major}/cleaning", json={"status": "COMPLETED"})

    res_eval_major = client.post(f"/api/returns/{ret_id_major}/evaluate")
    assert res_eval_major.status_code == 200
    assert res_eval_major.json()["overall_risk_level"] == "HIGH"
    assert "Major Physical/Hardware Damage" in res_eval_major.json()["flagged_issues"]

    db.expire_all()
    dev_major = db.query(Device).filter(Device.device_id == dev_id_major).first()
    assert dev_major.status == "QUARANTINED"

    biomed_task = db.query(FollowUpTask).filter(
        FollowUpTask.return_id == ret_id_major,
        FollowUpTask.assigned_to == "Biomedical Technician"
    ).first()
    assert biomed_task is not None
    assert biomed_task.priority == "HIGH"

    # Case B: Minor Cosmetic Wear (scratches on casing, intact display and sensors)
    dev_id_cosmetic = create_test_device(db, uuid.uuid4().hex[:6])
    res_start_c = client.post("/api/returns", json={"device_id": dev_id_cosmetic, "received_by": "Staff"})
    ret_id_cosmetic = res_start_c.json()["return_id"]

    client.post(f"/api/returns/{ret_id_cosmetic}/accessories", json={"items": [
        {"accessory_id": "ACC-TEST-CRIT", "expected_quantity": 1, "returned_quantity": 1, "condition": "PRESENT"},
        {"accessory_id": "ACC-TEST-STD", "expected_quantity": 1, "returned_quantity": 1, "condition": "PRESENT"}
    ]})
    client.post(f"/api/returns/{ret_id_cosmetic}/condition", json={
        "exterior": "Minor cosmetic wear", "screen": "Good", "power": "Normal", "sensors": "Functional"
    })
    client.post(f"/api/returns/{ret_id_cosmetic}/acknowledgement", json={"status": "RECEIVED", "method": "Signed Paper Form"})
    client.post(f"/api/returns/{ret_id_cosmetic}/cleaning", json={"status": "COMPLETED"})

    res_eval_cosmetic = client.post(f"/api/returns/{ret_id_cosmetic}/evaluate")
    assert res_eval_cosmetic.status_code == 200
    cosmetic_data = res_eval_cosmetic.json()
    assert cosmetic_data["overall_risk_level"] == "LOW"
    assert len(cosmetic_data["flagged_issues"]) == 0

    # Device is NOT quarantined
    db.expire_all()
    dev_cosmetic = db.query(Device).filter(Device.device_id == dev_id_cosmetic).first()
    assert dev_cosmetic.status == "RETURNED"

    # Rule RULE-02B recommendation is present
    rec_cosmetic = db.query(Recommendation).filter(
        Recommendation.return_id == ret_id_cosmetic,
        Recommendation.rule_id == "RULE-02B"
    ).first()
    assert rec_cosmetic is not None
    assert rec_cosmetic.risk_level == "LOW"

    app.dependency_overrides.clear()


# =========================================================================
# TEST 3: Sanitisation Verification Failure / Reissue Blocker
# =========================================================================
def test_e2e_sanitisation_verification_blocker(setup_environment):
    """
    Verifies that unverified or pending cleaning status flags MEDIUM risk,
    generates a sanitisation task, sets status to INSPECTION_REQUIRED, and blocks re-issue.
    """
    db = setup_environment
    app.dependency_overrides[get_current_user] = mock_staff_user

    dev_id = create_test_device(db, uuid.uuid4().hex[:6])
    res_start = client.post("/api/returns", json={"device_id": dev_id, "received_by": "Staff"})
    ret_id = res_start.json()["return_id"]

    client.post(f"/api/returns/{ret_id}/accessories", json={"items": [
        {"accessory_id": "ACC-TEST-CRIT", "expected_quantity": 1, "returned_quantity": 1, "condition": "PRESENT"},
        {"accessory_id": "ACC-TEST-STD", "expected_quantity": 1, "returned_quantity": 1, "condition": "PRESENT"}
    ]})
    client.post(f"/api/returns/{ret_id}/condition", json={"exterior": "Good", "screen": "Good", "power": "Normal", "sensors": "Functional"})
    client.post(f"/api/returns/{ret_id}/acknowledgement", json={"status": "RECEIVED", "method": "Signed Paper Form"})
    client.post(f"/api/returns/{ret_id}/cleaning", json={"status": "PENDING", "notes": "Requires bio-wipe"})

    res_eval = client.post(f"/api/returns/{ret_id}/evaluate")
    assert res_eval.status_code == 200
    data = res_eval.json()
    assert data["overall_risk_level"] == "MEDIUM"
    assert "Cleaning Incomplete" in data["flagged_issues"]

    db.expire_all()
    dev = db.query(Device).filter(Device.device_id == dev_id).first()
    assert dev.status == "INSPECTION_REQUIRED"

    sanitisation_task = db.query(FollowUpTask).filter(
        FollowUpTask.return_id == ret_id,
        FollowUpTask.issue_type == "Cleaning Verification Required"
    ).first()
    assert sanitisation_task is not None
    assert sanitisation_task.assigned_to == "Sanitisation Lead"

    app.dependency_overrides.clear()


# =========================================================================
# TEST 4: Pre-Evaluation Completeness Gate & State Machine Protection
# =========================================================================
def test_e2e_server_side_validation_and_pre_evaluation_completeness_gate(setup_environment):
    """
    Verifies that calling evaluate prematurely before completing all steps returns
    HTTP 422 with a detailed list of missing steps, preventing inconsistent states.
    """
    db = setup_environment
    app.dependency_overrides[get_current_user] = mock_staff_user

    dev_id = create_test_device(db, uuid.uuid4().hex[:6])
    res_start = client.post("/api/returns", json={"device_id": dev_id, "received_by": "Staff"})
    ret_id = res_start.json()["return_id"]

    # Only save accessories, skip condition, patient ack, and cleaning
    client.post(f"/api/returns/{ret_id}/accessories", json={"items": [
        {"accessory_id": "ACC-TEST-CRIT", "expected_quantity": 1, "returned_quantity": 1, "condition": "PRESENT"}
    ]})

    # Premature evaluate call must fail with HTTP 422
    res_premature = client.post(f"/api/returns/{ret_id}/evaluate")
    assert res_premature.status_code == 422
    err_detail = res_premature.json()["detail"]
    assert "Incomplete Return Checkout" in err_detail
    assert "Hardware Condition Checklist" in err_detail
    assert "Cleaning & Sanitisation Record" in err_detail

    # State Machine Violation test: Finalized return cannot be edited
    ret_obj = db.query(DeviceReturn).filter(DeviceReturn.return_id == ret_id).first()
    ret_obj.status = "COMPLETED"
    db.commit()

    res_violation = client.post(f"/api/returns/{ret_id}/condition", json={"exterior": "Good"})
    assert res_violation.status_code == 400
    assert "State Machine Violation" in res_violation.json()["detail"]

    app.dependency_overrides.clear()


# =========================================================================
# TEST 5: Atomic Multi-Step Checkout & Transaction Integrity
# =========================================================================
def test_e2e_atomic_multi_step_checkout(setup_environment):
    """
    Verifies that the atomic checkout endpoint validates and commits all steps
    in a single database transaction, evaluating the return safely.
    """
    db = setup_environment
    app.dependency_overrides[get_current_user] = mock_staff_user

    dev_id = create_test_device(db, uuid.uuid4().hex[:6])
    res_start = client.post("/api/returns", json={"device_id": dev_id, "received_by": "Staff"})
    ret_id = res_start.json()["return_id"]

    payload = {
        "accessories": [
            {"accessory_id": "ACC-TEST-CRIT", "expected_quantity": 1, "returned_quantity": 1, "condition": "PRESENT"},
            {"accessory_id": "ACC-TEST-STD", "expected_quantity": 1, "returned_quantity": 1, "condition": "PRESENT"}
        ],
        "condition": {
            "exterior": "Minor cosmetic wear",
            "screen": "Good",
            "buttons": "Functional",
            "power": "Normal",
            "battery": "Normal",
            "ports": "Good",
            "sensors": "Functional",
            "physical_cleanliness": "Clean",
            "notes": "Light surface scuff on outer shell."
        },
        "patient_ack": {
            "status": "RECEIVED",
            "method": "Digital Signature",
            "notes": "Patient confirmed device was working."
        },
        "cleaning": {
            "status": "COMPLETED",
            "notes": "Decontaminated with hospital-grade disinfectant."
        }
    }

    res_atomic = client.post(f"/api/returns/{ret_id}/checkout", json=payload)
    assert res_atomic.status_code == 200
    data = res_atomic.json()
    assert data["overall_risk_level"] == "LOW"
    assert "Atomic multi-step checkout and evaluation completed successfully" in data["message"]

    # Verify all records exist in DB
    db.expire_all()
    assert db.query(ConditionCheck).filter(ConditionCheck.return_id == ret_id).first() is not None
    assert db.query(PatientAcknowledgement).filter(PatientAcknowledgement.return_id == ret_id).first() is not None
    assert db.query(CleaningRecord).filter(CleaningRecord.return_id == ret_id).first() is not None

    app.dependency_overrides.clear()


# =========================================================================
# TEST 6: Auto-Escalation Engine SLA Threshold Trigger
# =========================================================================
def test_e2e_auto_escalation_engine(setup_environment):
    """
    Verifies that high-priority follow-up tasks that exceed their SLA (>24h)
    are automatically escalated to the Operations Manager with audit logging.
    """
    db = setup_environment

    task_id = f"TSK-OVERDUE-{uuid.uuid4().hex[:6]}"
    overdue_task = FollowUpTask(
        task_id=task_id,
        return_id="RET-MOCK",
        device_id="DEV-MOCK",
        issue_type="Missing Critical Accessory",
        description="Critical pulse oximeter probe missing.",
        priority="HIGH",
        assigned_to="Inventory Lead",
        created_date=datetime.datetime.utcnow() - datetime.timedelta(hours=36),
        due_date=datetime.datetime.utcnow() - datetime.timedelta(hours=12),
        status="OPEN",
        escalation_level=0
    )
    db.add(overdue_task)
    db.commit()

    # Trigger escalation engine
    escalate_result = check_and_escalate_tasks(db)
    assert escalate_result["escalated_count"] >= 1
    assert task_id in escalate_result["escalated_task_ids"]

    # Verify task state in database
    db.expire_all()
    updated_task = db.query(FollowUpTask).filter(FollowUpTask.task_id == task_id).first()
    assert updated_task.status == "ESCALATED"
    assert updated_task.escalation_level == 1
    assert "Operations Manager" in updated_task.assigned_to
