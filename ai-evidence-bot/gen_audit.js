const fs = require('fs');
const path = require('path');

function write(file, content) {
  fs.writeFileSync(path.join(__dirname, file), content.trim() + '\n');
}

write('src/audit/repository.ts', `
import { PutCommand, QueryCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from "../shared/db";
import { AuditEvent } from "../shared/types";

const TABLE_NAME = process.env.AUDIT_EVENTS_TABLE || '';

export async function saveAuditEvent(event: AuditEvent): Promise<void> {
  await docClient.send(new PutCommand({
    TableName: TABLE_NAME,
    Item: event
  }));
}

export async function getAuditEventsForEntity(entityId: string): Promise<AuditEvent[]> {
  const result = await docClient.send(new QueryCommand({
    TableName: TABLE_NAME,
    IndexName: 'entityId-index',
    KeyConditionExpression: 'entityId = :eid',
    ExpressionAttributeValues: {
      ':eid': entityId
    }
  }));
  return (result.Items || []) as AuditEvent[];
}
`);

write('src/audit/service.ts', `
import { saveAuditEvent, getAuditEventsForEntity } from './repository';
import { generateId } from '../shared/id';
import { AuditEvent } from '../shared/types';

export const auditService = {
  async record(params: Omit<AuditEvent, 'auditId' | 'timestamp'>) {
    const event: AuditEvent = {
      ...params,
      auditId: generateId('AUDIT'),
      timestamp: new Date().toISOString()
    };
    await saveAuditEvent(event);
  },
  async getForEntity(entityId: string) {
    return await getAuditEventsForEntity(entityId);
  }
};
`);

write('src/audit/handler.ts', `
import { APIGatewayProxyEvent } from 'aws-lambda';
import { success, errorResponse } from '../shared/response';
import { auditService } from './service';

export async function getReviewAudit(event: APIGatewayProxyEvent) {
  try {
    const reviewId = event.pathParameters?.reviewId;
    if (!reviewId) throw new Error('reviewId required');
    const events = await auditService.getForEntity(reviewId);
    return success(events);
  } catch (err) {
    return errorResponse(err);
  }
}

export async function getReviewControlAudit(event: APIGatewayProxyEvent) {
  try {
    const reviewControlId = event.pathParameters?.reviewControlId;
    if (!reviewControlId) throw new Error('reviewControlId required');
    const events = await auditService.getForEntity(reviewControlId);
    return success(events);
  } catch (err) {
    return errorResponse(err);
  }
}
`);
console.log('Audit generated.');
