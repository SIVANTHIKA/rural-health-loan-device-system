# System Architecture & Technical Design

## System Architecture Overview

```
                      [ Field Staff / Clinicians / Ops Managers ]
                                          │
                                          ▼
                         [ React + TypeScript + Vite UI ]
                        (Tailwind CSS + Recharts + Lucide Icons)
                                          │
                         [ ErrorBoundary Resilience Layer ]
                                          │
                                 REST APIs / JSON
                                          │
                                          ▼
                         [ Python FastAPI Backend Application ]
                 ┌────────────────────────┴────────────────────────┐
                 ▼                                                 ▼
         [ Auth & RBAC ]                               [ Rule & Risk Engine ]
       (JWT + User Roles)                           (7 Core Rules + Edge Cases)
                 │                                                 │
                 ▼                                                 ▼
      [ Centralized Error Boundary ]               [ Completeness Gate & State Machine ]
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

---

## Deterministic Rule Escalation Triggers & Classification Matrix

| Check Category | Input Threshold Condition | Rule ID | Risk Level | Action & Escalation Trigger | Device Status | SLA / Assignment |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Critical Accessory** | `criticality == 'CRITICAL'` and missing/damaged | `RULE-01` | **HIGH** | Immediate kit quarantine recommendation; urgent replacement order | `QUARANTINED` | 24h SLA ➔ Inventory Lead (auto-escalates to Ops Mgr) |
| **Standard Accessory** | `criticality == 'STANDARD'` and missing/damaged | `RULE-01B` | **LOW** | Routine restock advisory; no device quarantine required | `RETURNED` | 72h SLA ➔ Inventory Clerk |
| **Major Hardware Damage** | `exterior == 'Major damage'` or display cracked / no power / damaged sensor | `RULE-02` | **HIGH** | Immediate device quarantine; urgent biomedical repair order | `QUARANTINED` | 24h SLA ➔ Biomedical Technician |
| **Minor Cosmetic Wear** | `exterior == 'Minor cosmetic wear'` and display/power/sensors functional | `RULE-02B` | **LOW** | Routine cosmetic observation logged; non-escalating clearance | `RETURNED` | Routine Observation ➔ Safe for clinical release |
| **Minor Degradation** | `exterior == 'Minor damage'` or weak battery / partial button responsiveness | `RULE-02C` | **MEDIUM** | Routine maintenance / battery check scheduled prior to re-issue | `INSPECTION_REQUIRED` | 48h SLA ➔ Biomedical Technician (Routine) |
| **Sanitisation Verification** | `cleaning_status != 'COMPLETED'` | `RULE-03` | **MEDIUM** | Decontamination protocol required; blocks release | `INSPECTION_REQUIRED` | 12h SLA ➔ Sanitisation Lead |
| **Patient Ack** | `acknowledgement_status == 'MISSING'` | `RULE-04` | **MEDIUM** | Written/verbal form retrieval follow-up | `INSPECTION_REQUIRED` | 48h SLA ➔ Field Care Coordinator |
| **Compound Multi-Risk** | `total_flagged_issues >= 2` | `RULE-05` | **CRITICAL** | High-level clinical and operational review strictly required | `QUARANTINED` | Critical SLA ➔ Ops Manager & Lead Clinician |
| **Reissue Blocker** | Active follow-up tasks present | `RULE-06` | **HIGH** | Blocks device reissue until maintenance/restock resolved | `QUARANTINED` | Reissue Safety Guard |
| **Mandatory Review** | Recommendations present | `RULE-07` | **CRITICAL** | Requires explicit clinician CONFIRM or OVERRIDE | `IN_REVIEW` | Human-in-the-Loop Governance |

---

## Multi-Step Return Transaction Lifecycle & Completeness Gate

1. **State Machine Integrity**:
   - Statuses follow a deterministic pipeline: `RETURN_PENDING` ➔ `IN_REVIEW` (or `QUARANTINED` / `INSPECTION_REQUIRED`) ➔ `COMPLETED` / `READY_FOR_REISSUE`.
   - Returns marked `COMPLETED` or `READY_FOR_REISSUE` are locked against modification (HTTP 400 State Machine Violation).
2. **Pre-Evaluation Completeness Gate**:
   - Calling `POST /api/returns/{return_id}/evaluate` strictly validates that all 4 checklist steps (Accessories Reconciliation, Hardware Condition, Patient Acknowledgement, Sanitisation Verification) are present.
   - If any step is missing, evaluation is rejected with **HTTP 422 Unprocessable Entity** listing the exact missing sections, eliminating incomplete evaluation states.
3. **Atomic Multi-Step Checkout (`POST /api/returns/{return_id}/checkout`)**:
   - Combines accessory reconciliation, physical condition checklist, patient acknowledgement, cleaning verification, and rule engine evaluation in a single atomic database transaction.
   - If schema validation fails or a constraint violation occurs at any step, the transaction rolls back completely, preventing corrupted or half-saved records.

---

## Error Handling & Resilience Architecture

The system implements a two-tier defense-in-depth error handling strategy designed for rural health field deployments with limited technical support.

### 1. Frontend Client Error Boundary (`ErrorBoundary.tsx`)
- **React Class Lifecycle**: Implements `componentDidCatch` and `getDerivedStateFromError` to intercept unhandled UI runtime exceptions anywhere in the component subtree.
- **Fail-Safe UI**: Replaces broken views with a calm, non-technical diagnostic notice informing field workers that their backend database records remain safe.
- **Self-Healing Recovery Controls**: Offers **Retry View** (component-level state reset) and **Reload Application** (full page reboot) to recover without technical intervention.
- **Telemetry Logging**: Captures error stack traces to console diagnostics for maintenance audit.

### 2. Backend Centralized Exception Boundaries (`main.py`)
- **RequestValidationError Handler**: Traps malformed client payloads, logs field warnings, and responds with HTTP 422 containing standardized `detail`, `error`, `code`, and `path`.
- **StarletteHTTPException Handler**: Formats anticipated clinical business rule rejections (HTTP 400, 401, 403, 404, 409, 422) preserving backward-compatible `detail` strings while appending structured metadata.
- **Global Catch-All Exception Handler**: Intercepts unhandled HTTP 500 runtime faults. Prevents raw database schemas, SQLite errors, or server stack traces from leaking to clients while generating a sanitized error message and logging full tracebacks internally.

### 3. Request / Failure Recovery Flow

```
[ Client Request ]
       │
       ▼
