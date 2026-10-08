from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import DATA_DIR
from app.schemas import EvidenceRecord, EvidenceRequestRecord


class EvidenceRepository:
    """
    Abstracted persistence layer for EvidenceRequests and Evidence.
    Uses DynamoDB when running with AWS configuration, or local JSON/memory
    store when running offline/locally.
    """

    def __init__(self):
        self.evidence_table_name = os.getenv("DYNAMODB_EVIDENCE_TABLE")
        self.requests_table_name = os.getenv("DYNAMODB_REQUESTS_TABLE")
        self.use_dynamo = bool(self.evidence_table_name and self.requests_table_name and os.getenv("AWS_DEFAULT_REGION"))

        self._lock = threading.Lock()
        self._local_storage_file = DATA_DIR / "local_dynamo_db.json"
        self._local_requests: Dict[str, dict] = {}
        self._local_evidence: Dict[str, dict] = {}

        if not self.use_dynamo:
            self._load_local_storage()

    def _load_local_storage(self) -> None:
        if self._local_storage_file.exists():
            try:
                data = json.loads(self._local_storage_file.read_text(encoding="utf-8"))
                self._local_requests = data.get("requests", {})
                self._local_evidence = data.get("evidence", {})
            except Exception:
                self._local_requests = {}
                self._local_evidence = {}

    def _persist_local_storage(self) -> None:
        try:
            payload = {
                "requests": self._local_requests,
                "evidence": self._local_evidence,
            }
            self._local_storage_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    # -------------------------------------------------------------
    # EvidenceRequests operations
    # -------------------------------------------------------------
    def save_evidence_request(self, record: EvidenceRequestRecord) -> None:
        item = record.model_dump()
        if self.use_dynamo:
            import boto3

            table = boto3.resource("dynamodb").Table(self.requests_table_name)
            table.put_item(Item=item)
        else:
            with self._lock:
                self._local_requests[record.requestId] = item
                self._persist_local_storage()

    def get_evidence_request(self, request_id: str) -> Optional[EvidenceRequestRecord]:
        if self.use_dynamo:
            import boto3

            table = boto3.resource("dynamodb").Table(self.requests_table_name)
            res = table.get_item(Key={"requestId": request_id})
            item = res.get("Item")
            return EvidenceRequestRecord(**item) if item else None
        else:
            with self._lock:
                self._load_local_storage()
                item = self._local_requests.get(request_id)
                return EvidenceRequestRecord(**item) if item else None

    def list_evidence_requests_for_control(self, review_control_id: str) -> List[EvidenceRequestRecord]:
        if self.use_dynamo:
            import boto3
            from boto3.dynamodb.conditions import Key

            table = boto3.resource("dynamodb").Table(self.requests_table_name)
            res = table.query(
                IndexName="reviewControlId-index",
                KeyConditionExpression=Key("reviewControlId").eq(review_control_id),
            )
            items = res.get("Items", [])
            return [EvidenceRequestRecord(**item) for item in items]
        else:
            with self._lock:
                self._load_local_storage()
                items = [
                    EvidenceRequestRecord(**item)
                    for item in self._local_requests.values()
                    if item.get("reviewControlId") == review_control_id
                ]
                return items

    def update_evidence_request_status(self, request_id: str, status: str, evidence_id: Optional[str] = None) -> None:
        if self.use_dynamo:
            import boto3

            table = boto3.resource("dynamodb").Table(self.requests_table_name)
            expr = "SET #st = :st"
            names = {"#st": "status"}
            values = {":st": status}
            if evidence_id:
                expr += ", evidenceId = :eid"
                values[":eid"] = evidence_id

            table.update_item(
                Key={"requestId": request_id},
                UpdateExpression=expr,
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
            )
        else:
            with self._lock:
                self._load_local_storage()
                if request_id in self._local_requests:
                    self._local_requests[request_id]["status"] = status
                    if evidence_id:
                        self._local_requests[request_id]["evidenceId"] = evidence_id
                    self._persist_local_storage()

    # -------------------------------------------------------------
    # Evidence operations
    # -------------------------------------------------------------
    def save_evidence(self, record: EvidenceRecord) -> None:
        item = record.model_dump()
        if self.use_dynamo:
            import boto3

            table = boto3.resource("dynamodb").Table(self.evidence_table_name)
            table.put_item(Item=item)
        else:
            with self._lock:
                self._load_local_storage()
                self._local_evidence[record.evidenceId] = item
                self._persist_local_storage()

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceRecord]:
        if self.use_dynamo:
            import boto3

            table = boto3.resource("dynamodb").Table(self.evidence_table_name)
            res = table.get_item(Key={"evidenceId": evidence_id})
            item = res.get("Item")
            return EvidenceRecord(**item) if item else None
        else:
            with self._lock:
                self._load_local_storage()
                item = self._local_evidence.get(evidence_id)
                return EvidenceRecord(**item) if item else None

    def list_evidence_for_control(self, review_control_id: str) -> List[EvidenceRecord]:
        if self.use_dynamo:
            import boto3
            from boto3.dynamodb.conditions import Key

            table = boto3.resource("dynamodb").Table(self.evidence_table_name)
            res = table.query(
                IndexName="reviewControlId-index",
                KeyConditionExpression=Key("reviewControlId").eq(review_control_id),
            )
            items = res.get("Items", [])
            return [EvidenceRecord(**item) for item in items]
        else:
            with self._lock:
                self._load_local_storage()
                items = [
                    EvidenceRecord(**item)
                    for item in self._local_evidence.values()
                    if item.get("reviewControlId") == review_control_id
                ]
                return items
