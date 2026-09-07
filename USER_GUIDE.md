# User Guide: Rural Health Device Return Checklist System

## Overview
This guide instructs rural healthcare field staff, clinicians, and operations managers on using the system to conduct device return check-ins, reconcile expected accessories, review rule-engine risk scores, and manage follow-up tasks.

---

## 1. Login & Role Selection
1. Open the application at `http://localhost:3000`.
2. Use the **Active Role** selector in the top navbar to switch between persona views:
   - **Field Staff**: Conduct step-by-step return check-ins and submit condition forms.
   - **Clinician / Reviewer**: Access the Human Review Queue to confirm or override system recommendations.
   - **Ops Manager**: Oversee task auto-escalations and device inventory statuses.
   - **Administrator**: Access system configuration and audit trails.

---

## 2. Step-by-Step Device Return Checklist
1. Click **Start Return** from the top menu or dashboard button.
2. **Step 1: Identification**: Type or scan the Device ID (e.g. `DEV-001`) and enter receiving staff name. Click **Start Return Check-in**.
3. **Step 2: Accessory Reconciliation**: Inspect expected vs returned items. Update returned quantity or condition (`PRESENT`, `MISSING`, `DAMAGED`). Click **Save & Continue**.
4. **Step 3: Condition Checklist**: Evaluate exterior casing, screen, buttons, power, battery, ports, and sensors. Enter inspection notes.
5. **Step 4: Patient Acknowledgement**: Confirm whether signed paper form or verbal acknowledgement is received.
6. **Step 5: Cleaning Verification**: Select sanitisation status (`COMPLETED`, `PENDING`, `FAILED_UNCERTAIN`). Click **Run Rule Engine Evaluation**.
7. **Step 6: Risk & Rule Engine Breakdown**: Review evaluated rules, assigned overall risk score (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and generated recommendations.
8. **Step 7: Human Review & Final Decision**:
   - To approve recommendation: Click **Confirm System Recommendation**.
   - To override recommendation: Enter a **compulsory detailed justification reason** and click **Override System Recommendation**.

---

## 3. Managing Follow-Up Tasks & Escalations
1. Open **Follow-ups & Escalation** tab.
2. Filter tasks by status (`OPEN`, `ESCALATED`, `RESOLVED`) or priority (`CRITICAL`, `HIGH`).
3. To resolve a task: Click **Resolve**, type resolution summary, and click **Confirm Resolution**.
4. Overdue tasks are automatically flagged with an **ESCALATED (Level 1)** badge and assigned to the Operations Manager.

---

## 4. Viewing Audit Trail & Baseline Experiment
- Open **Audit Trail** to view timestamped logs of every return check-in, rule evaluation, confirmation, override, and task update.
- Open **Baseline & Experiment** to view before/after quantitative metrics and the 10-category error analysis matrix.
