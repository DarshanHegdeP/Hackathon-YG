const fs = require('fs');
const path = require('path');

function write(file, content) {
  fs.writeFileSync(path.join(__dirname, file), content.trim() + '\n');
}

write('src/shared/types.ts', `
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
`);

write('src/shared/errors.ts', `
export class AppError extends Error {
  constructor(public code: string, message: string, public statusCode: number = 400, public details: any = {}) {
    super(message);
    this.name = 'AppError';
  }
}
export class ValidationError extends AppError {
  constructor(message: string, details: any = {}) {
    super('VALIDATION_ERROR', message, 400, details);
  }
}
export class NotFoundError extends AppError {
  constructor(message: string) {
    super('NOT_FOUND', message, 404);
  }
}
export class ConflictError extends AppError {
  constructor(message: string) {
    super('CONFLICT', message, 409);
  }
}
`);

write('src/shared/response.ts', `
import { AppError } from './errors';

export function success(data: any) {
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data })
  };
}

export function errorResponse(err: any) {
  if (err instanceof AppError) {
    return {
      statusCode: err.statusCode,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: {
          code: err.code,
          message: err.message,
          details: err.details
        }
      })
    };
  }
  console.error(err);
  return {
    statusCode: 500,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      error: {
        code: 'INTERNAL_ERROR',
        message: 'An internal error occurred'
      }
    })
  };
}
`);

write('src/shared/id.ts', `
import { v4 as uuidv4 } from 'uuid';
export function generateId(prefix: string): string {
  return \`\${prefix}-\${uuidv4().substring(0, 8)}\`;
}
`);

write('src/shared/db.ts', `
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient } from "@aws-sdk/lib-dynamodb";

const client = new DynamoDBClient({
  endpoint: process.env.AWS_SAM_LOCAL ? "http://127.0.0.1:8000" : undefined,
});
export const docClient = DynamoDBDocumentClient.from(client);
`);

console.log('Shared files generated.');
