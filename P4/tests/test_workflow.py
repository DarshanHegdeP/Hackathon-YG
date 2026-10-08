import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    Person3Payload,
    SubjectInfo,
    PersonType,
    DecisionAction,
    PriorityLevel,
    CaseStatus,
    TaskStatus,
    ReminderStatus,
)
from app.workflow_engine import Person4WorkflowEngine
from app.database import db

client = TestClient(app)


def test_person4_diagram_scenario():
    """
    Validates the exact scenario from user's diagram:
    Person 3:
      - risk_score = 72
      - REQUEST_DOCUMENTS
    Person 4:
      - Case -> HIGH
      - Task -> Created
      - Email -> Created/Sent
      - Reminder -> Scheduled
      - Escalation -> Configured
      - Timeline -> Updated
      -> Employee / Customer
    """
    payload = Person3Payload(
        source="Person 3",
        risk_score=72.0,
        decision=DecisionAction.REQUEST_DOCUMENTS,
        subject=SubjectInfo(
            id="EMP-7842",
            type=PersonType.EMPLOYEE,
            name="Alex Morgan",
            email="alex.morgan@acmeworks.internal",
            manager_email="sarah.chen@acmeworks.internal",
        ),
        requested_documents=[
            "Government Photo ID / Passport",
            "Proof of Address (Utility Bill < 3 months)",
            "Employment Verification Certificate",
        ],
        sla_hours=72,
    )

    result = Person4WorkflowEngine.execute(payload, base_url="http://localhost:8000")

    # 1. Case -> HIGH
    assert result.case.priority == PriorityLevel.HIGH
    assert result.case.status == CaseStatus.DOCUMENT_REQUESTED
    assert result.case.risk_score == 72.0

    # 2. Task -> Created
    assert result.task.status == TaskStatus.CREATED
    assert result.task.priority == PriorityLevel.HIGH
    assert "Alex Morgan" in result.task.title

    # 3. Email -> Created/Sent
    assert result.email.status == "Created/Sent"
    assert result.email.recipient == "alex.morgan@acmeworks.internal"
    assert "/portal/" in result.email.portal_url

    # 4. Reminder -> Scheduled
    assert len(result.reminders) >= 2
    for r in result.reminders:
        assert r.status == ReminderStatus.SCHEDULED

    # 5. Escalation -> Configured
    assert result.escalation.status == "Configured"
    assert result.escalation.escalation_priority == PriorityLevel.CRITICAL
    assert result.escalation.escalate_to == "sarah.chen@acmeworks.internal"

    # 6. Timeline -> Updated
    assert len(result.timeline) >= 6
    actions = [t.action for t in result.timeline]
    assert "Case → HIGH" in actions
    assert "Task → Created" in actions
    assert "Email → Created/Sent" in actions
    assert "Reminder → Scheduled" in actions
    assert "Escalation → Configured" in actions


def test_api_webhook_person3():
    """Tests the REST API intake endpoint from Person 3."""
    response = client.post(
        "/api/webhook/person3",
        json={
            "source": "Person 3",
            "risk_score": 72.0,
            "decision": "REQUEST_DOCUMENTS",
            "subject": {
                "id": "CUST-9921",
                "type": "Customer",
                "name": "Jordan Lee",
                "email": "jordan.lee@example.com",
            },
            "requested_documents": ["Passport", "Bank Statement"],
            "sla_hours": 48,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["case"]["priority"] == "HIGH"
    assert data["task"]["status"] == "Created"
    assert data["email"]["status"] == "Created/Sent"
    assert data["escalation"]["status"] == "Configured"
    assert len(data["timeline"]) >= 6


def test_recipient_document_submission():
    """Tests the employee/customer portal submission flow."""
    # Create case
    res = client.post(
        "/api/webhook/person3",
        json={
            "risk_score": 72.0,
            "decision": "REQUEST_DOCUMENTS",
            "subject": {
                "id": "EMP-1001",
                "type": "Employee",
                "name": "Taylor Swift",
                "email": "taylor@company.com",
            },
        },
    )
    case_id = res.json()["case"]["case_id"]

    # Submit documents via portal
    submit_res = client.post(
        f"/api/portal/{case_id}/submit",
        json={
            "document_names": ["Passport_Scan.pdf", "Utility_Bill.pdf"],
            "notes": "Uploaded requested files.",
        },
    )
    assert submit_res.status_code == 200
    sub_data = submit_res.json()
    assert sub_data["case"]["status"] == "DOCUMENTS_SUBMITTED"

    # Verify tasks completed and reminders cancelled
    case_details = client.get(f"/api/cases/{case_id}").json()
    for task in case_details["tasks"]:
        assert task["status"] == "Completed"
    for reminder in case_details["reminders"]:
        assert reminder["status"] == "Cancelled"
