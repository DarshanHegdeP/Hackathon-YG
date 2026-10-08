export enum ReviewStatus {
  DRAFT = 'DRAFT',
  CONFIGURING = 'CONFIGURING',
  ACTIVE = 'ACTIVE',
  UNDER_REVIEW = 'UNDER_REVIEW',
  COMPLETED = 'COMPLETED',
  ARCHIVED = 'ARCHIVED'
}

export enum ControlRiskLevel {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

export enum ControlStatus {
  ACTIVE = 'ACTIVE',
  INACTIVE = 'INACTIVE'
}

export enum ReviewControlStatus {
  NOT_STARTED = 'NOT_STARTED',
  PENDING_EVIDENCE = 'PENDING_EVIDENCE',
  EVIDENCE_SUBMITTED = 'EVIDENCE_SUBMITTED',
  UNDER_REVIEW = 'UNDER_REVIEW',
  PARTIAL = 'PARTIAL',
  COMPLETE = 'COMPLETE',
  EXCEPTION = 'EXCEPTION',
  CLOSED = 'CLOSED'
}

export interface Review {
  reviewId: string;
  name: string;
  type: string;
  startDate: string;
  endDate: string;
  businessUnits: string[];
  description: string;
  status: ReviewStatus;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface Control {
  controlId: string;
  name: string;
  description: string;
  domain: string;
  riskLevel: ControlRiskLevel;
  frequency: string;
  requiredEvidenceTypes: string[];
  status: ControlStatus;
  createdAt: string;
  updatedAt: string;
}

export interface ReviewControl {
  reviewControlId: string;
  reviewId: string;
  controlId: string;
  ownerId: string;
  status: ReviewControlStatus;
  riskLevel: ControlRiskLevel;
  createdAt: string;
  updatedAt: string;
}

export interface User {
  userId: string;
  name: string;
  email: string;
  role: string;
  businessUnit: string;
  active: boolean;
}

export interface AuditEvent {
  auditId: string;
  entityType: string;
  entityId: string;
  action: string;
  actorType: string;
  actorId: string;
  metadata: any;
  timestamp: string;
}
