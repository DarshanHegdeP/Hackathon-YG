from datetime import datetime, timedelta, timezone
from typing import List, Tuple
import uuid

from app.models import (
    Person3Payload,
    CaseRecord,
    TaskRecord,
    EmailRecord,
    ReminderRecord,
    EscalationRecord,
    TimelineEntry,
    Person4ExecutionResponse,
    PriorityLevel,
    CaseStatus,
    TaskStatus,
    ReminderStatus,
)
from app.database import db


class Person4WorkflowEngine:
    """
    Person 4 Engine
    Receives risk assessment & decision from Person 3:
      - risk_score = 72
      - decision = REQUEST_DOCUMENTS
    Executes the 6-step workflow:
      1. Case → HIGH
      2. Task → Created
      3. Email → Created/Sent
      4. Reminder → Scheduled
      5. Escalation → Configured
      6. Timeline → Updated
    Dispatches outbound communication to Employee / Customer.
    """

    @staticmethod
    def classify_priority(risk_score: float) -> PriorityLevel:
        if risk_score >= 70:
            return PriorityLevel.HIGH
        elif risk_score >= 40:
            return PriorityLevel.MEDIUM
        else:
            return PriorityLevel.LOW

    @classmethod
    def execute(cls, payload: Person3Payload, base_url: str = "http://localhost:8000") -> Person4ExecutionResponse:
        now = datetime.now(timezone.utc)
        case_id = payload.case_id or f"CASE-{uuid.uuid4().hex[:6].upper()}"

        # -------------------------------------------------------------------------
        # STEP 1: Case → HIGH (or classified based on risk score)
        # -------------------------------------------------------------------------
        priority = cls.classify_priority(payload.risk_score)
        deadline = now + timedelta(hours=payload.sla_hours)

        case = CaseRecord(
            case_id=case_id,
            subject=payload.subject,
            risk_score=payload.risk_score,
            priority=priority,
            status=CaseStatus.DOCUMENT_REQUESTED,
            created_at=now,
            updated_at=now,
            deadline_at=deadline,
            requested_documents=payload.requested_documents,
            notes=payload.notes,
        )
        db.save_case(case)

        # -------------------------------------------------------------------------
        # STEP 2: Task → Created
        # -------------------------------------------------------------------------
        task_id = f"TSK-{uuid.uuid4().hex[:6].upper()}"
        task = TaskRecord(
            task_id=task_id,
            case_id=case_id,
            title=f"Review Verification Documents - {payload.subject.name} (Risk: {payload.risk_score})",
            description=(
                f"Verify submitted identity and compliance documents for {payload.subject.type.value} "
                f"{payload.subject.name} ({payload.subject.id}). Flags: {', '.join(payload.risk_factors)}. "
                f"Mandatory documents: {', '.join(payload.requested_documents)}."
            ),
            priority=priority,
            status=TaskStatus.CREATED,
            assignee="Tier-2 Compliance & Risk Operations Queue",
            due_date=deadline,
            created_at=now,
        )
        db.add_task(task)

        # -------------------------------------------------------------------------
        # STEP 3: Email → Created/Sent
        # -------------------------------------------------------------------------
        portal_url = f"{base_url}/portal/{case_id}"
        email_id = f"EML-{uuid.uuid4().hex[:6].upper()}"
        doc_list_html = "".join([f"<li style='margin-bottom:6px;'><strong>{doc}</strong></li>" for doc in payload.requested_documents])
        doc_list_text = "\n".join([f"  - {doc}" for doc in payload.requested_documents])

        email_subject = f"[Action Required] Verification Documents Requested - Ref #{case_id}"
        email_body_text = f"""Hello {payload.subject.name},

As part of our security and regulatory verification procedure, we need you to upload the following documents for your {payload.subject.type.value.lower()} profile:

{doc_list_text}

Target Submission Deadline: {deadline.strftime('%Y-%m-%d %H:%M UTC')} ({payload.sla_hours} hours)

Please submit your documents securely using your dedicated portal:
{portal_url}

If you have any questions or require assistance, please reply directly to this notification.

Best regards,
Risk & Compliance Operations Team
"""

        email_body_html = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background: #ffffff;">
    <div style="display: flex; align-items: center; border-bottom: 2px solid #ef4444; padding-bottom: 16px; margin-bottom: 20px;">
        <h2 style="margin: 0; color: #0f172a; font-size: 20px;">Verification Document Request</h2>
        <span style="margin-left: auto; background: #fee2e2; color: #991b1b; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 700;">PRIORITY: {priority.value}</span>
    </div>
    <p style="color: #334155; font-size: 15px; line-height: 1.6;">Dear <strong>{payload.subject.name}</strong>,</p>
    <p style="color: #475569; font-size: 14px; line-height: 1.6;">
        Our risk and compliance monitoring system requires you to submit verified documentation for reference case <strong>{case_id}</strong>.
    </p>
    <div style="background: #f8fafc; border-left: 4px solid #3b82f6; padding: 14px 18px; margin: 18px 0; border-radius: 0 8px 8px 0;">
        <p style="margin: 0 0 8px 0; font-weight: 600; color: #1e293b; font-size: 14px;">Required Documents:</p>
        <ul style="margin: 0; padding-left: 20px; color: #334155; font-size: 14px;">
            {doc_list_html}
        </ul>
    </div>
    <p style="color: #475569; font-size: 14px; line-height: 1.6;">
        <strong>Deadline:</strong> {deadline.strftime('%b %d, %Y at %H:%M UTC')} ({payload.sla_hours} hours from receipt).
    </p>
    <div style="text-align: center; margin: 28px 0;">
        <a href="{portal_url}" style="background: #2563eb; color: #ffffff; padding: 12px 28px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 8px; display: inline-block; box-shadow: 0 4px 6px -1px rgba(37,99,235,0.2);">
            Upload Requested Documents
        </a>
    </div>
    <p style="font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 16px; margin-top: 24px;">
        Or copy this URL into your browser: <a href="{portal_url}" style="color: #2563eb;">{portal_url}</a><br>
        Case ID: {case_id} | Subject ID: {payload.subject.id} ({payload.subject.type.value})
    </p>
