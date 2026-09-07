# System Architecture & Technical Design

## System Architecture Overview

```
                      [ Field Staff / Clinicians / Ops Managers ]
                                          │
                                          ▼
                         [ React + TypeScript + Vite UI ]
                       (Tailwind CSS + Recharts + Lucide Icons)
                                          │
                                 REST APIs / JSON
                                          ▼
                         [ Python FastAPI Backend Application ]
                 ┌────────────────────────┴────────────────────────┐
                 ▼                                                 ▼
         [ Auth & RBAC ]                               [ Rule & Risk Engine ]
       (JWT + User Roles)                           (7 Core Rules + Edge Cases)
                 │                                                 │
                 └────────────────────────┬────────────────────────┘
                                          ▼
                               [ SQLAlchemy ORM ]
                                          │
                                          ▼
                         [ SQLite Relational Database ]
                 ┌────────────────────────┴────────────────────────┐
                 ▼                                                 ▼
          [ Core Tables ]                                    [ Audit Trail ]
    (devices, returns, tasks, etc.)                    (Immutable Event Log)
```

---

## Data Flow Diagram

```
Issue Record (Device Issued)
     ↓
Device Return Check-in (Scan ID)
     ↓
Accessory Reconciliation (Expected vs Returned)
     ↓
Condition Check (8 Hardware Parameters)
     ↓
Patient Acknowledgement Verification
     ↓
Sanitisation & Cleaning Check
     ↓
Transparent Rule Engine Evaluation
     ↓
Risk Classification (LOW / MEDIUM / HIGH / CRITICAL)
     ↓
Recommendation Generation
     ↓
Human-in-the-Loop Clinician Review (CONFIRM / OVERRIDE with compulsory reason)
     ↓
Follow-Up Task Creation & Auto-Escalation Engine
     ↓
Final Device Status Update (READY_FOR_REISSUE / QUARANTINED / MAINTENANCE)
     ↓
Immutable Audit Log Storage
```

---

## Safety & Governance Boundaries

1. **Autonomous Decision Prohibition**: The rule engine generates explainable recommendations, evidence, and risk scores, but **never** mutates device status to `READY_FOR_REISSUE` autonomously when safety flags exist.
2. **Compulsory Override Reason**: Overrides require a non-empty, detailed justification text string. Blank or whitespace override reasons are rejected server-side (HTTP 422).
3. **No Disappearing Unresolved Issues**: Follow-up tasks remain active in the queue until formally resolved or closed by authorised personnel. Overdue items auto-escalate to Operations Managers.
4. **Patient Privacy**: Patient identity is referenced exclusively via synthetic Patient Reference IDs (e.g. `PAT-9021`). No unnecessary personally identifiable information (PII) is stored.
