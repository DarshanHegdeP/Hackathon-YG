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
