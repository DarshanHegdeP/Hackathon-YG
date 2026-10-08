from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas import (
    ConfirmUploadResponse,
    CreateEvidenceRequestInput,
    DocumentMetadata,
    EvidenceMetadata,
    EvidenceRecord,
    EvidenceRequestRecord,
    Person3EvidenceData,
    Person3EvidenceResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.audit_service import AuditService
from app.services.document_parser import parse_document
from app.services.repository import EvidenceRepository
from app.services.s3_service import S3StorageService


class EvidencePipelineService:
    def __init__(
        self,
        repository: Optional[EvidenceRepository] = None,
        s3_service: Optional[S3StorageService] = None,
        audit_service: Optional[AuditService] = None,
    ):
        self.repo = repository or EvidenceRepository()
        self.s3 = s3_service or S3StorageService()
        self.audit = audit_service or AuditService()

    # -------------------------------------------------------------
    # 1. Evidence Request Management
    # -------------------------------------------------------------
    def create_evidence_request(self, payload: CreateEvidenceRequestInput) -> EvidenceRequestRecord:
        now_iso = datetime.now(timezone.utc).isoformat()
        request_id = f"REQ-{random.randint(10000, 99999)}"

        record = EvidenceRequestRecord(
            requestId=request_id,
            reviewControlId=payload.reviewControlId,
            title=payload.title,
            description=payload.description or "",
            requiredEvidenceType=payload.requiredEvidenceType,
            assignedOwnerId=payload.assignedOwnerId,
            dueDate=payload.dueDate,
            status="PENDING",
            evidenceId=None,
            createdAt=now_iso,
            updatedAt=now_iso,
        )

        self.repo.save_evidence_request(record)
        return record

    def list_evidence_requests_for_control(self, review_control_id: str) -> List[EvidenceRequestRecord]:
        return self.repo.list_evidence_requests_for_control(review_control_id)

    # -------------------------------------------------------------
    # 2. S3 Presigned PUT URL Generation
    # -------------------------------------------------------------
    def generate_upload_url(self, payload: UploadUrlRequest) -> UploadUrlResponse:
        evidence_id = f"EV-{random.randint(10000, 99999)}"
        safe_name = payload.fileName.strip().replace(" ", "_")
        s3_key = f"{payload.reviewControlId}/{payload.requestId}/{evidence_id}/{safe_name}"
        expires_in = 900  # 15 minutes

        upload_url = self.s3.generate_presigned_put_url(
            s3_key=s3_key,
            file_type=payload.fileType,
            expires_in=expires_in,
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        initial_record = EvidenceRecord(
            evidenceId=evidence_id,
            reviewControlId=payload.reviewControlId,
            requestId=payload.requestId,
            s3Bucket=self.s3.bucket_name,
            s3Key=s3_key,
            document=DocumentMetadata(
                fileName=payload.fileName,
                fileType=payload.fileType,
                fileSizeBytes=payload.fileSizeBytes,
                pageCount=1,
                sha256="",
            ),
            extractedText="",
            tables=[],
            processingStatus="PENDING_UPLOAD",
            errorMessage=None,
            uploadedBy=payload.uploadedBy or "SYSTEM",
            uploadedAt=now_iso,
        )

        self.repo.save_evidence(initial_record)

        self.audit.emit_event(
            "EvidenceUploadInitiated",
            {
                "evidenceId": evidence_id,
                "reviewControlId": payload.reviewControlId,
                "requestId": payload.requestId,
                "s3Key": s3_key,
            },
        )

        return UploadUrlResponse(
            evidenceId=evidence_id,
            uploadUrl=upload_url,
            s3Key=s3_key,
            expiresInSeconds=expires_in,
        )

    # -------------------------------------------------------------
    # 3. Document Processing Pipeline
    # -------------------------------------------------------------
    def process_evidence(
        self,
        evidence_id: str,
        s3_bucket: Optional[str] = None,
        s3_key: Optional[str] = None,
    ) -> EvidenceRecord:
        record = self.repo.get_evidence(evidence_id)
        if not record:
            raise ValueError(f"Evidence with ID {evidence_id} not found.")

        target_bucket = s3_bucket or record.s3Bucket
        target_key = s3_key or record.s3Key

        # Update status to PROCESSING
        record.processingStatus = "PROCESSING"
        self.repo.save_evidence(record)

        try:
            file_bytes = self.s3.get_object_bytes(target_bucket, target_key)
        except Exception as exc:
            record.processingStatus = "FAILED"
            record.errorMessage = f"Failed to retrieve file from storage: {str(exc)}"
            self.repo.save_evidence(record)
            self.audit.emit_event(
                "EvidenceProcessingFailed",
                {"evidenceId": evidence_id, "error": record.errorMessage},
            )
            return record

        parse_result = parse_document(
            file_content=file_bytes,
            file_name=record.document.fileName,
            file_type=record.document.fileType,
        )

        # Update document metadata
        record.document.sha256 = parse_result.sha256
        record.document.pageCount = parse_result.page_count
        record.document.fileSizeBytes = len(file_bytes)
        record.extractedText = parse_result.extracted_text
        record.tables = parse_result.tables

        if parse_result.is_success:
            record.processingStatus = "PARSED"
            record.errorMessage = None
            # Update associated request status to SUBMITTED
            self.repo.update_evidence_request_status(
                request_id=record.requestId,
                status="SUBMITTED",
                evidence_id=record.evidenceId,
            )
            self.audit.emit_event(
                "EvidenceProcessingCompleted",
                {
                    "evidenceId": evidence_id,
                    "reviewControlId": record.reviewControlId,
                    "requestId": record.requestId,
                    "sha256": parse_result.sha256,
                    "pageCount": parse_result.page_count,
                    "tableCount": len(parse_result.tables),
                },
            )
        else:
            record.processingStatus = "FAILED"
            record.errorMessage = parse_result.error_message
            self.audit.emit_event(
                "EvidenceProcessingFailed",
                {"evidenceId": evidence_id, "error": parse_result.error_message},
            )

        self.repo.save_evidence(record)
        return record

    # -------------------------------------------------------------
    # 4. GET /evidence/{evidenceId} for Person 3
    # -------------------------------------------------------------
    def get_evidence_for_person3(self, evidence_id: str) -> Optional[Person3EvidenceResponse]:
        record = self.repo.get_evidence(evidence_id)
        if not record:
            return None

        return Person3EvidenceResponse(
            data=Person3EvidenceData(
                evidenceId=record.evidenceId,
                reviewControlId=record.reviewControlId,
                requestId=record.requestId,
                document=record.document,
                processingStatus=record.processingStatus,
                extractedText=record.extractedText,
                tables=record.tables,
                metadata=EvidenceMetadata(
                    uploadedAt=record.uploadedAt,
                    uploadedBy=record.uploadedBy,
                ),
            )
        )
