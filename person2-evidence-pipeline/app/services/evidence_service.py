from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import LOCAL_BASE_URL, PERSON3_EVALUATION_URL, PERSON3_TIMEOUT_SECONDS
from app.schemas import EvidenceRecord, EvidenceUploadRequest, Person3EvaluationRequest, ProcessedEvidenceResponse
from app.services.document_processor import build_normalized_facts, extract_text_from_file
from app.services.storage_service import LocalStorageService


class EvidenceService:
    def __init__(self, storage_service: LocalStorageService | None = None):
        self.storage = storage_service or LocalStorageService()

    def create_upload_url(self, payload: EvidenceUploadRequest) -> dict[str, Any]:
        result = self.storage.generate_upload_url(
            review_id=payload.reviewId,
            control_id=payload.controlId,
            request_id=payload.requestId,
            file_name=payload.fileName,
            owner=payload.owner,
        )

        return {
            "evidenceId": result["evidenceId"],
            "requestId": payload.requestId,
            "s3Key": result["s3Key"],
            "uploadUrl": result["uploadUrl"],
            "expiresAt": result["expiresAt"],
        }

    def process_file(
        self,
        file_content: bytes,
        file_name: str,
        review_id: str,
        control_id: str,
        request_id: str,
        owner: str,
    ) -> ProcessedEvidenceResponse:
        evidence_id = self._generate_evidence_id(file_name)
        s3_key = f"{review_id}/{control_id}/{request_id}/{evidence_id}/{file_name}"
        saved_file = self.storage.save_upload(file_content, s3_key)

        extraction = extract_text_from_file(saved_file)
        normalized_facts = build_normalized_facts(file_name, extraction["raw_text"])

        payload = {
            "evidenceId": evidence_id,
            "requestId": request_id,
            "reviewId": review_id,
            "controlId": control_id,
            "fileName": file_name,
            "s3Key": s3_key,
            "status": "READY_FOR_EVALUATION",
            "extractedText": extraction["raw_text"],
            "normalizedFacts": normalized_facts,
            "aiRequest": {
                "evidenceId": evidence_id,
                "requestId": request_id,
                "reviewId": review_id,
                "controlId": control_id,
                "fileName": file_name,
                "s3Key": s3_key,
                "metadata": {
                    "owner": owner,
                    "uploadedAt": datetime.now(timezone.utc).isoformat(),
                    "documentType": normalized_facts.get("documentType"),
                    "reportingPeriod": normalized_facts.get("reportingPeriod"),
                },
                "controlRequirements": {
                    "requiredEvidence": [
                        "customer_population",
                        "review_completion_report",
                        "sample_review_records",
                        "approval_records",
                        "exception_report",
                    ],
                    "name": "High Risk Customer Review",
                },
                "normalizedFacts": normalized_facts,
            },
        }

        self.storage.save_processed_payload(evidence_id, payload)

        return ProcessedEvidenceResponse(**payload)

    async def send_to_person3(self, processed: ProcessedEvidenceResponse) -> dict[str, Any]:
        if not PERSON3_EVALUATION_URL:
            return {"status": "not_configured"}

        person3_payload = build_person3_payload(processed.model_dump()).model_dump()
        try:
            async with httpx.AsyncClient(timeout=PERSON3_TIMEOUT_SECONDS) as client:
                response = await client.post(PERSON3_EVALUATION_URL, json=person3_payload)
            response.raise_for_status()
            return {"status": "sent", "httpStatusCode": response.status_code}
        except httpx.HTTPStatusError as exc:
            return {"status": "failed", "httpStatusCode": exc.response.status_code}
        except httpx.HTTPError as exc:
            return {"status": "failed", "error": type(exc).__name__}

    @staticmethod
    def _generate_evidence_id(file_name: str) -> str:
        return f"EV-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{hash(file_name) & 0xFFFFFFFF:08x}"


def build_person3_payload(processed_response: dict[str, Any]) -> Person3EvaluationRequest:
    return Person3EvaluationRequest(
        evidenceId=processed_response["evidenceId"],
        requestId=processed_response["requestId"],
        reviewId=processed_response["reviewId"],
        controlId=processed_response["controlId"],
        fileName=processed_response["fileName"],
        s3Key=processed_response["s3Key"],
        extractedText=processed_response["extractedText"],
        metadata=processed_response["aiRequest"]["metadata"],
        normalizedFacts=processed_response["normalizedFacts"],
        controlRequirements=processed_response["aiRequest"]["controlRequirements"],
    )