</div>"""

        email = EmailRecord(
            email_id=email_id,
            case_id=case_id,
            recipient=payload.subject.email,
            recipient_name=payload.subject.name,
            subject=email_subject,
            body_text=email_body_text,
            body_html=email_body_html,
            portal_url=portal_url,
            sent_at=now,
            status="Created/Sent",
        )
        db.add_email(email)

        # -------------------------------------------------------------------------
        # STEP 4: Reminder → Scheduled
        # -------------------------------------------------------------------------
        reminders: List[ReminderRecord] = []
        reminder_configs: List[Tuple[int, int, str, str]] = [
            (1, 24, "Follow-Up Reminder 1", "Gentle automated reminder sent if no documents submitted (T+24h)"),
            (2, 48, "Follow-Up Reminder 2 (Urgent)", "Urgent reminder highlighting 24h remaining SLA window (T+48h)"),
            (3, 66, "Final Warning Notice", "Final reminder sent 6h prior to automatic supervisor escalation (T+66h)"),
        ]

        for stage, offset_hours, label, desc in reminder_configs:
            rem_id = f"REM-{uuid.uuid4().hex[:6].upper()}"
            rem_time = now + timedelta(hours=offset_hours)
            rem = ReminderRecord(
                reminder_id=rem_id,
                case_id=case_id,
                stage=stage,
                label=label,
                scheduled_for=rem_time,
                status=ReminderStatus.SCHEDULED,
                description=desc,
            )
            db.add_reminder(rem)
            reminders.append(rem)

        # -------------------------------------------------------------------------
        # STEP 5: Escalation → Configured
        # -------------------------------------------------------------------------
        escalation_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
        escalate_target = payload.subject.manager_email or "senior_compliance_lead@company.com"
        escalation = EscalationRecord(
            escalation_id=escalation_id,
            case_id=case_id,
            threshold_hours=payload.sla_hours,
            escalate_to=escalate_target,
            escalation_priority=PriorityLevel.CRITICAL,
            condition="Unfulfilled document request exceeding SLA deadline or invalid submissions",
            trigger_at=deadline,
            status="Configured",
        )
        db.set_escalation(escalation)

        # -------------------------------------------------------------------------
        # STEP 6: Timeline → Updated
        # -------------------------------------------------------------------------
        timeline_events = [
            TimelineEntry(
                case_id=case_id,
                timestamp=now,
                step_name="Ingestion",
                action="Person 3 Ingestion",
                detail=f"Received risk assessment event from Person 3. Risk Score: {payload.risk_score}, Action: {payload.decision.value}.",
                badge_type="info",
                metadata={"source": "Person 3", "risk_score": payload.risk_score, "decision": payload.decision.value},
            ),
            TimelineEntry(
                case_id=case_id,
                timestamp=now + timedelta(seconds=1),
                step_name="Case Classification",
                action="Case → HIGH",
                detail=f"Classified case priority as {priority.value} based on risk score {payload.risk_score} (Threshold >= 70). Status: DOCUMENT_REQUESTED.",
                badge_type="high" if priority == PriorityLevel.HIGH else "warning",
                metadata={"priority": priority.value, "risk_score": payload.risk_score},
            ),
            TimelineEntry(
                case_id=case_id,
                timestamp=now + timedelta(seconds=2),
                step_name="Task Management",
                action="Task → Created",
                detail=f"Operational task #{task.task_id} generated for compliance investigator queue. Due in {payload.sla_hours} hours.",
                badge_type="info",
                metadata={"task_id": task.task_id, "assignee": task.assignee},
            ),
            TimelineEntry(
                case_id=case_id,
                timestamp=now + timedelta(seconds=3),
                step_name="Communication",
                action="Email → Created/Sent",
                detail=f"Dispatch email #{email.email_id} sent to {payload.subject.name} ({payload.subject.email}) containing document submission portal link.",
                badge_type="success",
                metadata={"email_id": email.email_id, "recipient": email.recipient},
            ),
            TimelineEntry(
                case_id=case_id,
                timestamp=now + timedelta(seconds=4),
                step_name="Scheduling",
                action="Reminder → Scheduled",
                detail=f"Configured {len(reminders)} automated follow-up cadences (T+24h, T+48h, T+66h) with deadline {deadline.strftime('%Y-%m-%d %H:%M UTC')}.",
                badge_type="info",
                metadata={"reminder_count": len(reminders)},
            ),
            TimelineEntry(
                case_id=case_id,
                timestamp=now + timedelta(seconds=5),
                step_name="Policy Enforcement",
                action="Escalation → Configured",
                detail=f"Configured auto-escalation #{escalation.escalation_id} to {escalation.escalate_to} if documents remain unfulfilled at T+{payload.sla_hours}h.",
                badge_type="warning",
                metadata={"escalation_id": escalation.escalation_id, "escalate_to": escalation.escalate_to},
            ),
        ]

        for entry in timeline_events:
            db.add_timeline_entry(entry)

        return Person4ExecutionResponse(
            case=case,
            task=task,
            email=email,
            reminders=reminders,
            escalation=escalation,
            timeline=db.get_timeline(case_id),
            summary={
                "diagram_matching": {
                    "person_3_input": f"risk_score={payload.risk_score}, action={payload.decision.value}",
                    "person_4_execution": {
                        "case": f"{priority.value}",
                        "task": "Created",
                        "email": "Created/Sent",
                        "reminder": f"Scheduled ({len(reminders)} stages)",
                        "escalation": f"Configured (to {escalate_target})",
                        "timeline": f"Updated ({len(timeline_events)} entries recorded)",
                    },
                    "target_recipient": f"{payload.subject.type.value} ({payload.subject.name})",
                }
            },
        )
