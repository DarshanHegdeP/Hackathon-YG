# Person 2: Evidence Collection, Storage & Document Processing Pipeline

Stack 2 of the 4-person fintech hackathon team building an **AI-Powered Evidence Collection Bot** for banking LOD2 control testing.

---

## Boundaries & Architectural Roles

### Strict Single Responsibility (Person 2):
1. **Manages Evidence Requests** linked to `reviewControlId`.
2. **Generates secure S3 presigned PUT URLs** (valid for 15 minutes) so clients upload files directly to S3 without passing bytes through Lambda/server memory.
3. **Automatically parses uploaded documents** (PDF, XLSX, CSV, plain-text) using PyMuPDF and openpyxl/csv table extractors.
4. **Calculates SHA-256 integrity hashes** of documents for audit non-repudiation.
5. **Normalizes evidence** into structured records and stores them in DynamoDB.
6. **Exposes a clean REST API (`GET /evidence/{evidenceId}`)** returning normalized text, tables, and document metadata for **Person 3 (AI Evaluation)** to consume on demand.
7. **Emits audit events** for upload initiation and document processing.

### Boundary Exclusions (What Person 2 Does NOT Implement):
- ❌ **No Review/Control CRUD or review lifecycle** (Owned by Person 1)
- ❌ **No LLM prompting, fact extraction, Jev decision layer, or AI evaluation** (Owned by Person 3)
- ❌ **No EventBridge reminder scheduling, SES email sending, or manager escalations** (Owned by Person 4)

---

## Contract with Person 3 (AI Evaluation)

When Person 3 queries for normalized evidence, Person 2 serves `GET /evidence/{evidenceId}` with this exact response structure:

```json
{
  "data": {
    "evidenceId": "EV-00042",
    "reviewControlId": "RC-00091",
    "requestId": "REQ-00084",
    "document": {
      "fileName": "AML_Q3_Report.pdf",
      "fileType": "application/pdf",
      "fileSizeBytes": 2458102,
      "pageCount": 12,
      "sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a"
    },
    "processingStatus": "PARSED",
    "extractedText": "AML Q3 Compliance Review Report...",
    "tables": [
      {
        "sheetName": "Summary",
        "headers": ["Metric", "Value"],
        "rows": [["TotalAccounts", 4], ["HighRiskThreshold", 75.0]]
      }
    ],
    "metadata": {
      "uploadedAt": "2026-10-08T10:15:00Z",
      "uploadedBy": "USER-AML-001"
    }
  }
}
```

---

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/evidence-requests` | Creates an evidence request linked to a `reviewControlId` |
| `GET` | `/review-controls/{reviewControlId}/evidence-requests` | Lists all evidence requests for a given review control |
| `POST` | `/evidence/upload-url` | Validates input, creates initial `PENDING_UPLOAD` record, and returns 15-minute S3 presigned PUT URL |
| `POST` | `/evidence/{evidenceId}/confirm` | Triggers document parsing pipeline (computes SHA-256, extracts text/tables, transitions status to `PARSED`) |
| `GET` | `/evidence/{evidenceId}` | **Primary endpoint for Person 3**: Returns normalized text, tables, and document metadata |
| `GET` | `/health` | Health check probe |

---

## Local Verification & Testing

### 1. Setup Virtual Environment & Install Dependencies
From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Run the Automated Test Suite (PyTest)
Run all 10 unit and integration tests (PDF extraction, Excel table parsing, CSV parsing, SHA-256 calculation, presigned URL validation, full end-to-end flow, and Lambda handlers):

```powershell
.\.venv\Scripts\pytest.exe -v
```

### 3. Start the API Locally
```powershell
python -m uvicorn app.main:app --reload --port 8000
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

---

## End-to-End Walkthrough (Step-by-Step)

### Step 1: Create an Evidence Request
```bash
curl -X POST "http://localhost:8000/evidence-requests" \
  -H "Content-Type: application/json" \
  -d '{
    "reviewControlId": "RC-00091",
    "title": "AML High Risk Account Sample Records",
    "description": "Provide sample testing records for Q3 high risk customers",
    "requiredEvidenceType": "PDF",
    "assignedOwnerId": "USER-AML-001",
    "dueDate": "2026-10-15"
  }'
```
*Response returns `{ "requestId": "REQ-XXXXX", "status": "PENDING", ... }`*

### Step 2: List Requests for Control
```bash
curl -X GET "http://localhost:8000/review-controls/RC-00091/evidence-requests"
```

### Step 3: Request Presigned Upload URL
```bash
curl -X POST "http://localhost:8000/evidence/upload-url" \
  -H "Content-Type: application/json" \
  -d '{
    "reviewControlId": "RC-00091",
    "requestId": "REQ-00084",
    "fileName": "AML_Q3_Report.pdf",
    "fileType": "application/pdf",
    "fileSizeBytes": 15420,
    "uploadedBy": "USER-AML-001"
  }'
```
*Response returns `{ "evidenceId": "EV-XXXXX", "uploadUrl": "...", "s3Key": "...", "expiresInSeconds": 900 }`*

### Step 4: Client Uploads File Directly to S3 Presigned URL
In production, the client PUTs directly to the S3 bucket URL without passing bytes through Lambda memory. In local development:
```bash
curl -X PUT "http://localhost:8000/mock-upload/RC-00091/REQ-00084/EV-XXXXX/AML_Q3_Report.pdf" \
  --data-binary "@fixtures/AML_Q3_Report.pdf"
```

### Step 5: Confirm Upload & Trigger Processing
```bash
curl -X POST "http://localhost:8000/evidence/EV-XXXXX/confirm"
```
*Parses document, computes SHA-256, stores text and tables, updates EvidenceRequest status to `SUBMITTED`, and returns `{ "status": "SUCCESS", "processingStatus": "PARSED" }`.*

### Step 6: Person 3 Requests the Data
Person 3 pulls the normalized evidence record whenever ready:
```bash
curl -X GET "http://localhost:8000/evidence/EV-XXXXX"
```

---

## AWS SAM Deployment

The project includes a production-ready AWS Serverless Application Model (`template.yaml`) configuration with:
- **AWS API Gateway** REST API with CORS configured.
- **AWS S3 Encrypted Bucket** with AES256 server-side encryption and public access blocked.
- **AWS DynamoDB Tables** (`EvidenceRequests` and `Evidence`) with Pay-Per-Request billing and `reviewControlId-index` GSIs.
- **Lambda Functions**:
  - `ApiFunction`: Handles API Gateway REST endpoints.
  - `ProcessorFunction`: Automatically triggered upon S3 `ObjectCreated:*` events.

### Deploy to AWS:
```bash
sam build
sam deploy --guided
```

### Test Locally with SAM CLI:
```bash
sam local start-api
```
