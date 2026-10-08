from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import LOCAL_BASE_URL, PROCESSED_DIR, UPLOAD_DIR


class LocalStorageService:
    def __init__(self, upload_dir: Path | None = None, processed_dir: Path | None = None):
        self.upload_dir = upload_dir or UPLOAD_DIR
        self.processed_dir = processed_dir or PROCESSED_DIR
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def generate_upload_url(
        self,
        review_id: str,
        control_id: str,
        request_id: str,
        file_name: str,
        owner: str,
    ) -> dict[str, Any]:
        evidence_id = str(uuid4())
        safe_name = self._safe_filename(file_name)
        s3_key = f"{review_id}/{control_id}/{request_id}/{evidence_id}/{safe_name}"

        return {
            "evidenceId": evidence_id,
            "requestId": request_id,
            "s3Key": s3_key,
            "uploadUrl": f"{LOCAL_BASE_URL}/mock-upload/{s3_key}",
            "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
            "localPath": str(self.upload_dir / s3_key.replace("/", "_")),
        }

    def save_upload(self, file_content: bytes, s3_key: str) -> Path:
        destination = self.upload_dir / s3_key.replace("/", "_")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(file_content)
        return destination

    def save_processed_payload(self, evidence_id: str, payload: dict[str, Any]) -> Path:
        output_path = self.processed_dir / f"{evidence_id}.json"
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output_path

    @staticmethod
    def _safe_filename(file_name: str) -> str:
        cleaned = file_name.strip().replace(" ", "_")
        return cleaned or "evidence_file"
