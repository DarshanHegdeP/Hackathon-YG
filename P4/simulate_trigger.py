#!/usr/bin/env python3
"""
Simulates Person 3 firing a trigger payload into Person 4:
  - risk_score = 72
  - REQUEST_DOCUMENTS
And prints the full Person 4 execution output.
"""
import sys
import httpx

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PAYLOAD = {
    "source": "Person 3",
    "risk_score": 72.0,
    "decision": "REQUEST_DOCUMENTS",
    "subject": {
        "id": "EMP-7842",
        "type": "Employee",
        "name": "Alex Morgan",
        "email": "alex.morgan@acmeworks.internal",
        "department_or_account": "Cloud Infrastructure & Ops",
        "manager_email": "sarah.chen@acmeworks.internal"
    },
    "requested_documents": [
        "Government Photo ID / Passport",
        "Proof of Address (Utility Bill < 3 months)",
        "Employment Verification Certificate"
    ],
    "risk_factors": [
        "Anomalous off-hours credential access",
        "Transaction threshold anomaly (Score: 72 >= 70)",
        "High-risk IP address range detected"
    ],
    "notes": "Automated trigger from Person 3: Risk score of 72 breaches acceptable tolerance (Threshold 70). Document reverification mandated.",
    "sla_hours": 72
}

def main():
    print("=" * 65)
    print("Sending Trigger from Person 3 to Person 4...")
    print(f"Risk Score : {PAYLOAD['risk_score']}")
    print(f"Decision   : {PAYLOAD['decision']}")
    print(f"Recipient  : {PAYLOAD['subject']['name']} ({PAYLOAD['subject']['email']})")
    print("=" * 65)

    try:
        response = httpx.post("http://localhost:8000/api/webhook/person3", json=PAYLOAD, timeout=10.0)
        if response.status_code == 200:
            res = response.json()
            print("\n[SUCCESS] PERSON 4 EXECUTED ALL 6 WORKFLOW ACTIONS SUCCESSFULLY:")
            print("-" * 65)
            print(f"1. Case       -> {res['case']['priority']} (ID: {res['case']['case_id']})")
            print(f"2. Task       -> {res['task']['status']} (ID: {res['task']['task_id']}, Assignee: {res['task']['assignee']})")
            print(f"3. Email      -> {res['email']['status']} (To: {res['email']['recipient']})")
            print(f"4. Reminder   -> Scheduled ({len(res['reminders'])} cadences registered)")
            print(f"5. Escalation -> {res['escalation']['status']} (To: {res['escalation']['escalate_to']} at T+72h)")
            print(f"6. Timeline   -> Updated ({len(res['timeline'])} audit entries recorded)")
            print("-" * 65)
            print(f"Portal Upload URL for Recipient: {res['email']['portal_url']}")
        else:
            print(f"[ERROR] {response.status_code}: {response.text}")
    except httpx.ConnectError:
        print("[WARNING] Could not connect to http://localhost:8000.")
        print("Please ensure the Person 4 server is running via:")
        print("   python run.py")

if __name__ == "__main__":
    main()
