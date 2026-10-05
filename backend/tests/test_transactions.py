import sys
import os
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, engine, Base
from app.models import Device, DeviceReturn, ReturnedAccessory, ConditionCheck, PatientAcknowledgement, CleaningRecord
from app.services.rule_engine import seed_rules_if_empty

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_rules_if_empty(db)
    yield db
    db.close()

def test_atomic_checkout_success(setup_db):
    """Verify all 4 checklist steps and evaluation persist atomically in one request."""
    db = setup_db
    uid = uuid.uuid4().hex[:6]
    dev_id = f"DEV-TX-{uid}"
    ret_id = f"RET-TX-{uid}"

    dev = Device(device_id=dev_id, device_type="Pulse Oximeter", serial_number=f"SN-TX-{uid}", status="RETURN_PENDING")
    db.add(dev)
    ret = DeviceReturn(return_id=ret_id, device_id=dev_id, received_by="Field Nurse", status="RETURN_PENDING")
    db.add(ret)
    db.commit()

    payload = {
        "accessories": [
            {"accessory_id": "ACC-PROBE-01", "expected_quantity": 1, "returned_quantity": 1, "condition": "PRESENT"}
        ],
        "condition": {
            "exterior": "Good",
            "screen": "Good",
            "buttons": "Functional",
            "power": "Normal",
            "battery": "Normal",
            "ports": "Good",
            "sensors": "Functional",
            "physical_cleanliness": "Clean",
            "notes": "All hardware in optimal working order."
        },
        "patient_ack": {
            "status": "RECEIVED",
            "method": "Digital Signature",
            "notes": "Patient confirmed return without issues."
        },
        "cleaning": {
            "status": "COMPLETED",
            "notes": "Standard 70% isopropyl wipe down completed."
        }
    }

    res = client.post(f"/api/returns/{ret_id}/checkout", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["return_id"] == ret_id
    assert data["overall_risk_level"] == "LOW"

    # Verify all records exist in DB
    db.expire_all()
    assert db.query(ReturnedAccessory).filter(ReturnedAccessory.return_id == ret_id).count() == 1
    assert db.query(ConditionCheck).filter(ConditionCheck.return_id == ret_id).count() == 1
    assert db.query(PatientAcknowledgement).filter(PatientAcknowledgement.return_id == ret_id).count() == 1
    assert db.query(CleaningRecord).filter(CleaningRecord.return_id == ret_id).count() == 1

def test_atomic_checkout_nonexistent_return():
    """Verify atomic checkout against non-existent return returns 404."""
    payload = {
        "accessories": [],
        "condition": {"exterior": "Good", "screen": "Good", "buttons": "Functional", "power": "Normal", "battery": "Normal", "ports": "Good", "sensors": "Functional", "physical_cleanliness": "Clean"},
        "patient_ack": {"status": "RECEIVED"},
        "cleaning": {"status": "COMPLETED"}
    }
    res = client.post("/api/returns/RET-NONEXISTENT-9999/checkout", json=payload)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_atomic_checkout_rejects_finalized_return(setup_db):
    """Verify atomic checkout against an already completed return is rejected with 400 state violation."""
    db = setup_db
    uid = uuid.uuid4().hex[:6]
    dev_id = f"DEV-FIN-{uid}"
    ret_id = f"RET-FIN-{uid}"

    dev = Device(device_id=dev_id, device_type="Infusion Pump", serial_number=f"SN-FIN-{uid}", status="COMPLETED")
    db.add(dev)
    ret = DeviceReturn(return_id=ret_id, device_id=dev_id, received_by="Field Nurse", status="COMPLETED")
    db.add(ret)
    db.commit()

    payload = {
        "accessories": [],
        "condition": {"exterior": "Good", "screen": "Good", "buttons": "Functional", "power": "Normal", "battery": "Normal", "ports": "Good", "sensors": "Functional", "physical_cleanliness": "Clean"},
        "patient_ack": {"status": "RECEIVED"},
        "cleaning": {"status": "COMPLETED"}
    }
    res = client.post(f"/api/returns/{ret_id}/checkout", json=payload)
    assert res.status_code == 400
    assert "State Machine Violation" in res.json()["detail"]
