from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Device, AccessoryCatalog, DeviceAccessory, DeviceIssueRecord, User
from app.schemas import (
    DeviceResponse, DeviceCreate, AccessoryCatalogItem,
    DeviceIssueRecordResponse, DeviceIssueRecordCreate
)
from app.auth import get_current_user, require_roles
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api", tags=["Devices & Issues"])

@router.get("/devices", response_model=List[DeviceResponse])
def get_devices(
    query: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Device)
    if status:
        q = q.filter(Device.status == status)
    if query:
        q = q.filter(
            (Device.device_id.ilike(f"%{query}%")) |
            (Device.serial_number.ilike(f"%{query}%")) |
            (Device.device_type.ilike(f"%{query}%"))
        )
    return q.all()

@router.get("/devices/{device_id}", response_model=DeviceResponse)
def get_device_by_id(device_id: str, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found.")
    return device

@router.post("/devices", response_model=DeviceResponse)
def create_device(
    dev_in: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "ops_manager"]))
):
    existing = db.query(Device).filter(Device.device_id == dev_in.device_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Device ID '{dev_in.device_id}' already exists.")
    
    device = Device(
        device_id=dev_in.device_id,
        device_type=dev_in.device_type,
        serial_number=dev_in.serial_number,
        status=dev_in.status,
        location=dev_in.location
    )
    db.add(device)
    
    if dev_in.expected_accessories:
        for acc in dev_in.expected_accessories:
            da = DeviceAccessory(
                device_id=dev_in.device_id,
                accessory_id=acc["accessory_id"],
                expected_quantity=acc.get("expected_quantity", 1)
            )
            db.add(da)

    db.commit()
    db.refresh(device)

    log_audit(db, action="CREATE_DEVICE", entity="Device", entity_id=device.device_id, user=current_user)
    return device

@router.get("/accessories", response_model=List[AccessoryCatalogItem])
def get_accessory_catalog(db: Session = Depends(get_db)):
    return db.query(AccessoryCatalog).all()

@router.get("/issue-records", response_model=List[DeviceIssueRecordResponse])
def get_issue_records(
    query: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(DeviceIssueRecord)
    if status:
        q = q.filter(DeviceIssueRecord.status == status)
    if query:
        q = q.filter(
            (DeviceIssueRecord.issue_id.ilike(f"%{query}%")) |
            (DeviceIssueRecord.device_id.ilike(f"%{query}%")) |
            (DeviceIssueRecord.patient_reference.ilike(f"%{query}%"))
        )
    return q.all()

@router.get("/issue-records/{issue_id}", response_model=DeviceIssueRecordResponse)
def get_issue_record_by_id(issue_id: str, db: Session = Depends(get_db)):
    rec = db.query(DeviceIssueRecord).filter(DeviceIssueRecord.issue_id == issue_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Issue record '{issue_id}' not found.")
    return rec

@router.post("/issue-records", response_model=DeviceIssueRecordResponse)
def create_issue_record(
    issue_in: DeviceIssueRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.device_id == issue_in.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{issue_in.device_id}' does not exist.")
    
    if device.status not in ["READY_FOR_REISSUE", "RETURNED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Device '{device.device_id}' cannot be issued. Current status: '{device.status}'."
        )

    rec = DeviceIssueRecord(
        issue_id=issue_in.issue_id,
        device_id=issue_in.device_id,
        patient_reference=issue_in.patient_reference,
        expected_return_date=issue_in.expected_return_date,
        issued_by=issue_in.issued_by,
        status="ISSUED"
    )
    device.status = "ISSUED"
    db.add(rec)
    db.commit()
    db.refresh(rec)

    log_audit(db, action="ISSUE_DEVICE", entity="DeviceIssueRecord", entity_id=rec.issue_id, user=current_user, details=f"Issued to {rec.patient_reference}")
    return rec
