# Person 4 (P4) - Case & Workflow Orchestrator

Implementation of **Person 4** in the automated risk governance pipeline. Person 4 acts as the central case management and operations orchestrator, ingesting risk assessment events from **Person 3**, executing workflow actions, and dispatching communication to the **Employee / Customer**.

---

## 📐 Architecture & Workflow

```text
Person 3
   │
   │ risk_score = 72
   │ REQUEST_DOCUMENTS
   ▼
┌──────────────────────────┐
│       PERSON 4           │
│                          │
│ Case → HIGH              │  (Classifies case priority: risk_score >= 70 -> HIGH)
│ Task → Created           │  (Generates compliance review task for Ops queue)
│ Email → Created/Sent     │  (Dispatches formal document request email)
│ Reminder → Scheduled     │  (Schedules T+24h, T+48h, T+66h follow-up cadences)
│ Escalation → Configured  │  (Sets auto-escalation policy to supervisor at T+72h)
│ Timeline → Updated       │  (Appends complete audit trail in case history)
└──────────────────────────┘
             │
             ▼
      Employee / Customer     (Receives email & uploads files via secure portal)
```

---

## 🚀 Features

1. **Intake Webhook (`POST /api/webhook/person3`)**:
   - Ingests payloads with `risk_score` (e.g. 72) and decision `REQUEST_DOCUMENTS`.
   - Validated with strict Pydantic models.

2. **The 6 Person 4 Workflow Steps**:
   - **Case → HIGH**: Evaluates risk score against threshold tiers (`>= 70` = HIGH, `40-69` = MEDIUM, `< 40` = LOW).
   - **Task → Created**: Assigns operational task to the Tier-2 Compliance queue with due date matching SLA.
   - **Email → Created/Sent**: Generates branded notification email to the Employee/Customer with secure portal URL.
   - **Reminder → Scheduled**: Multi-tier reminder scheduler for automated follow-ups (24h gentle, 48h urgent, 66h final notice).
   - **Escalation → Configured**: Registers automated supervisor escalation if SLA is breached without document submission.
   - **Timeline → Updated**: Immutable, sequential audit trail of all ingestion and orchestration actions.

3. **Interactive Full-Stack Web Dashboard (`http://localhost:8000`)**:
   - Real-time workflow visualizer.
   - 1-Click test trigger for the exact diagram scenario (`risk_score = 72`, `REQUEST_DOCUMENTS`).
   - Live tabbed inspector for Case, Tasks, Email preview, Reminders, Escalations, and Timeline.

4. **Simulated Recipient Portal (`http://localhost:8000/portal/{case_id}`)**:
   - Employee/Customer upload interface where the recipient can upload requested files.
   - Marks the task as completed, cancels remaining reminders, and records the event in the audit timeline.

---

## 🛠️ Project Structure

```text
P4/
├── app/
│   ├── __init__.py
│   ├── models.py            # Pydantic schemas for Person 3, Case, Task, Email, Reminder, Escalation, Timeline
│   ├── workflow_engine.py   # Core logic executing the 6 Person 4 steps
│   ├── database.py          # Thread-safe in-memory state store with case & timeline persistence
│   └── main.py              # FastAPI app with REST endpoints and UI routes
├── static/
│   ├── index.html           # Modern interactive dashboard & workflow visualizer
│   └── portal.html          # Recipient document submission portal
├── tests/
│   ├── __init__.py
│   └── test_workflow.py     # Automated pytest suite verifying all 6 workflow operations
├── run.py                   # Server launcher (uvicorn)
├── simulate_trigger.py      # CLI script simulating Person 3 sending the webhook
├── requirements.txt         # Dependencies
└── README.md                # Project documentation
```

---

## ⚡ Quickstart

### 1. Activate Environment & Run Server

```bash
# Using the pre-configured virtual environment
.venv\Scripts\python.exe run.py
```

Open your browser to:
- **Interactive Dashboard**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Run the Exact Diagram Scenario via CLI

While the server is running in another terminal:

```bash
.venv\Scripts\python.exe simulate_trigger.py
```

### 3. Run Automated Tests

```bash
.venv\Scripts\python.exe -m pytest -v tests/test_workflow.py
```

---

## 📡 API Reference

### 1. Ingest Event from Person 3
- **URL**: `POST /api/webhook/person3`
- **Request Body**:
```json
{
  "source": "Person 3",
  "risk_score": 72.0,
  "decision": "REQUEST_DOCUMENTS",
  "subject": {
    "id": "EMP-7842",
    "type": "Employee",
    "name": "Alex Morgan",
    "email": "alex.morgan@acmeworks.internal",
    "department_or_account": "Cloud Infrastructure",
    "manager_email": "sarah.chen@acmeworks.internal"
  },
  "requested_documents": [
    "Government Photo ID / Passport",
    "Proof of Address (Utility Bill < 3 months)",
    "Employment Verification Certificate"
  ],
  "sla_hours": 72
}
```

- **Response (`200 OK`)**:
```json
{
  "case": {
    "case_id": "CASE-XXXXXX",
    "risk_score": 72.0,
    "priority": "HIGH",
    "status": "DOCUMENT_REQUESTED"
  },
  "task": {
    "task_id": "TSK-XXXXXX",
    "status": "Created",
    "priority": "HIGH"
  },
  "email": {
    "email_id": "EML-XXXXXX",
    "status": "Created/Sent",
    "portal_url": "http://localhost:8000/portal/CASE-XXXXXX"
  },
  "reminders": [
    {"label": "Follow-Up Reminder 1", "status": "Scheduled"},
    {"label": "Follow-Up Reminder 2 (Urgent)", "status": "Scheduled"}
  ],
  "escalation": {
    "escalation_priority": "CRITICAL",
    "escalate_to": "sarah.chen@acmeworks.internal",
    "status": "Configured"
  },
  "timeline": [...]
}
```

### 2. Recipient Portal Submission
- **URL**: `POST /api/portal/{case_id}/submit`
- **Request Body**:
```json
{
  "document_names": ["passport_scan.pdf", "utility_bill.pdf"],
  "notes": "Uploaded latest documents."
}
```
