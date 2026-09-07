import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

# User Schemas
class UserBase(BaseModel):
    username: str
    name: str
    role: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    active: bool
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class LoginRequest(BaseModel):
    username: str
    password: str

# Device & Accessory Schemas
class AccessoryCatalogItem(BaseModel):
    accessory_id: str
    accessory_name: str
    category: str
    criticality: str
    model_config = ConfigDict(from_attributes=True)

class DeviceAccessorySchema(BaseModel):
    accessory_id: str
    accessory_name: str
    category: str
    criticality: str
    expected_quantity: int
    model_config = ConfigDict(from_attributes=True)

class DeviceBase(BaseModel):
    device_id: str
    device_type: str
    serial_number: str
    status: str
    location: str

class DeviceCreate(DeviceBase):
    expected_accessories: Optional[List[dict]] = []

class DeviceResponse(DeviceBase):
    created_at: datetime.datetime
    accessories: List[DeviceAccessorySchema] = []
    model_config = ConfigDict(from_attributes=True)

# Device Issue Record Schemas
class DeviceIssueRecordCreate(BaseModel):
    issue_id: str
    device_id: str
    patient_reference: str
    expected_return_date: datetime.datetime
    issued_by: str

class DeviceIssueRecordResponse(BaseModel):
    issue_id: str
    device_id: str
    patient_reference: str
    issued_date: datetime.datetime
    expected_return_date: datetime.datetime
    issued_by: str
    status: str
    model_config = ConfigDict(from_attributes=True)

# Return Checklist Input Schemas
class AccessoryReturnItemInput(BaseModel):
    accessory_id: str
    expected_quantity: int
    returned_quantity: int
    condition: str = Field(description="PRESENT, MISSING, DAMAGED, UNKNOWN")

class ReturnedAccessoriesBatchInput(BaseModel):
    items: List[AccessoryReturnItemInput]

class ConditionCheckInput(BaseModel):
    exterior: str = Field(default="Good", description="Good, Minor damage, Major damage")
    screen: str = Field(default="Good", description="Good, Cracked, Not functioning")
    buttons: str = Field(default="Functional", description="Functional, Partially functional, Not functional")
    power: str = Field(default="Normal", description="Normal, Charging issue, Does not power on")
    battery: str = Field(default="Normal", description="Normal, Weak, Unknown")
    ports: str = Field(default="Good", description="Good, Damaged, Unknown")
    sensors: str = Field(default="Functional", description="Functional, Damaged, Unknown")
    physical_cleanliness: str = Field(default="Clean", description="Clean, Needs cleaning, Contaminated/uncertain")
    notes: Optional[str] = None
    photo_url: Optional[str] = None

class PatientAckInput(BaseModel):
    status: str = Field(description="RECEIVED, MISSING")
    method: str = Field(default="Signed Paper Form")
    notes: Optional[str] = None

class CleaningInput(BaseModel):
    status: str = Field(description="COMPLETED, PENDING, FAILED_UNCERTAIN, NOT_APPLICABLE")
    notes: Optional[str] = None

class CreateReturnRequest(BaseModel):
    device_id: str
    issue_id: Optional[str] = None
    received_by: str

# Rule & Recommendation Schemas
class RuleSchema(BaseModel):
    rule_id: str
    rule_name: str
    condition_expr: str
    recommendation: str
    risk_level: str
    required_human_action: str
    evidence_description: str
    model_config = ConfigDict(from_attributes=True)

class RecommendationResponse(BaseModel):
    recommendation_id: str
    return_id: str
    rule_id: Optional[str]
    recommendation: str
    risk_level: str
    status: str # PENDING, CONFIRMED, OVERRIDDEN
    rule: Optional[RuleSchema] = None
    model_config = ConfigDict(from_attributes=True)

# HITL Review Schemas
class ConfirmRecommendationInput(BaseModel):
    notes: Optional[str] = None

class OverrideRecommendationInput(BaseModel):
    override_reason: str = Field(min_length=3, description="Compulsory non-empty reason explaining the decision override")
    notes: Optional[str] = None

class ReviewDecisionResponse(BaseModel):
    decision_id: str
    recommendation_id: str
    reviewer_id: int
    decision: str # CONFIRM, OVERRIDE
    override_reason: Optional[str]
    timestamp: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

# Follow-up Task Schemas
class FollowUpTaskCreate(BaseModel):
    device_id: str
    return_id: Optional[str] = None
    issue_type: str
    description: str
    priority: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, CRITICAL")
    assigned_to: Optional[str] = "Unassigned"
    due_hours: int = 24

class FollowUpTaskUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime.datetime] = None
    resolution: Optional[str] = None

class FollowUpTaskResponse(BaseModel):
    task_id: str
    return_id: Optional[str]
    device_id: str
    issue_type: str
    description: str
    priority: str
    assigned_to: str
    created_date: datetime.datetime
    due_date: datetime.datetime
    status: str
    escalation_level: int
    resolution: Optional[str]
    resolved_by: Optional[str]
    resolved_date: Optional[datetime.datetime]
    model_config = ConfigDict(from_attributes=True)

# Audit Log Schemas
class AuditLogResponse(BaseModel):
    log_id: int
    user_id: Optional[int]
    user_name: str
    user_role: str
    action: str
    entity: str
    entity_id: str
    timestamp: datetime.datetime
    details: Optional[str]
    model_config = ConfigDict(from_attributes=True)

# Dashboard & Metrics Schemas
class DashboardMetrics(BaseModel):
    total_devices: int
    returned_today: int
    pending_inspection: int
    missing_accessories: int
    cleaning_pending: int
    high_priority_count: int
    critical_count: int
    overdue_followups: int
    ready_for_reissue: int
    turnaround_completion_rate: float
    missing_accessory_rate: float
    damaged_device_rate: float
    cleaning_completion_rate: float
    acknowledgement_completion_rate: float
    avg_turnaround_days: float

# Complete Return Response
class CompleteReturnDetails(BaseModel):
    return_id: str
    device_id: str
    issue_id: Optional[str]
    returned_date: datetime.datetime
    received_by: str
    status: str
    overall_risk_level: str
    returned_accessories: List[dict]
    condition_check: Optional[dict]
    patient_ack: Optional[dict]
    cleaning_record: Optional[dict]
    recommendations: List[RecommendationResponse]
    follow_up_tasks: List[FollowUpTaskResponse]
