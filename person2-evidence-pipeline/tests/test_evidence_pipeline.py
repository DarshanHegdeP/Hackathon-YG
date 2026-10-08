from __future__ import annotations

import hashlib
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.services.document_parser import compute_sha256, parse_document

client = TestClient(app)
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


# =============================================================
# UNIT TESTS
# =============================================================

def test_sha256_calculation():
    sample_bytes = b"Hello LOD2 Audit Non-Repudiation"
    expected = hashlib.sha256(sample_bytes).hexdigest()
    assert compute_sha256(sample_bytes) == expected


def test_pdf_text_extraction():
    pdf_path = FIXTURES_DIR / "AML_Q3_Report.pdf"
    assert pdf_path.exists(), "AML_Q3_Report.pdf fixture must exist"

    content = pdf_path.read_bytes()
    result = parse_document(file_content=content, file_name="AML_Q3_Report.pdf", file_type="application/pdf")

    assert result.is_success is True
    assert result.page_count >= 1
    assert len(result.sha256) == 64
    assert "AML Q3 Compliance Review Report" in result.extracted_text
    assert "RC-00091" in result.extracted_text
    assert "REQ-00084" in result.extracted_text


def test_excel_table_parsing():
    xlsx_path = FIXTURES_DIR / "high_risk_accounts.xlsx"
    assert xlsx_path.exists(), "high_risk_accounts.xlsx fixture must exist"

    content = xlsx_path.read_bytes()
    result = parse_document(
        file_content=content,
        file_name="high_risk_accounts.xlsx",
        file_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    assert result.is_success is True
    assert len(result.tables) >= 2
    sheet_names = [t.sheetName for t in result.tables]
    assert "HighRiskAccounts" in sheet_names
    assert "Summary" in sheet_names

    accounts_table = next(t for t in result.tables if t.sheetName == "HighRiskAccounts")
    assert "AccountId" in accounts_table.headers
    assert "RiskScore" in accounts_table.headers
    assert len(accounts_table.rows) == 4
    assert accounts_table.rows[0][0] == "ACC-10091"


def test_csv_table_parsing():
    csv_path = FIXTURES_DIR / "exceptions.csv"
    assert csv_path.exists(), "exceptions.csv fixture must exist"

    content = csv_path.read_bytes()
    result = parse_document(file_content=content, file_name="exceptions.csv", file_type="text/csv")

    assert result.is_success is True
    assert len(result.tables) == 1
    table = result.tables[0]
    assert "ExceptionId" in table.headers
    assert "ControlRule" in table.headers
    assert len(table.rows) == 3
    assert table.rows[0][0] == "EX-001"


def test_corrupt_file_graceful_failure():
    corrupt_bytes = b"%PDF-1.4 CORRUPT_RANDOM_BYTES_NOT_A_VALID_PDF"
    result = parse_document(file_content=corrupt_bytes, file_name="corrupt.pdf", file_type="application/pdf")
    # Must handle gracefully without crashing
    assert result.is_success is False
    assert result.error_message is not None
    assert len(result.sha256) == 64


def test_presigned_url_generation_parameters():
    payload = {
        "reviewControlId": "RC-00091",
        "requestId": "REQ-00084",
        "fileName": "AML_Q3_Report.pdf",
        "fileType": "application/pdf",
        "fileSizeBytes": 2458102,
        "uploadedBy": "USER-AML-001",
    }
    response = client.post("/evidence/upload-url", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["evidenceId"].startswith("EV-")
    assert data["expiresInSeconds"] == 900
    assert data["s3Key"] == f"RC-00091/REQ-00084/{data['evidenceId']}/AML_Q3_Report.pdf"
    assert "uploadUrl" in data


# =============================================================
# INTEGRATION TESTS (FULL END-TO-END FLOW)
# =============================================================

def test_end_to_end_evidence_pipeline_pdf():
    # 1. Create Evidence Request
    req_payload = {
        "reviewControlId": "RC-00091",
        "title": "AML High Risk Customer Review Evidence",
        "description": "Please provide the Q3 population report and sampling records",
        "requiredEvidenceType": "PDF",
        "assignedOwnerId": "USER-AML-001",
        "dueDate": "2026-10-15",
    }
    create_req_res = client.post("/evidence-requests", json=req_payload)
    assert create_req_res.status_code == 201
    created_req = create_req_res.json()
    request_id = created_req["requestId"]
    assert created_req["status"] == "PENDING"

    # Verify listing by review control ID
    list_res = client.get("/review-controls/RC-00091/evidence-requests")
    assert list_res.status_code == 200
    matching = [r for r in list_res.json() if r["requestId"] == request_id]
    assert len(matching) == 1

    # 2. Request Presigned Upload URL
    pdf_path = FIXTURES_DIR / "AML_Q3_Report.pdf"
    pdf_bytes = pdf_path.read_bytes()

    upload_url_payload = {
        "reviewControlId": "RC-00091",
        "requestId": request_id,
        "fileName": "AML_Q3_Report.pdf",
        "fileType": "application/pdf",
        "fileSizeBytes": len(pdf_bytes),
        "uploadedBy": "USER-AML-001",
    }
    url_res = client.post("/evidence/upload-url", json=upload_url_payload)
    assert url_res.status_code == 200
    url_data = url_res.json()
    evidence_id = url_data["evidenceId"]
    s3_key = url_data["s3Key"]

    # 3. Simulate Client Direct Upload to Presigned URL
    # (Client PUTs bytes directly to S3 / mock URL)
    put_res = client.put(f"/mock-upload/{s3_key}", content=pdf_bytes)
    assert put_res.status_code == 200

    # 4. Trigger / Confirm Document Processing
    confirm_res = client.post(f"/evidence/{evidence_id}/confirm")
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "SUCCESS"
    assert confirm_res.json()["processingStatus"] == "PARSED"

    # 5. GET /evidence/{evidenceId} - Person 3 Consumption Contract Verification
    person3_res = client.get(f"/evidence/{evidence_id}")
    assert person3_res.status_code == 200
    body = person3_res.json()

    # Exact Schema Verification for Person 3
    assert "data" in body
    data = body["data"]
    assert data["evidenceId"] == evidence_id
    assert data["reviewControlId"] == "RC-00091"
    assert data["requestId"] == request_id
    assert data["processingStatus"] == "PARSED"

    doc = data["document"]
    assert doc["fileName"] == "AML_Q3_Report.pdf"
    assert doc["fileType"] == "application/pdf"
    assert doc["fileSizeBytes"] == len(pdf_bytes)
    assert doc["pageCount"] >= 1
    assert len(doc["sha256"]) == 64

    assert "AML Q3 Compliance Review Report" in data["extractedText"]
    assert isinstance(data["tables"], list)

    metadata = data["metadata"]
    assert metadata["uploadedBy"] == "USER-AML-001"
    assert "uploadedAt" in metadata

    # 6. Verify EvidenceRequest status has transitioned to SUBMITTED
    updated_req_res = client.get("/review-controls/RC-00091/evidence-requests")
    assert updated_req_res.status_code == 200
    updated_req = next(r for r in updated_req_res.json() if r["requestId"] == request_id)
    assert updated_req["status"] == "SUBMITTED"
    assert updated_req["evidenceId"] == evidence_id


def test_end_to_end_evidence_pipeline_xlsx():
    xlsx_path = FIXTURES_DIR / "high_risk_accounts.xlsx"
    xlsx_bytes = xlsx_path.read_bytes()

    # 1. Request Upload URL
    upload_url_payload = {
        "reviewControlId": "RC-00092",
        "requestId": "REQ-00085",
        "fileName": "high_risk_accounts.xlsx",
        "fileType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "fileSizeBytes": len(xlsx_bytes),
        "uploadedBy": "USER-AML-002",
    }
    url_res = client.post("/evidence/upload-url", json=upload_url_payload)
    assert url_res.status_code == 200
    url_data = url_res.json()
    evidence_id = url_data["evidenceId"]
    s3_key = url_data["s3Key"]

    # 2. PUT upload bytes directly
    put_res = client.put(f"/mock-upload/{s3_key}", content=xlsx_bytes)
    assert put_res.status_code == 200

    # 3. Confirm
    confirm_res = client.post(f"/evidence/{evidence_id}/confirm")
    assert confirm_res.status_code == 200

    # 4. GET /evidence/{evidenceId}
    person3_res = client.get(f"/evidence/{evidence_id}")
    assert person3_res.status_code == 200
    data = person3_res.json()["data"]
    assert len(data["tables"]) >= 2
    assert data["tables"][0]["headers"] == ["AccountId", "CustomerName", "RiskScore", "CountryCode", "PEPStatus", "ReviewDate"]


def test_end_to_end_evidence_pipeline_csv():
    csv_path = FIXTURES_DIR / "exceptions.csv"
    csv_bytes = csv_path.read_bytes()

    upload_url_payload = {
        "reviewControlId": "RC-00093",
        "requestId": "REQ-00086",
        "fileName": "exceptions.csv",
        "fileType": "text/csv",
        "fileSizeBytes": len(csv_bytes),
        "uploadedBy": "USER-AML-003",
    }
    url_res = client.post("/evidence/upload-url", json=upload_url_payload)
    assert url_res.status_code == 200
    url_data = url_res.json()
    evidence_id = url_data["evidenceId"]
    s3_key = url_data["s3Key"]

    put_res = client.put(f"/mock-upload/{s3_key}", content=csv_bytes)
    assert put_res.status_code == 200

    confirm_res = client.post(f"/evidence/{evidence_id}/confirm")
    assert confirm_res.status_code == 200

    person3_res = client.get(f"/evidence/{evidence_id}")
    assert person3_res.status_code == 200
    data = person3_res.json()["data"]
    assert len(data["tables"]) == 1
    assert data["tables"][0]["headers"] == ["ExceptionId", "AccountId", "ControlRule", "Severity", "IdentifiedDate", "Resolution"]
    assert len(data["tables"][0]["rows"]) == 3


def test_lambda_api_and_processor_handlers():
    import json
    from app.handlers.api_handler import lambda_handler as api_handler
    from app.handlers.processor_handler import lambda_handler as processor_handler

    # 1. Test API Gateway Lambda Handler - Create Evidence Request
    req_event = {
        "httpMethod": "POST",
        "path": "/evidence-requests",
        "body": json.dumps({
            "reviewControlId": "RC-00099",
            "title": "Lambda Integration Request",
            "requiredEvidenceType": "PDF",
            "assignedOwnerId": "USER-LAMBDA",
            "dueDate": "2026-11-01",
        }),
    }
    res = api_handler(req_event, None)
    assert res["statusCode"] == 201
    created = json.loads(res["body"])
    req_id = created["requestId"]

    # 2. Test API Gateway Lambda Handler - Upload URL
    pdf_bytes = (FIXTURES_DIR / "AML_Q3_Report.pdf").read_bytes()
    upload_event = {
        "httpMethod": "POST",
        "path": "/evidence/upload-url",
        "body": json.dumps({
            "reviewControlId": "RC-00099",
            "requestId": req_id,
            "fileName": "AML_Q3_Report.pdf",
            "fileType": "application/pdf",
            "fileSizeBytes": len(pdf_bytes),
            "uploadedBy": "USER-LAMBDA",
        }),
    }
    url_res = api_handler(upload_event, None)
    assert url_res["statusCode"] == 200
    upload_data = json.loads(url_res["body"])
    evidence_id = upload_data["evidenceId"]
    s3_key = upload_data["s3Key"]

    # Save bytes to simulate S3 upload
    client.put(f"/mock-upload/{s3_key}", content=pdf_bytes)

    # 3. Test S3 Processor Lambda Handler triggered by S3 ObjectCreated event
    s3_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-evidence-bucket"},
                    "object": {"key": s3_key},
                }
            }
        ]
    }
    proc_res = processor_handler(s3_event, None)
    assert proc_res["status"] == "COMPLETED"
    assert proc_res["processedCount"] == 1

    # 4. Test API Gateway Lambda Handler - GET /evidence/{evidenceId} for Person 3
    get_event = {
        "httpMethod": "GET",
        "path": f"/evidence/{evidence_id}",
        "pathParameters": {"evidenceId": evidence_id},
    }
    p3_res = api_handler(get_event, None)
    assert p3_res["statusCode"] == 200
    p3_body = json.loads(p3_res["body"])
    assert p3_body["data"]["evidenceId"] == evidence_id
    assert p3_body["data"]["processingStatus"] == "PARSED"
    assert p3_body["data"]["document"]["fileName"] == "AML_Q3_Report.pdf"