[ FastAPI Route Entry ]
       │
  Valid Schema? ──── NO ───► [ HTTP 422 Validation Error Boundary ] ───► Structured JSON Error
       │ YES
       ▼
[ Business Logic & State Checks ]
       │
  Modifiable State? ─ NO ──► [ HTTP 400 State Violation Boundary ] ───► Refuse Modification
       │ YES
       ▼
[ DB Transaction Block ]
       │
  Transaction Error? ── YES ─► [ db.rollback() + Clean Error ] ───► Prevent Partial Save
       │ NO
       ▼
[ Success Response / UI Render ]
       │
  Render Crash? ───── YES ─► [ React Error Boundary ] ───► Graceful Recovery Card (Retry/Reload)
       │ NO
       ▼
[ Interactive View Displayed ]
```

---

## Testing & Quality Assurance Architecture

The test suite enforces full-stack regression confidence across 5 dedicated test modules with 37 automated tests:

1. **`test_e2e_integration.py` (6 tests)**:
   - End-to-end integration workflows from device issuance to return checkout, rule execution, human review, and audit trail verification.
2. **`test_edge_cases.py` (3 tests)**:
   - Edge case protection against unknown device IDs, duplicate check-in attempts, and whitespace-only override justifications.
3. **`test_validation.py` (9 tests)**:
   - Granular Pydantic schema validation: negative quantities rejected, invalid condition enums blocked, required fields enforced, override rationale character length checked.
4. **`test_state_machine.py` (2 tests)**:
   - Modifiability protection: active returns permit edits; finalized returns (`COMPLETED`, `READY_FOR_REISSUE`, `ARCHIVED`) strictly reject mutations.
5. **`test_transactions.py` (3 tests)**:
   - ACID transaction atomicity during checkout: all 4 checklist steps and evaluation persist together; rollback triggers cleanly on failure.
6. **`test_escalation.py` (4 tests)**:
   - SLA monitoring: tasks before due date stay intact; overdue high/critical items auto-escalate; duplicate escalations prevented; resolved items ignored.
7. **`test_rules.py` (10 tests)**:
   - Granular unit verification of all 10 safety rules (`RULE-01`, `RULE-01B`, `RULE-02`, `RULE-02B`, `RULE-02C`, `RULE-03`, `RULE-04`, `RULE-05`, `RULE-07`).
