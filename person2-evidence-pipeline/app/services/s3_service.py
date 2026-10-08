from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from app.config import LOCAL_BASE_URL, UPLOAD_DIR


class S3StorageService:
    def __init__(self):
        self.bucket_name = os.getenv("EVIDENCE_S3_BUCKET", "lod2-evidence-bucket")
        self.use_aws_s3 = bool(os.getenv("AWS_DEFAULT_REGION") and os.getenv("EVIDENCE_S3_BUCKET"))

    def generate_presigned_put_url(
        self,
        s3_key: str,
        file_type: str,
        expires_in: int = 900,
    ) -> str:
        """
        Generates an S3 presigned PUT URL valid for 15 minutes (900s).
        In local offline mode, returns a mock local PUT URL for development testing.
        """
        if self.use_aws_s3:
            import boto3
            from botocore.config import Config

            s3_client = boto3.client("s3", config=Config(signature_version="s3v4"))
            url = s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                    "ContentType": file_type,
                },
                ExpiresIn=expires_in,
            )
            return url
        else:
            return f"{LOCAL_BASE_URL}/mock-upload/{s3_key}"

    def get_object_bytes(self, s3_bucket: Optional[str], s3_key: str) -> bytes:
        """
        Retrieves object bytes from S3 or local development storage.
        """
        bucket = s3_bucket or self.bucket_name
        if self.use_aws_s3:
            import boto3

            s3_client = boto3.client("s3")
            response = s3_client.get_object(Bucket=bucket, Key=s3_key)
            return response["Body"].read()
        else:
            local_path = UPLOAD_DIR / s3_key.replace("/", "_")
            if not local_path.exists():
                raise FileNotFoundError(f"File not found in local storage: {local_path}")
            return local_path.read_bytes()

    def save_local_mock_upload(self, s3_key: str, content: bytes) -> Path:
        """Saves bytes to local disk when client PUTs to mock upload URL."""
        local_path = UPLOAD_DIR / s3_key.replace("/", "_")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(content)
        return local_path
