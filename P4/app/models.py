from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class PersonType(str, Enum):
    EMPLOYEE = "Employee"
    CUSTOMER = "Customer"


class DecisionAction(str, Enum):
    REQUEST_DOCUMENTS = "REQUEST_DOCUMENTS"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class PriorityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CaseStatus(str, Enum):
    NEW = "NEW"
    DOCUMENT_REQUESTED = "DOCUMENT_REQUESTED"
    DOCUMENTS_SUBMITTED = "DOCUMENTS_SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class TaskStatus(str, Enum):
    CREATED = "Created"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    BLOCKED = "Blocked"


class ReminderStatus(str, Enum):
    SCHEDULED = "Scheduled"
    SENT = "Sent"
    CANCELLED = "Cancelled"


class SubjectInfo(BaseModel):
    id: str = Field(..., description="Employee or Customer ID, e.g. EMP-9421 or CUST-5120")
    type: PersonType = Field(default=PersonType.EMPLOYEE, description="Employee or Customer")
    name: str = Field(..., description="Full Name of the individual")
    email: str = Field(..., description="Email address to receive document request notification")
    department_or_account: Optional[str] = Field(default="Engineering / Global Ops", description="Department or Account ref")
    manager_email: Optional[str] = Field(default="manager@company.com", description="Manager or escalation contact email")


class Person3Payload(BaseModel):
    event_id: str = Field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:8].upper()}")
    case_id: Optional[str] = Field(default=None, description="Optional existing case ID, generated if omitted")
    source: str = Field(default="Person 3", description="Originating agent / step")
    risk_score: float = Field(..., ge=0, le=100, description="Risk assessment score (0 to 100). E.g., 72")
    decision: DecisionAction = Field(default=DecisionAction.REQUEST_DOCUMENTS, description="Decision made by Person 3")
    subject: SubjectInfo = Field(..., description="Target employee or customer info")
    requested_documents: List[str] = Field(
        default_factory=lambda: [
            "Government Photo ID / Passport",
            "Proof of Address (Utility Bill < 3 months)",
            "Employment Verification Certificate"
        ],
        description="Documents required for compliance / verification"
    )
    risk_factors: List[str] = Field(
        default_factory=lambda: [
            "Unusual login geography detected",
            "High-risk transaction flag",
            "Outdated KYC profile"
        ],
        description="Risk factors flagged by Person 3"
    )
    notes: Optional[str] = Field(
        default="High risk threshold breached. Immediate KYC/compliance verification required.",
        description="Notes or justification from Person 3"
    )
    sla_hours: int = Field(default=72, description="Target SLA in hours for document submission")


class CaseRecord(BaseModel):
    case_id: str
    subject: SubjectInfo
    risk_score: float
    priority: PriorityLevel
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    deadline_at: datetime
    requested_documents: List[str]
    notes: Optional[str] = None


class TaskRecord(BaseModel):
    task_id: str
    case_id: str
    title: str
    description: str
    priority: PriorityLevel
    status: TaskStatus
    assignee: str
    due_date: datetime
    created_at: datetime


class EmailRecord(BaseModel):
    email_id: str
    case_id: str
    recipient: str
    recipient_name: str
    subject: str
    body_text: str
    body_html: str
    portal_url: str
    sent_at: datetime
    status: str = "Created/Sent"


class ReminderRecord(BaseModel):
    reminder_id: str
    case_id: str
    stage: int
    label: str
    scheduled_for: datetime
    status: ReminderStatus
    channel: str = "Email & In-App Notification"
    description: str


class EscalationRecord(BaseModel):
    escalation_id: str
    case_id: str
    threshold_hours: int
    escalate_to: str
    escalation_priority: PriorityLevel
    condition: str
    trigger_at: datetime
    status: str = "Configured"


class TimelineEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: f"TL-{uuid.uuid4().hex[:6].upper()}")
    case_id: str
    timestamp: datetime
    step_name: str
    action: str
    detail: str
    badge_type: str = "info"  # "high", "success", "warning", "info"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentSubmissionPayload(BaseModel):
    document_names: List[str] = Field(..., description="Names of documents uploaded")
    notes: Optional[str] = Field(default="Documents submitted by recipient via portal")


class Person4ExecutionResponse(BaseModel):
    case: CaseRecord
    task: TaskRecord
    email: EmailRecord
    reminders: List[ReminderRecord]
    escalation: EscalationRecord
    timeline: List[TimelineEntry]
    summary: Dict[str, Any]
