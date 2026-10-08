from __future__ import annotations

import logging
import urllib.parse
from typing import Any, Dict

from app.services.pipeline_service import EvidencePipelineService

logger = logging.getLogger("processor_handler")
logger.setLevel(logging.INFO)

pipeline_service = EvidencePipelineService()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler triggered by S3 ObjectCreated events.
    Automatically parses uploaded files and stores normalized evidence.
    """
    logger.info("Received S3 event: %s", event)
    records = event.get("Records", [])
    processed_count = 0

    for record in records:
        s3_data = record.get("s3", {})
        bucket_name = s3_data.get("bucket", {}).get("name")
        raw_key = s3_data.get("object", {}).get("key")

        if not bucket_name or not raw_key:
            continue

        s3_key = urllib.parse.unquote_plus(raw_key)
        logger.info("Processing S3 object s3://%s/%s", bucket_name, s3_key)

        # Expected key pattern: {reviewControlId}/{requestId}/{evidenceId}/{fileName}
        key_parts = s3_key.split("/")
        if len(key_parts) >= 3:
            evidence_id = key_parts[2]
        else:
            logger.warning("Unrecognized S3 key format: %s", s3_key)
            continue

        try:
            processed_record = pipeline_service.process_evidence(
                evidence_id=evidence_id,
                s3_bucket=bucket_name,
                s3_key=s3_key,
            )
            logger.info(
                "Successfully processed evidence %s with status %s",
                evidence_id,
                processed_record.processingStatus,
            )
            processed_count += 1
        except Exception as exc:
            logger.error("Failed to process evidence %s: %s", evidence_id, exc, exc_info=True)

    return {
        "status": "COMPLETED",
        "processedCount": processed_count,
    }
