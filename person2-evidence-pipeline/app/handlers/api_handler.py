from __future__ import annotations

import json
from typing import Any, Dict

from app.schemas import (
    ConfirmUploadRequest,
    CreateEvidenceRequestInput,
    UploadUrlRequest,
)
from app.services.pipeline_service import EvidencePipelineService

pipeline_service = EvidencePipelineService()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point for API Gateway REST API.
    Routes requests to appropriate service actions.
    """
    http_method = event.get("httpMethod", "GET").upper()
    path = event.get("path", "/")
    path_parameters = event.get("pathParameters") or {}
    body_raw = event.get("body")
    body = json.loads(body_raw) if body_raw else {}

    cors_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PUT",
    }

    if http_method == "OPTIONS":
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"status": "ok"})}

    try:
        # GET /health
        if http_method == "GET" and path == "/health":
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": json.dumps({"status": "ok", "service": "person2-evidence-pipeline"}),
            }

        # POST /evidence-requests
        if http_method == "POST" and path == "/evidence-requests":
            input_data = CreateEvidenceRequestInput(**body)
            created = pipeline_service.create_evidence_request(input_data)
            return {
                "statusCode": 201,
                "headers": cors_headers,
                "body": json.dumps(created.model_dump()),
            }

        # GET /review-controls/{reviewControlId}/evidence-requests
        if http_method == "GET" and "review-controls" in path and "evidence-requests" in path:
            control_id = path_parameters.get("reviewControlId")
            if not control_id and len(path.split("/")) > 2:
                control_id = path.split("/")[2]

            records = pipeline_service.list_evidence_requests_for_control(control_id or "")
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": json.dumps([r.model_dump() for r in records]),
            }

        # POST /evidence/upload-url
        if http_method == "POST" and path == "/evidence/upload-url":
            input_data = UploadUrlRequest(**body)
            result = pipeline_service.generate_upload_url(input_data)
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": json.dumps(result.model_dump()),
            }

        # POST /evidence/{evidenceId}/confirm
        if http_method == "POST" and "confirm" in path:
            evidence_id = path_parameters.get("evidenceId")
            if not evidence_id:
                parts = path.strip("/").split("/")
                evidence_id = parts[1] if len(parts) >= 2 else None

            if not evidence_id:
                return {
                    "statusCode": 400,
                    "headers": cors_headers,
                    "body": json.dumps({"detail": "Missing evidenceId in path"}),
                }

            confirm_payload = ConfirmUploadRequest(**body) if body else None
            record = pipeline_service.process_evidence(
                evidence_id=evidence_id,
                s3_bucket=confirm_payload.s3Bucket if confirm_payload else None,
                s3_key=confirm_payload.s3Key if confirm_payload else None,
            )
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": json.dumps(
                    {
                        "status": "SUCCESS" if record.processingStatus == "PARSED" else "FAILED",
                        "evidenceId": record.evidenceId,
                        "processingStatus": record.processingStatus,
                        "message": record.errorMessage or "Evidence processed successfully.",
                    }
                ),
            }

        # GET /evidence/{evidenceId} (Contract for Person 3)
        if http_method == "GET" and "/evidence/" in path:
            evidence_id = path_parameters.get("evidenceId")
            if not evidence_id:
                parts = path.strip("/").split("/")
                evidence_id = parts[1] if len(parts) >= 2 else None

            if not evidence_id:
                return {
                    "statusCode": 400,
                    "headers": cors_headers,
                    "body": json.dumps({"detail": "Missing evidenceId"}),
                }

            result = pipeline_service.get_evidence_for_person3(evidence_id)
            if not result:
                return {
                    "statusCode": 404,
                    "headers": cors_headers,
                    "body": json.dumps({"detail": f"Evidence with ID '{evidence_id}' not found."}),
                }

            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": json.dumps(result.model_dump()),
            }

        return {
            "statusCode": 404,
            "headers": cors_headers,
            "body": json.dumps({"detail": f"Route not found: {http_method} {path}"}),
        }

    except ValueError as val_err:
        return {
            "statusCode": 404,
            "headers": cors_headers,
            "body": json.dumps({"detail": str(val_err)}),
        }
    except Exception as exc:
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"detail": f"Internal Server Error: {str(exc)}"}),
        }
