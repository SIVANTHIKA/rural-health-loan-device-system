import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(30), nullable=False)  # field_staff, clinician, ops_manager, admin
    hashed_password = Column(String(200), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    decisions = relationship("ReviewDecision", back_populates="reviewer")
    audit_logs = relationship("AuditLog", back_populates="user")


class Device(Base):
    __tablename__ = "devices"

    device_id = Column(String(50), primary_key=True, index=True)  # e.g., DEV-001
    device_type = Column(String(100), nullable=False)  # e.g., Portable Oxygen Monitor
    serial_number = Column(String(100), unique=True, nullable=False)
    status = Column(String(50), nullable=False, default="READY_FOR_REISSUE")
    location = Column(String(100), default="Main Health Center")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    issue_records = relationship("DeviceIssueRecord", back_populates="device")
    accessories = relationship("DeviceAccessory", back_populates="device")
    returns = relationship("DeviceReturn", back_populates="device")


class AccessoryCatalog(Base):
    __tablename__ = "accessory_catalog"

    accessory_id = Column(String(50), primary_key=True, index=True) # ACC-001
    accessory_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False) # Sensor, Cable, Charger, Case
    criticality = Column(String(20), default="STANDARD") # CRITICAL, STANDARD

    device_accessories = relationship("DeviceAccessory", back_populates="accessory")


class DeviceAccessory(Base):
    __tablename__ = "device_accessories"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(50), ForeignKey("devices.device_id"), nullable=False)
    accessory_id = Column(String(50), ForeignKey("accessory_catalog.accessory_id"), nullable=False)
    expected_quantity = Column(Integer, default=1)

    device = relationship("Device", back_populates="accessories")
    accessory = relationship("AccessoryCatalog", back_populates="device_accessories")


class DeviceIssueRecord(Base):
    __tablename__ = "device_issue_records"

    issue_id = Column(String(50), primary_key=True, index=True) # ISS-1001
    device_id = Column(String(50), ForeignKey("devices.device_id"), nullable=False)
    patient_reference = Column(String(50), nullable=False) # e.g. PAT-8821
    issued_date = Column(DateTime, default=datetime.datetime.utcnow)
    expected_return_date = Column(DateTime, nullable=False)
    issued_by = Column(String(100), nullable=False)
    status = Column(String(30), default="ISSUED") # ISSUED, RETURNED, OVERDUE

    device = relationship("Device", back_populates="issue_records")
    returns = relationship("DeviceReturn", back_populates="issue_record")


class DeviceReturn(Base):
    __tablename__ = "device_returns"

    return_id = Column(String(50), primary_key=True, index=True) # RET-2001
    device_id = Column(String(50), ForeignKey("devices.device_id"), nullable=False)
    issue_id = Column(String(50), ForeignKey("device_issue_records.issue_id"), nullable=True)
    returned_date = Column(DateTime, default=datetime.datetime.utcnow)
    received_by = Column(String(100), nullable=False)
    status = Column(String(50), default="RETURN_PENDING") # RETURN_PENDING, IN_REVIEW, COMPLETED, QUARANTINED
    overall_risk_level = Column(String(20), default="LOW") # LOW, MEDIUM, HIGH, CRITICAL

    device = relationship("Device", back_populates="returns")
    issue_record = relationship("DeviceIssueRecord", back_populates="returns")
    returned_accessories = relationship("ReturnedAccessory", back_populates="device_return")
    condition_check = relationship("ConditionCheck", back_populates="device_return", uselist=False)
    patient_ack = relationship("PatientAcknowledgement", back_populates="device_return", uselist=False)
    cleaning_record = relationship("CleaningRecord", back_populates="device_return", uselist=False)
    recommendations = relationship("Recommendation", back_populates="device_return")
    follow_up_tasks = relationship("FollowUpTask", back_populates="device_return")


class ReturnedAccessory(Base):
    __tablename__ = "returned_accessories"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(String(50), ForeignKey("device_returns.return_id"), nullable=False)
    accessory_id = Column(String(50), ForeignKey("accessory_catalog.accessory_id"), nullable=False)
    expected_quantity = Column(Integer, default=1)
    returned_quantity = Column(Integer, default=0)
    condition = Column(String(30), default="PRESENT") # PRESENT, MISSING, DAMAGED, UNKNOWN

    device_return = relationship("DeviceReturn", back_populates="returned_accessories")
    accessory = relationship("AccessoryCatalog")


