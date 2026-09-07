import sys
import os
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, engine, Base
from app.models import Device, DeviceReturn, ReturnedAccessory, ConditionCheck, CleaningRecord, PatientAcknowledgement, User
from app.auth import get_current_user

client = TestClient(app)

def mock_get_clinician_user():
    return User(id=99, username="clinician_test", name="Dr. Test", role="clinician")

def mock_get_staff_user():
    return User(id=88, username="staff_test", name="Field Staff Test", role="field_staff")

@pytest.fixture(scope="module")
def setup_test_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    uid = uuid.uuid4().hex[:6]
    dev_id = f"DEV-EDGE-{uid}"
    dev = Device(device_id=dev_id, device_type="Test Oximeter", serial_number=f"SN-EDGE-{uid}", status="READY_FOR_REISSUE")
    db.add(dev)
    db.commit()
    yield {"db": db, "device_id": dev_id}
    db.close()

def test_edge_case_5_unknown_device_id(setup_test_data):
    app.dependency_overrides[get_current_user] = mock_get_staff_user
    response = client.post("/api/returns", json={"device_id": "DEV-UNKNOWN-999", "received_by": "Staff"})
    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]

def test_edge_case_4_duplicate_device_return(setup_test_data):
    dev_id = setup_test_data["device_id"]
    app.dependency_overrides[get_current_user] = mock_get_staff_user
    res1 = client.post("/api/returns", json={"device_id": dev_id, "received_by": "Staff"})
    assert res1.status_code == 201
    
    res2 = client.post("/api/returns", json={"device_id": dev_id, "received_by": "Staff"})
    app.dependency_overrides.clear()
    assert res2.status_code == 400
    assert "Duplicate Return Attempt" in res2.json()["detail"]

def test_edge_case_9_reject_empty_override_reason():
    app.dependency_overrides[get_current_user] = mock_get_clinician_user
    response = client.post("/api/recommendations/REC-9999/override", json={"override_reason": "   "})
    app.dependency_overrides.clear()
    
    assert response.status_code == 422
    assert "non-empty" in response.json()["detail"]
