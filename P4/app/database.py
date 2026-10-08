from datetime import datetime, timezone
import threading
from typing import Dict, List, Optional
from app.models import (
    CaseRecord,
    TaskRecord,
    EmailRecord,
    ReminderRecord,
    EscalationRecord,
    TimelineEntry,
    CaseStatus,
    TaskStatus,
    ReminderStatus,
)


class InMemoryStore:
    def __init__(self):
        self._lock = threading.Lock()
        self.cases: Dict[str, CaseRecord] = {}
        self.tasks: Dict[str, List[TaskRecord]] = {}
        self.emails: Dict[str, List[EmailRecord]] = {}
        self.reminders: Dict[str, List[ReminderRecord]] = {}
        self.escalations: Dict[str, Optional[EscalationRecord]] = {}
        self.timelines: Dict[str, List[TimelineEntry]] = {}

    def save_case(self, case: CaseRecord):
        with self._lock:
            self.cases[case.case_id] = case
            if case.case_id not in self.tasks:
                self.tasks[case.case_id] = []
            if case.case_id not in self.emails:
                self.emails[case.case_id] = []
            if case.case_id not in self.reminders:
                self.reminders[case.case_id] = []
            if case.case_id not in self.timelines:
                self.timelines[case.case_id] = []

    def get_case(self, case_id: str) -> Optional[CaseRecord]:
        with self._lock:
            return self.cases.get(case_id)

    def list_cases(self) -> List[CaseRecord]:
        with self._lock:
            return list(self.cases.values())

    def add_task(self, task: TaskRecord):
        with self._lock:
            if task.case_id not in self.tasks:
                self.tasks[task.case_id] = []
            self.tasks[task.case_id].append(task)

    def get_tasks(self, case_id: str) -> List[TaskRecord]:
        with self._lock:
            return list(self.tasks.get(case_id, []))

    def add_email(self, email: EmailRecord):
        with self._lock:
            if email.case_id not in self.emails:
                self.emails[email.case_id] = []
            self.emails[email.case_id].append(email)

    def get_emails(self, case_id: str) -> List[EmailRecord]:
        with self._lock:
            return list(self.emails.get(case_id, []))

    def add_reminder(self, reminder: ReminderRecord):
        with self._lock:
            if reminder.case_id not in self.reminders:
                self.reminders[reminder.case_id] = []
            self.reminders[reminder.case_id].append(reminder)

    def get_reminders(self, case_id: str) -> List[ReminderRecord]:
        with self._lock:
            return list(self.reminders.get(case_id, []))

    def set_escalation(self, escalation: EscalationRecord):
        with self._lock:
            self.escalations[escalation.case_id] = escalation

    def get_escalation(self, case_id: str) -> Optional[EscalationRecord]:
        with self._lock:
            return self.escalations.get(case_id)

    def add_timeline_entry(self, entry: TimelineEntry):
        with self._lock:
            if entry.case_id not in self.timelines:
                self.timelines[entry.case_id] = []
            self.timelines[entry.case_id].append(entry)

    def get_timeline(self, case_id: str) -> List[TimelineEntry]:
        with self._lock:
            return sorted(
                list(self.timelines.get(case_id, [])),
                key=lambda x: x.timestamp
            )

    def record_document_submission(self, case_id: str, uploaded_files: List[str], notes: str) -> bool:
        with self._lock:
            case = self.cases.get(case_id)
            if not case:
                return False
            
            now = datetime.now(timezone.utc)
            case.status = CaseStatus.DOCUMENTS_SUBMITTED
            case.updated_at = now

            # Complete related tasks
            for t in self.tasks.get(case_id, []):
                t.status = TaskStatus.COMPLETED

            # Cancel remaining reminders
            for r in self.reminders.get(case_id, []):
                if r.status == ReminderStatus.SCHEDULED:
                    r.status = ReminderStatus.CANCELLED

            # Update timeline
            tl_entry = TimelineEntry(
                case_id=case_id,
                timestamp=now,
                step_name="Portal Submission",
                action="Documents Uploaded",
                detail=f"Customer/Employee uploaded {len(uploaded_files)} document(s): {', '.join(uploaded_files)}. Reminders paused.",
                badge_type="success",
                metadata={"files": uploaded_files, "notes": notes}
            )
            self.timelines[case_id].append(tl_entry)
            return True


db = InMemoryStore()
