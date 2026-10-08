# Integration Contracts

Downstream systems (Evidence Pipeline, AI Evaluation, Notifications) will rely on the \`reviewControlId\`.

## 1. Retrieve details for a ReviewControl
\`GET /review-controls/{reviewControlId}\`

Example response:
\`\`\`json
{
  "data": {
    "reviewControlId": "RC-001",
    "reviewId": "REV-001",
    "controlId": "AML-002",
    "controlName": "High Risk Customer Review",
    "controlDescription": "...",
    "riskLevel": "HIGH",
    "ownerId": "USER-AML-001",
    "ownerName": "AML Operations",
    "ownerEmail": "amlops@bank.local",
    "reviewStartDate": "2026-07-01",
    "reviewEndDate": "2026-09-30",
    "requiredEvidenceTypes": ["CUSTOMER_POPULATION"],
    "status": "NOT_STARTED"
  }
}
\`\`\`

## 2. Event Types
The audit log (and eventual event bus) captures these contracts:

### REVIEW_ACTIVATED
\`\`\`json
{
  "eventType": "REVIEW_ACTIVATED",
  "reviewId": "REV-001"
}
\`\`\`

### CONTROL_ATTACHED
\`\`\`json
{
  "eventType": "CONTROL_ATTACHED",
  "reviewId": "REV-001",
  "reviewControlId": "RC-001",
  "controlId": "AML-002"
}
\`\`\`

### OWNER_ASSIGNED
\`\`\`json
{
  "eventType": "OWNER_ASSIGNED",
  "reviewControlId": "RC-001",
  "ownerId": "USER-AML-001"
}
\`\`\`
