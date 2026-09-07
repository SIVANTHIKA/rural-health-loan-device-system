export type UserRole = 'field_staff' | 'clinician' | 'ops_manager' | 'admin';

export interface User {
  id: number;
  username: string;
  name: string;
  role: UserRole;
  active: boolean;
}

export interface AccessoryCatalogItem {
  accessory_id: string;
  accessory_name: string;
  category: string;
  criticality: 'CRITICAL' | 'STANDARD';
}

export interface ReturnedAccessoryItem {
  id?: number;
  accessory_id: string;
  accessory_name: string;
  category: string;
  criticality: 'CRITICAL' | 'STANDARD';
  expected_quantity: number;
  returned_quantity: number;
  condition: 'PRESENT' | 'MISSING' | 'DAMAGED' | 'UNKNOWN';
}

export interface ConditionCheck {
  exterior: 'Good' | 'Minor damage' | 'Major damage';
  screen: 'Good' | 'Cracked' | 'Not functioning';
  buttons: 'Functional' | 'Partially functional' | 'Not functional';
  power: 'Normal' | 'Charging issue' | 'Does not power on';
  battery: 'Normal' | 'Weak' | 'Unknown';
  ports: 'Good' | 'Damaged' | 'Unknown';
  sensors: 'Functional' | 'Damaged' | 'Unknown';
  physical_cleanliness: 'Clean' | 'Needs cleaning' | 'Contaminated/uncertain';
  notes?: string;
  photo_url?: string;
}

export interface PatientAck {
  status: 'RECEIVED' | 'MISSING';
  method: string;
  recorded_by: string;
  timestamp?: string;
  notes?: string;
}

export interface CleaningRecord {
  status: 'COMPLETED' | 'PENDING' | 'FAILED_UNCERTAIN' | 'NOT_APPLICABLE';
  completed_by: string;
  completed_at?: string;
  notes?: string;
}

export interface Recommendation {
  recommendation_id: string;
  return_id: string;
  rule_id?: string;
  recommendation: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'PENDING' | 'CONFIRMED' | 'OVERRIDDEN';
  rule_name?: string;
  required_human_action?: string;
  evidence_description?: string;
  decisions?: Array<{
    decision_id: string;
    decision: 'CONFIRM' | 'OVERRIDE';
    reviewer_id: number;
    override_reason?: string;
    timestamp: string;
  }>;
}

export interface FollowUpTask {
  task_id: string;
  return_id?: string;
  device_id: string;
  issue_type: string;
  description: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  assigned_to: string;
  created_date: string;
  due_date: string;
  status: 'OPEN' | 'IN_PROGRESS' | 'BLOCKED' | 'RESOLVED' | 'ESCALATED' | 'CLOSED';
  escalation_level: number;
  resolution?: string;
  resolved_by?: string;
  resolved_date?: string;
}

export interface DeviceReturnDetails {
  return_id: string;
  device_id: string;
  device?: {
    device_id: string;
    device_type: string;
    serial_number: string;
    status: string;
    location: string;
  };
  issue_id?: string;
  patient_reference: string;
  returned_date: string;
  received_by: string;
  status: string;
  overall_risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  returned_accessories: ReturnedAccessoryItem[];
  condition_check?: ConditionCheck;
  patient_ack?: PatientAck;
  cleaning_record?: CleaningRecord;
  recommendations: Recommendation[];
  follow_up_tasks: FollowUpTask[];
}

export interface DashboardMetrics {
  total_devices: number;
  returned_today: number;
  pending_inspection: number;
  missing_accessories: number;
  cleaning_pending: number;
  high_priority_count: number;
  critical_count: number;
  overdue_followups: number;
  ready_for_reissue: number;
  turnaround_completion_rate: number;
  missing_accessory_rate: number;
  damaged_device_rate: number;
  cleaning_completion_rate: number;
  acknowledgement_completion_rate: number;
  avg_turnaround_days: number;
}

export interface AuditLogItem {
  log_id: number;
  user_id?: number;
  user_name: string;
  user_role: string;
  action: string;
  entity: string;
  entity_id: string;
  timestamp: string;
  details?: string;
}
