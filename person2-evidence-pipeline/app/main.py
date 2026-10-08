from __future__ import annotations

from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response, status

from app.schemas import (
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    CreateEvidenceRequestInput,
    EvidenceRequestRecord,
    Person3EvidenceResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.pipeline_service import EvidencePipelineService

app = FastAPI(
    title="Person 2: Evidence Collection, Storage & Document Processing Pipeline",
    description="Stack 2 REST API for LOD2 Control Testing. Manages evidence requests, presigned S3 URLs, document parsing (PDF, XLSX, CSV), and normalized evidence extraction for Person 3.",
    version="1.0.0",
)

pipeline_service = EvidencePipelineService()


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "person2-evidence-pipeline"}


# -------------------------------------------------------------
# 1. POST /evidence-requests
# -------------------------------------------------------------
@app.post(
    "/evidence-requests",
    response_model=EvidenceRequestRecord,
    status_code=status.HTTP_201_CREATED,
    tags=["Evidence Requests"],
    summary="Create an evidence request linked to a reviewControlId",
)
def create_evidence_request(payload: CreateEvidenceRequestInput) -> EvidenceRequestRecord:
    return pipeline_service.create_evidence_request(payload)


# -------------------------------------------------------------
# 2. GET /review-controls/{reviewControlId}/evidence-requests
# -------------------------------------------------------------
@app.get(
    "/review-controls/{reviewControlId}/evidence-requests",
    response_model=List[EvidenceRequestRecord],
    tags=["Evidence Requests"],
    summary="List all evidence requests for a given review control",
)
def list_evidence_requests_for_control(reviewControlId: str) -> List[EvidenceRequestRecord]:
    return pipeline_service.list_evidence_requests_for_control(reviewControlId)


# -------------------------------------------------------------
# 3. POST /evidence/upload-url
# -------------------------------------------------------------
@app.post(
    "/evidence/upload-url",
    response_model=UploadUrlResponse,
    tags=["Evidence Upload"],
    summary="Generate secure S3 presigned PUT URL for direct client upload",
)
def generate_upload_url(payload: UploadUrlRequest) -> UploadUrlResponse:
    if payload.fileSizeBytes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fileSizeBytes must be greater than 0",
        )
    return pipeline_service.generate_upload_url(payload)


# -------------------------------------------------------------
# 4. POST /evidence/{evidenceId}/confirm
# -------------------------------------------------------------
@app.post(
    "/evidence/{evidenceId}/confirm",
    response_model=ConfirmUploadResponse,
    tags=["Evidence Upload"],
    summary="Trigger processing/extraction pipeline upon upload confirmation",
)
def confirm_upload(
    evidenceId: str,
    payload: Optional[ConfirmUploadRequest] = None,
) -> ConfirmUploadResponse:
    try:
        s3_bucket = payload.s3Bucket if payload else None
        s3_key = payload.s3Key if payload else None
        record = pipeline_service.process_evidence(
            evidence_id=evidenceId,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
        )
        return ConfirmUploadResponse(
            status="SUCCESS" if record.processingStatus == "PARSED" else "FAILED",
            evidenceId=record.evidenceId,
            processingStatus=record.processingStatus,
            message=record.errorMessage or "Evidence processed successfully.",
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# -------------------------------------------------------------
# 5. GET /evidence/{evidenceId} (Contract for Person 3)
# -------------------------------------------------------------
@app.get(
    "/evidence/{evidenceId}",
    response_model=Person3EvidenceResponse,
    tags=["Person 3 Contract"],
    summary="Returns the full normalized evidence record for Person 3 AI evaluation",
)
def get_evidence_for_person3(evidenceId: str) -> Person3EvidenceResponse:
    result = pipeline_service.get_evidence_for_person3(evidenceId)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence with ID '{evidenceId}' not found.",
        )
    return result


# -------------------------------------------------------------
# Local Dev Helper: Direct PUT mock upload endpoint
# Simulates S3 direct PUT URL without loading bytes into Lambda memory in prod
# -------------------------------------------------------------
@app.put("/mock-upload/{s3_key:path}", tags=["Local Development"])
async def local_mock_put_upload(s3_key: str, request: Request):
    content = await request.body()
    pipeline_service.s3.save_local_mock_upload(s3_key, content)
    return {"status": "UPLOADED", "s3Key": s3_key, "bytesReceived": len(content)}
