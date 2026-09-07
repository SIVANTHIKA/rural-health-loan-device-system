import datetime
import random
import uuid
from app.database import engine, SessionLocal, Base
from app.models import (
    User, Device, AccessoryCatalog, DeviceAccessory, DeviceIssueRecord,
    DeviceReturn, ReturnedAccessory, ConditionCheck, PatientAcknowledgement,
    CleaningRecord, Rule, Recommendation, ReviewDecision, FollowUpTask, AuditLog
)
from app.auth import get_password_hash
from app.services.rule_engine import evaluate_device_return

def seed_database():
    print("Recreating database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # 1. Seed Users (Roles: field_staff, clinician, ops_manager, admin)
        users_data = [
            {"username": "staff1", "name": "Sarah Connor (Field Staff)", "role": "field_staff"},
            {"username": "staff2", "name": "David Miller (Field Nurse)", "role": "field_staff"},
            {"username": "clinician1", "name": "Dr. Elizabeth Vance (Clinician)", "role": "clinician"},
            {"username": "clinician2", "name": "Dr. Marcus Brody (Biomedical Lead)", "role": "clinician"},
            {"username": "ops1", "name": "Robert Chen (Operations Manager)", "role": "ops_manager"},
            {"username": "admin1", "name": "System Admin", "role": "admin"}
        ]
        
        default_pwd = get_password_hash("password123")
        created_users = []
        for u in users_data:
            user_obj = User(
                username=u["username"],
                name=u["name"],
                role=u["role"],
                hashed_password=default_pwd,
                active=True
            )
            db.add(user_obj)
            created_users.append(user_obj)
        db.commit()
        print(f"Created {len(created_users)} users.")

        # 2. Seed Accessory Catalog
        accessories = [
            {"accessory_id": "ACC-001", "accessory_name": "Finger Pulse Oximeter Sensor", "category": "Sensor", "criticality": "CRITICAL"},
            {"accessory_id": "ACC-002", "accessory_name": "AC Power Adapter & Charger Cable", "category": "Charger", "criticality": "CRITICAL"},
            {"accessory_id": "ACC-003", "accessory_name": "Padded Protective Carrying Case", "category": "Case", "criticality": "STANDARD"},
            {"accessory_id": "ACC-004", "accessory_name": "USB Data Sync Cable", "category": "Cable", "criticality": "STANDARD"},
            {"accessory_id": "ACC-005", "accessory_name": "Patient Quick-Start User Manual", "category": "Documentation", "criticality": "STANDARD"},
            {"accessory_id": "ACC-006", "accessory_name": "ECG 5-Lead Patient Cable Harness", "category": "Sensor", "criticality": "CRITICAL"},
            {"accessory_id": "ACC-007", "accessory_name": "CPAP Heated Humidifier Tubing", "category": "Tubing", "criticality": "CRITICAL"},
            {"accessory_id": "ACC-008", "accessory_name": "CPAP Silicone Nasal Cushion Mask", "category": "Mask", "criticality": "CRITICAL"}
        ]
        for a in accessories:
            db.add(AccessoryCatalog(**a))
        db.commit()
        print("Created accessory catalog.")

        # 3. Seed 50 Devices
        device_types = [
            ("Portable Oxygen Monitor", ["ACC-001", "ACC-002", "ACC-003", "ACC-004", "ACC-005"]),
            ("3-Channel Portable ECG Recorder", ["ACC-006", "ACC-002", "ACC-003", "ACC-004", "ACC-005"]),
            ("Rural Field CPAP Machine", ["ACC-007", "ACC-008", "ACC-002", "ACC-003", "ACC-005"]),
            ("Ambulatory Infusion Pump", ["ACC-002", "ACC-003", "ACC-004", "ACC-005"])
        ]

        locations = ["Highland Clinic A", "River Valley Clinic B", "Mobile Unit 1", "Central Depot", "District Hospital"]
        devices = []

        for i in range(1, 51):
            dev_id = f"DEV-{i:03d}"
            dtype, acc_ids = device_types[i % len(device_types)]
            serial = f"SN-{dtype[:3].upper()}-2026-{1000+i}"
            
            # Initial status
            status = "READY_FOR_REISSUE"
            if i in [1, 5, 12, 18, 25]:
                status = "ISSUED"
            elif i in [2, 7, 14, 22]:
                status = "QUARANTINED"
            elif i in [3, 9, 15]:
                status = "INSPECTION_REQUIRED"

            dev = Device(
                device_id=dev_id,
                device_type=dtype,
                serial_number=serial,
                status=status,
                location=locations[i % len(locations)]
            )
            db.add(dev)
            devices.append((dev, acc_ids))

        db.commit()
        print("Created 50 devices.")

        # Assign Expected Accessories
        for dev, acc_ids in devices:
            for acc_id in acc_ids:
                db.add(DeviceAccessory(
                    device_id=dev.device_id,
                    accessory_id=acc_id,
                    expected_quantity=1
                ))
        db.commit()

        # 4. Seed 100 Issue Records & 100 Returns
        now = datetime.datetime.utcnow()
        returns_created = 0

        for i in range(1, 101):
            dev_obj, acc_ids = devices[(i - 1) % 50]
            issue_id = f"ISS-{1000+i}"
            patient_ref = f"PAT-9{i:03d}"
            issued_dt = now - datetime.timedelta(days=random.randint(5, 30))
            exp_return_dt = issued_dt + datetime.timedelta(days=7)

            iss_record = DeviceIssueRecord(
                issue_id=issue_id,
                device_id=dev_obj.device_id,
                patient_reference=patient_ref,
                issued_date=issued_dt,
                expected_return_date=exp_return_dt,
                issued_by="Sarah Connor (Field Staff)",
                status="RETURNED"
            )
            db.add(iss_record)

            ret_id = f"RET-{2000+i}"
            ret_dt = issued_dt + datetime.timedelta(days=random.randint(4, 9))

            ret_obj = DeviceReturn(
                return_id=ret_id,
                device_id=dev_obj.device_id,
                issue_id=issue_id,
                returned_date=ret_dt,
                received_by="David Miller (Field Nurse)",
                status="RETURN_PENDING",
                overall_risk_level="LOW"
            )
            db.add(ret_obj)
            db.commit()

            # Seed Returned Accessories with controlled edge cases
            is_edge_case_1 = (i in [1, 11, 21, 31, 41]) # Missing critical accessory
            is_edge_case_6 = (i in [6, 16]) # Excess accessory quantity

            for acc_id in acc_ids:
                exp_qty = 1
                ret_qty = 1
                cond = "PRESENT"

                if is_edge_case_1 and acc_id in ["ACC-001", "ACC-006", "ACC-007"]:
                    ret_qty = 0
                    cond = "MISSING"
                elif is_edge_case_6 and acc_id == "ACC-004":
                    ret_qty = 2 # Excess quantity returned

                db.add(ReturnedAccessory(
                    return_id=ret_id,
                    accessory_id=acc_id,
                    expected_quantity=exp_qty,
                    returned_quantity=ret_qty,
                    condition=cond
                ))

            # Condition Check with Edge Cases
            is_edge_case_2 = (i in [2, 12, 22, 32, 42]) # Major physical damage
            exterior = "Good"
            screen = "Good"
            power = "Normal"
            sensors = "Functional"

            if is_edge_case_2:
                exterior = "Major damage"
                screen = "Cracked"
                power = "Charging issue"
                sensors = "Damaged"
            elif i in [8, 18, 28]:
                exterior = "Minor damage"

            db.add(ConditionCheck(
                return_id=ret_id,
                exterior=exterior,
                screen=screen,
                buttons="Functional",
                power=power,
                battery="Normal",
                ports="Good",
                sensors=sensors,
                physical_cleanliness="Clean" if not is_edge_case_2 else "Needs cleaning",
                notes="Checklist logged during check-in."
            ))

            # Patient Ack with Edge Cases
            is_edge_case_7 = (i in [7, 17, 27, 37, 47]) # Patient Ack Missing
            db.add(PatientAcknowledgement(
                return_id=ret_id,
                status="MISSING" if is_edge_case_7 else "RECEIVED",
                method="Signed Paper Form" if not is_edge_case_7 else "None",
                recorded_by="David Miller (Field Nurse)",
                timestamp=ret_dt
            ))

            # Cleaning Status with Edge Cases
            is_edge_case_3 = (i in [3, 13, 23, 33, 43]) # Cleaning unknown / pending
            db.add(CleaningRecord(
                return_id=ret_id,
                status="PENDING" if is_edge_case_3 else "COMPLETED",
                completed_by="Sanitisation Lead",
                completed_at=ret_dt
            ))

            db.commit()

            # Run Rule Engine Evaluation for every return record
            evaluate_device_return(db, ret_id)
            returns_created += 1

        print(f"Created and evaluated {returns_created} return records with realistic edge cases.")

        # Seed Overdue Follow-up Task for Edge Case 8 testing
        overdue_task = FollowUpTask(
            task_id="TSK-OVERDUE-01",
            return_id="RET-2001",
            device_id="DEV-001",
            issue_type="Missing Critical Sensor",
            description="EDGE CASE 8: Overdue high-priority sensor replacement pending > 48 hrs.",
            priority="HIGH",
            assigned_to="Operations Manager (Escalated)",
            created_date=now - datetime.timedelta(days=3),
            due_date=now - datetime.timedelta(days=1),
            status="ESCALATED",
            escalation_level=1
        )
        db.add(overdue_task)
        db.commit()

        print("Database seeded successfully with 50 devices, 100 issue records, 100 returns, edge cases, and tasks!")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