class ConditionCheck(Base):
    __tablename__ = "condition_checks"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(String(50), ForeignKey("device_returns.return_id"), unique=True, nullable=False)
    exterior = Column(String(30), default="Good") # Good, Minor damage, Major damage
    screen = Column(String(30), default="Good") # Good, Cracked, Not functioning
    buttons = Column(String(30), default="Functional") # Functional, Partially functional, Not functional
    power = Column(String(30), default="Normal") # Normal, Charging issue, Does not power on
    battery = Column(String(30), default="Normal") # Normal, Weak, Unknown
    ports = Column(String(30), default="Good") # Good, Damaged, Unknown
    sensors = Column(String(30), default="Functional") # Functional, Damaged, Unknown
    physical_cleanliness = Column(String(30), default="Clean") # Clean, Needs cleaning, Contaminated/uncertain
    notes = Column(Text, nullable=True)
    photo_url = Column(String(255), nullable=True)

    device_return = relationship("DeviceReturn", back_populates="condition_check")


class PatientAcknowledgement(Base):
    __tablename__ = "patient_acknowledgements"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(String(50), ForeignKey("device_returns.return_id"), unique=True, nullable=False)
    status = Column(String(30), default="RECEIVED") # RECEIVED, MISSING
    method = Column(String(50), default="Signed Paper Form") # Signed Paper Form, Digital Signature, Verbal Confirmation
    recorded_by = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, nullable=True)

    device_return = relationship("DeviceReturn", back_populates="patient_ack")


class CleaningRecord(Base):
    __tablename__ = "cleaning_records"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(String(50), ForeignKey("device_returns.return_id"), unique=True, nullable=False)
    status = Column(String(30), default="COMPLETED") # COMPLETED, PENDING, FAILED_UNCERTAIN, NOT_APPLICABLE
    completed_by = Column(String(100), nullable=False)
    completed_at = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, nullable=True)

    device_return = relationship("DeviceReturn", back_populates="cleaning_record")


class Rule(Base):
    __tablename__ = "rules"

    rule_id = Column(String(50), primary_key=True, index=True) # RULE-01
    rule_name = Column(String(100), nullable=False)
    condition_expr = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    risk_level = Column(String(20), default="MEDIUM") # LOW, MEDIUM, HIGH, CRITICAL
    required_human_action = Column(Text, nullable=False)
    evidence_description = Column(Text, nullable=False)


class Recommendation(Base):
    __tablename__ = "recommendations"

    recommendation_id = Column(String(50), primary_key=True, index=True) # REC-5001
    return_id = Column(String(50), ForeignKey("device_returns.return_id"), nullable=False)
    rule_id = Column(String(50), ForeignKey("rules.rule_id"), nullable=True)
    recommendation = Column(Text, nullable=False)
    risk_level = Column(String(20), nullable=False) # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(30), default="PENDING") # PENDING, CONFIRMED, OVERRIDDEN

    device_return = relationship("DeviceReturn", back_populates="recommendations")
    rule = relationship("Rule")
    decisions = relationship("ReviewDecision", back_populates="recommendation")


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    decision_id = Column(String(50), primary_key=True, index=True) # DEC-6001
    recommendation_id = Column(String(50), ForeignKey("recommendations.recommendation_id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    decision = Column(String(20), nullable=False) # CONFIRM, OVERRIDE
    override_reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    recommendation = relationship("Recommendation", back_populates="decisions")
    reviewer = relationship("User", back_populates="decisions")


class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"

    task_id = Column(String(50), primary_key=True, index=True) # TSK-7001
    return_id = Column(String(50), ForeignKey("device_returns.return_id"), nullable=True)
    device_id = Column(String(50), ForeignKey("devices.device_id"), nullable=False)
    issue_type = Column(String(100), nullable=False) # Missing Accessory, Major Damage, Cleaning Pending, Patient Ack Missing
    description = Column(Text, nullable=False)
    priority = Column(String(20), default="MEDIUM") # LOW, MEDIUM, HIGH, CRITICAL
    assigned_to = Column(String(100), default="Unassigned")
    created_date = Column(DateTime, default=datetime.datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    status = Column(String(30), default="OPEN") # OPEN, IN_PROGRESS, BLOCKED, RESOLVED, ESCALATED, CLOSED
    escalation_level = Column(Integer, default=0) # 0 = Normal, 1 = Manager Escalated
    resolution = Column(Text, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_date = Column(DateTime, nullable=True)

    device_return = relationship("DeviceReturn", back_populates="follow_up_tasks")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_name = Column(String(100), default="System")
    user_role = Column(String(50), default="System")
    action = Column(String(100), nullable=False) # CHECK_IN, RECONCILE, EVALUATE, CONFIRM_RECOMMENDATION, OVERRIDE_RECOMMENDATION, ESCALATE_TASK
    entity = Column(String(50), nullable=False) # DeviceReturn, Recommendation, FollowUpTask, Device
    entity_id = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(Text, nullable=True)

    user = relationship("User", back_populates="audit_logs")
