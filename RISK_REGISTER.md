# Operational Risk Register

| Risk | Likelihood | Impact | Severity | Mitigation Strategy | Owner | Monitoring Method |
|---|---|---|---|---|---|---|
| Incorrect Device Identification | Medium | High | HIGH | Implement mandatory barcode scanning with fallback manual serial verification | Field Staff | Check-in validation logs |
| Missing Accessory Overlooked | High | High | HIGH | Automated accessory reconciliation comparing catalog expected items against returned quantity | Inventory Lead | Pre-release rule check |
| Damaged Device Re-issued | Low | Critical | CRITICAL | Mandatory physical condition checklist; major damage triggers automated quarantine recommendation | Biomedical Technician | Clinician review sign-off |
| Unverified Cleaning / Sanitisation | Medium | Critical | CRITICAL | Rule 3 blocks re-issue unless cleaning status is explicitly marked COMPLETED | Sanitisation Lead | Re-issue policy validator |
| Overriding Recommendation Without Justification | Medium | High | HIGH | Server-side validation rejects empty or whitespace override reasons (HTTP 422) | Clinician | Immutable audit log |
| Overdue Follow-up Task Forgotten | Medium | Medium | MEDIUM | Automatic task escalation engine escalates high-priority items due > 24h to Operations Manager | Ops Manager | Daily escalation dashboard |
| Transient Rural Network Outage | High | Low | LOW | Local draft state saving and background API retry mechanisms | Field Staff | Sync status indicator |
| Duplicate Return Submission | Low | Medium | LOW | Unique database constraint and return check-in active return validator | Database Admin | Backend error log |
| Patient Receipt Form Missing | Medium | Medium | MEDIUM | Rule 4 auto-generates follow-up task for field care officer | Field Coordinator | Active task queue |
| Unauthorised Final Decision | Low | Critical | CRITICAL | Role-based access control (RBAC) restricting confirmation/override actions to authorised clinicians | System Admin | User access audit log |
| Inconsistent State During Multi-Step Checkout | Medium | High | HIGH | Pre-evaluation completeness validation gate (HTTP 422) and atomic transactional multi-step checkout endpoint with rollback | Backend Lead | API validation logs |
| False Quarantine of Minor Cosmetic Wear | High | Medium | MEDIUM | Deterministic rule RULE-02B classifying superficial scuffs as LOW risk routine observation without kit quarantine | Biomedical Lead | Evaluation analytics |
