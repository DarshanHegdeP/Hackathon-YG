from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# Document & Table Schemas
# -------------------------------------------------------------
class TableData(BaseModel):
    sheetName: str = Field(..., description="Name of the sheet or table identifier")
    headers: List[str] = Field(default_factory=list, description="Column headers")
    rows: List[List[Any]] = Field(default_factory=list, description="Data rows")


class DocumentMetadata(BaseModel):
    fileName: str
    fileType: str
    fileSizeBytes: int
    pageCount: int = 1
    sha256: str


# -------------------------------------------------------------
# Evidence Request Schemas
# -------------------------------------------------------------
class CreateEvidenceRequestInput(BaseModel):
    reviewControlId: str = Field(..., description="Parent review control ID, e.g. RC-00091")
    title: str = Field(..., description="Title of requested evidence")
    description: Optional[str] = Field(default="", description="Description of the request")
    requiredEvidenceType: str = Field(..., description="Expected document type e.g. PDF, XLSX, CSV")
    assignedOwnerId: str = Field(..., description="Assigned owner identifier")
    dueDate: str = Field(..., description="ISO dueDate string or YYYY-MM-DD")


class EvidenceRequestRecord(BaseModel):
    requestId: str
    reviewControlId: str
    title: str
    description: Optional[str] = ""
    requiredEvidenceType: str
    assignedOwnerId: str
    dueDate: str
    status: Literal["PENDING", "SUBMITTED", "OVERDUE"] = "PENDING"
    evidenceId: Optional[str] = None
    createdAt: str
    updatedAt: str


# -------------------------------------------------------------
# Evidence Upload Schemas
# -------------------------------------------------------------
class UploadUrlRequest(BaseModel):
    reviewControlId: str
    requestId: str
    fileName: str
    fileType: str
    fileSizeBytes: int
    uploadedBy: Optional[str] = Field(default="USER-AML-001", description="Uploader identifier")


class UploadUrlResponse(BaseModel):
    evidenceId: str
    uploadUrl: str
    s3Key: str
    expiresInSeconds: int


class ConfirmUploadRequest(BaseModel):
    s3Bucket: Optional[str] = None
    s3Key: Optional[str] = None


class ConfirmUploadResponse(BaseModel):
    status: str
    evidenceId: str
    processingStatus: str
    message: Optional[str] = None


# -------------------------------------------------------------
# Normalized Evidence & Contract with Person 3 (AI Evaluation)
# -------------------------------------------------------------
class EvidenceMetadata(BaseModel):
    uploadedAt: str
    uploadedBy: str


class Person3EvidenceData(BaseModel):
    evidenceId: str
    reviewControlId: str
    requestId: str
    document: DocumentMetadata
    processingStatus: Literal["PENDING_UPLOAD", "PROCESSING", "PARSED", "FAILED"]
    extractedText: str
    tables: List[TableData] = Field(default_factory=list)
    metadata: EvidenceMetadata


class Person3EvidenceResponse(BaseModel):
    data: Person3EvidenceData


# Internal storage model for Evidence table
class EvidenceRecord(BaseModel):
    evidenceId: str
    reviewControlId: str
    requestId: str
    s3Bucket: str
    s3Key: str
    document: DocumentMetadata
    extractedText: str = ""
    tables: List[TableData] = Field(default_factory=list)
    processingStatus: Literal["PENDING_UPLOAD", "PROCESSING", "PARSED", "FAILED"] = "PENDING_UPLOAD"
    errorMessage: Optional[str] = None
    uploadedBy: str
    uploadedAt: str
