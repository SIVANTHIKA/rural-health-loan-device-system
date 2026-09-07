# Relational Database Schema Documentation

## Database Tables Overview

1. `users`: Stores system user accounts, roles (`field_staff`, `clinician`, `ops_manager`, `admin`), and credentials.
2. `devices`: Inventory of portable medical devices (`device_id`, `device_type`, `serial_number`, `status`, `location`).
3. `accessory_catalog`: Master accessory catalog (`accessory_id`, `accessory_name`, `category`, `criticality`).
4. `device_accessories`: Link table defining expected accessory catalog items per device.
5. `device_issue_records`: Patient loan transaction history (`issue_id`, `device_id`, `patient_reference`, `issued_date`, `expected_return_date`, `status`).
6. `device_returns`: Return check-in headers (`return_id`, `device_id`, `issue_id`, `returned_date`, `received_by`, `status`, `overall_risk_level`).
7. `returned_accessories`: Reconciled returned items per check-in (`expected_quantity`, `returned_quantity`, `condition`).
8. `condition_checks`: 8-point physical condition checklist (`exterior`, `screen`, `buttons`, `power`, `battery`, `ports`, `sensors`, `physical_cleanliness`, `notes`).
9. `patient_acknowledgements`: Return receipt forms (`status`, `method`, `recorded_by`, `timestamp`).
10. `cleaning_records`: Sanitisation records (`status`, `completed_by`, `completed_at`).
11. `rules`: Master rule definitions (`rule_id`, `rule_name`, `condition_expr`, `recommendation`, `risk_level`, `required_human_action`).
12. `recommendations`: Evaluated recommendations per return (`recommendation_id`, `return_id`, `rule_id`, `recommendation`, `risk_level`, `status`).
13. `review_decisions`: Human-in-the-Loop decision log (`decision_id`, `recommendation_id`, `reviewer_id`, `decision`, `override_reason`, `timestamp`).
14. `follow_up_tasks`: Task queue with auto-escalation (`task_id`, `return_id`, `device_id`, `issue_type`, `priority`, `assigned_to`, `due_date`, `status`, `escalation_level`, `resolution`).
15. `audit_logs`: Immutable audit log (`log_id`, `user_id`, `user_name`, `user_role`, `action`, `entity`, `entity_id`, `timestamp`, `details`).
