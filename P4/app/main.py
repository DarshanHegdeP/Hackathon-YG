import os
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import (
    Person3Payload,
    SubjectInfo,
    PersonType,
    DecisionAction,
    DocumentSubmissionPayload,
    Person4ExecutionResponse,
)
from app.workflow_engine import Person4WorkflowEngine
from app.database import db

app = FastAPI(
    title="Person 4 - Case & Workflow Orchestrator",
    description="Automated intake from Person 3 (risk scoring) to case classification, task creation, employee/customer email notification, reminder scheduling, escalation policies, and audit timeline tracking.",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Person 4 Orchestrator", "cases_count": len(db.list_cases())}


@app.get("/api/sample-payload", response_model=Person3Payload)
def get_sample_payload():
    """
    Returns the exact sample payload corresponding to the diagram:
    Person 3 -> risk_score = 72, REQUEST_DOCUMENTS -> Person 4 -> Employee/Customer
    """
    return Person3Payload(
        source="Person 3",
        risk_score=72.0,
        decision=DecisionAction.REQUEST_DOCUMENTS,
        subject=SubjectInfo(
            id="EMP-7842",
            type=PersonType.EMPLOYEE,
            name="Alex Morgan",
            email="alex.morgan@acmeworks.internal",
            department_or_account="Global Operations & Cloud Infrastructure",
            manager_email="sarah.chen@acmeworks.internal",
        ),
        requested_documents=[
            "Government Photo ID / Passport",
            "Proof of Address (Utility Bill / Bank Statement < 3 months)",
            "Employment Verification Certificate",
        ],
        risk_factors=[
            "Anomalous off-hours credential access",
            "Transaction threshold anomaly (Score: 72)",
            "High-risk IP address range detected",
        ],
        notes="Automated trigger from Person 3: Risk score of 72 breaches acceptable tolerance (Threshold 70). Document reverification mandated.",
        sla_hours=72,
    )


@app.post("/api/webhook/person3", response_model=Person4ExecutionResponse)
def handle_person3_event(payload: Person3Payload, request: Request):
    """
    Primary intake webhook for Person 3.
    Executes the 6-step Person 4 pipeline:
      1. Case → HIGH (or classified based on risk score)
      2. Task → Created
      3. Email → Created/Sent
      4. Reminder → Scheduled
      5. Escalation → Configured
      6. Timeline → Updated
    """
    base_url = str(request.base_url).rstrip("/")
    result = Person4WorkflowEngine.execute(payload, base_url=base_url)
    return result


@app.get("/api/cases")
def list_cases():
    return db.list_cases()


@app.get("/api/cases/{case_id}")
def get_case_details(case_id: str):
    case = db.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return {
        "case": case,
        "tasks": db.get_tasks(case_id),
        "emails": db.get_emails(case_id),
        "reminders": db.get_reminders(case_id),
        "escalation": db.get_escalation(case_id),
        "timeline": db.get_timeline(case_id),
    }


@app.post("/api/portal/{case_id}/submit")
def submit_customer_documents(case_id: str, payload: DocumentSubmissionPayload):
    """
    Simulates the Employee / Customer submitting the requested documents.
    Updates case status to DOCUMENTS_SUBMITTED, marks task COMPLETED,
    cancels pending reminders, and appends to the audit timeline.
    """
    success = db.record_document_submission(case_id, payload.document_names, payload.notes or "")
    if not success:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return {
        "success": True,
        "message": f"Successfully processed {len(payload.document_names)} documents for case {case_id}",
        "case": db.get_case(case_id),
        "timeline": db.get_timeline(case_id),
    }


# Serve the primary dashboard
@app.get("/", response_class=HTMLResponse)
def index_page():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Person 4 Service Running</h1><p>API docs at <a href='/docs'>/docs</a></p>")


# Serve the simulated Employee / Customer upload portal
@app.get("/portal/{case_id}", response_class=HTMLResponse)
def customer_portal_page(case_id: str):
    portal_file = STATIC_DIR / "portal.html"
    if portal_file.exists():
        content = portal_file.read_text(encoding="utf-8").replace("{{CASE_ID}}", case_id)
        return HTMLResponse(content=content)
    return HTMLResponse(content=f"<h1>Customer Portal for Case {case_id}</h1>")
