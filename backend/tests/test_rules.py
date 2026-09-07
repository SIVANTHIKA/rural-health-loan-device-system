import sys
import os
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.database import SessionLocal, engine, Base
from app.models import (
    Device, DeviceReturn, ReturnedAccessory, ConditionCheck,
    PatientAcknowledgement, CleaningRecord, Recommendation, FollowUpTask
)
from app.services.rule_engine import evaluate_device_return, seed_rules_if_empty

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_rules_if_empty(db)
    yield db
    db.close()

def test_rule_engine_clean_return(setup_db):
    db = setup_db
    uid = uuid.uuid4().hex[:6]
    dev_id = f"DEV-TEST-{uid}"
    ret_id = f"RET-TEST-{uid}"
    
    dev = Device(device_id=dev_id, device_type="Pulse Ox", serial_number=f"SN-TEST-{uid}", status="RETURN_PENDING")
    db.add(dev)
    ret = DeviceReturn(return_id=ret_id, device_id=dev_id, received_by="Staff A", status="RETURN_PENDING")
    db.add(ret)
    db.add(ConditionCheck(return_id=ret_id, exterior="Good", screen="Good", power="Normal"))
    db.add(PatientAcknowledgement(return_id=ret_id, status="RECEIVED", recorded_by="Staff A"))
    db.add(CleaningRecord(return_id=ret_id, status="COMPLETED", completed_by="Staff A"))
    db.commit()

    result = evaluate_device_return(db, ret_id)
    assert result["overall_risk_level"] == "LOW"
    assert len(result["flagged_issues"]) == 0
