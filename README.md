# Rural Health Loan-Device Return Checklist & Accessory Reconciliation System

A healthcare operational support system designed for rural health networks lending portable medical devices to patients. It guides authorised field staff through structured return check-ins, accessory reconciliation, condition assessment, sanitisation verification, patient acknowledgement tracking, transparent rule-based risk scoring, human-in-the-loop (HITL) mandatory decision review, auto-escalation, and baseline vs prototype evaluation.

---

## Key Features

- **Accessory Reconciliation**: Automatically calculates expected vs returned items, detecting missing or damaged critical sensors, chargers, tubing, and cables.
- **Structured Condition Checklist**: 8-point physical hardware assessment covering exterior casing, screen, buttons, power systems, ports, and sensors.
- **Transparent Safety Rule Engine**: 7 explainable rules generating risk scores (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) with clear evidence descriptions and required human actions.
- **Mandatory Human-in-the-Loop (HITL) Review**: System strictly prohibits autonomous state transitions to `READY_FOR_REISSUE`. Clinicians must explicitly `CONFIRM` or `OVERRIDE` (with a compulsory non-empty justification) before re-issue clearance.
- **Follow-up Task Engine & Auto-Escalation**: Unresolved tasks automatically escalate to Operations Managers after configured time thresholds (e.g. >24h for HIGH priority). Unresolved items **never** silently disappear.
- **Immutable Audit Log**: Every check-in, recommendation, clinician confirmation, override, and task update is logged with user ID, role, and timestamp.
- **Baseline vs Prototype Experiment**: Built-in quantitative comparison engine comparing historical paper/manual processes against prototype performance across 8 metrics + a 10-category error analysis matrix.

---

## User Roles & Access Control (RBAC)

1. **Field Staff**: Initiate check-ins, complete accessory reconciliation, record condition and sanitisation status.
2. **Clinician / Authorised Reviewer**: Review flagged recommendations, confirm quarantine or release, override recommendations with compulsory justification.
3. **Operations Manager**: Monitor unresolved high-priority/critical tasks, reassign task owners, handle escalated overdue items.
4. **Administrator**: Manage users, device catalogs, rules, and view audit logs.

---

## Tech Stack

- **Backend**: Python 3.13, FastAPI, SQLAlchemy ORM, SQLite Relational Database, Pydantic v2, Pytest
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide Icons
- **Deployment & Infra**: Docker, Docker Compose

---

## Project Structure

```
rural-device-return/
│
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app & router composition
│   │   ├── database.py          # SQLite engine & Session maker
│   │   ├── auth.py              # Authentication & RBAC middleware
│   │   ├── models.py            # 15 SQLAlchemy relational database models
│   │   ├── schemas.py           # Pydantic API validation schemas
│   │   ├── routers/             # API routes (Auth, Devices, Returns, Reviews, Tasks, Dashboard, Audit)
│   │   └── services/            # Rule Engine, Escalation Engine, Baseline Simulation, Audit Logger
│   ├── tests/                   # Pytest test suite (rules, edge cases, overrides)
│   ├── seed_data.py             # Database seeder (50 devices, 100 issue records, 100 returns, edge cases)
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/          # Navbar, RoleSwitcher
│   │   ├── pages/               # Dashboard, ReturnWizard, HumanReviewQueue, TasksEscalation, Inventory, AuditLogs, Experiment
│   │   ├── services/            # API client wrapper
│   │   ├── types.ts             # TypeScript interfaces
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── docs/                        # Architecture, Data Schema, Experiment, Risk Register, User Guide
├── README.md
├── USER_GUIDE.md
├── RISK_REGISTER.md
├── EXPERIMENT.md
├── ARCHITECTURE.md
└── docker-compose.yml
```

---

## Quick Start & Installation

### 1. Backend Setup & Database Seeding

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Seed SQLite database with 50 devices, 100 issue records, 100 returns & edge cases
python seed_data.py

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

Backend Swagger API documentation is available at: `http://localhost:8000/docs`

---

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install npm packages
npm install

# Run Vite dev server
npm run dev
```

Frontend application opens at: `http://localhost:3000`

---

### 3. Running Automated Pytest Suite

```bash
# Run full test suite (rules, edge cases, e2e integration)
cd backend
python -m pytest tests/ -v
```

---

## Verified Edge Cases Handled

1. **Edge Case 1: Missing Critical Accessory** ➔ Flags `HIGH` risk, blocks auto-release, creates 24h SLA inventory replacement task with auto-escalation trigger.
2. **Edge Case 2: Major Physical Damage** ➔ Flags `HIGH`/`CRITICAL` risk, enforces device quarantine, generates 24h biomedical technician task.
3. **Edge Case 3: Cleaning Status Unknown/Pending** ➔ Flags `MEDIUM` risk, blocks re-issue until sanitisation protocol completed.
4. **Edge Case 4: Duplicate Device Return** ➔ Server validation catches active return in progress and rejects duplicate (HTTP 400).
5. **Edge Case 5: Unknown Device ID** ➔ Rejects unregistered device barcodes with clear 404 validation error.
6. **Edge Case 6: Returned Accessory Quantity Greater Than Expected** ➔ Flags excess accessory anomaly for inventory audit.
7. **Edge Case 7: Patient Acknowledgement Missing** ➔ Creates field officer follow-up task to verify verbal/written receipt.
8. **Edge Case 8: Overdue High-Priority Follow-Up** ➔ Auto-escalates overdue task (>24h SLA) to Operations Manager with alert badge and audit trail.
9. **Edge Case 9: Staff Overrides Recommendation Without Reason** ➔ Server rejects override attempts with empty/whitespace reason string (HTTP 422).
10. **Edge Case 10: Missing Standard/Consumable Accessory Only** ➔ Rule `RULE-01B` logs `LOW` risk advisory and 72h restock task without forcing device quarantine.
11. **Edge Case 11: Minor Cosmetic Wear** ➔ Rule `RULE-02B` classifies superficial scuffs/scratches as `LOW` risk routine observation, permitting clinical clearance without emergency quarantine.
12. **Edge Case 12: Inconsistent Multi-Step State Prevention** ➔ Server-side completeness gate (HTTP 422) prevents evaluation of partial submissions, and atomic checkout (`POST /api/returns/{return_id}/checkout`) ensures all-or-nothing transactional integrity.
