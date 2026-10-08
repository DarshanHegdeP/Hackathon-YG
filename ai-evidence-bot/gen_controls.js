const fs = require('fs');
const path = require('path');

function write(file, content) {
  fs.writeFileSync(path.join(__dirname, file), content.trim() + '\n');
}

write('src/controls/repository.ts', `
import { PutCommand, GetCommand, ScanCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from "../shared/db";
import { Control } from "../shared/types";

const TABLE_NAME = process.env.CONTROLS_TABLE || '';

export async function saveControl(control: Control): Promise<void> {
  await docClient.send(new PutCommand({
    TableName: TABLE_NAME,
    Item: control
  }));
}

export async function getControl(controlId: string): Promise<Control | null> {
  const result = await docClient.send(new GetCommand({
    TableName: TABLE_NAME,
    Key: { controlId }
  }));
  return (result.Item as Control) || null;
}

export async function listControls(filters: any): Promise<Control[]> {
  const result = await docClient.send(new ScanCommand({
    TableName: TABLE_NAME
  }));
  let controls = (result.Items || []) as Control[];
  if (filters.domain) controls = controls.filter(c => c.domain === filters.domain);
  if (filters.riskLevel) controls = controls.filter(c => c.riskLevel === filters.riskLevel);
  if (filters.status) controls = controls.filter(c => c.status === filters.status);
  return controls;
}
`);

write('src/controls/service.ts', `
import { saveControl, getControl, listControls } from './repository';
import { generateId } from '../shared/id';
import { Control, ControlStatus } from '../shared/types';
import { NotFoundError } from '../shared/errors';
import { auditService } from '../audit/service';

export const controlService = {
  async create(data: any, actorId: string) {
    const controlId = data.controlId || generateId('CTRL');
    const control: Control = {
      controlId,
      name: data.name,
      description: data.description,
      domain: data.domain,
      riskLevel: data.riskLevel,
      frequency: data.frequency,
      requiredEvidenceTypes: data.requiredEvidenceTypes || [],
      status: data.status || ControlStatus.ACTIVE,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    await saveControl(control);
    await auditService.record({
      entityType: 'CONTROL',
      entityId: control.controlId,
      action: 'CONTROL_CREATED',
      actorType: 'USER',
      actorId,
      metadata: { control }
    });
    return control;
  },
  async get(controlId: string) {
    const control = await getControl(controlId);
    if (!control) throw new NotFoundError('Control not found');
    return control;
  },
  async update(controlId: string, data: any, actorId: string) {
    const control = await this.get(controlId);
    const updated = {
      ...control,
      ...data,
      controlId,
      updatedAt: new Date().toISOString()
    };
    await saveControl(updated);
    await auditService.record({
      entityType: 'CONTROL',
      entityId: controlId,
      action: 'CONTROL_UPDATED',
      actorType: 'USER',
      actorId,
      metadata: { changes: data }
    });
    return updated;
  },
  async list(filters: any) {
    return await listControls(filters);
  }
};
`);

write('src/controls/handler.ts', `
import { APIGatewayProxyEvent } from 'aws-lambda';
import { success, errorResponse } from '../shared/response';
import { controlService } from './service';

function getActor(event: APIGatewayProxyEvent) {
  return event.headers['x-actor-id'] || event.headers['X-Actor-Id'] || 'USER-LOD2-001';
}

export async function create(event: APIGatewayProxyEvent) {
  try {
    const data = JSON.parse(event.body || '{}');
    const control = await controlService.create(data, getActor(event));
    return success(control);
  } catch (err) {
    return errorResponse(err);
  }
}

export async function get(event: APIGatewayProxyEvent) {
  try {
    const controlId = event.pathParameters?.controlId;
    if (!controlId) throw new Error('controlId required');
    const control = await controlService.get(controlId);
    return success(control);
  } catch (err) {
    return errorResponse(err);
  }
}

export async function update(event: APIGatewayProxyEvent) {
  try {
    const controlId = event.pathParameters?.controlId;
    if (!controlId) throw new Error('controlId required');
    const data = JSON.parse(event.body || '{}');
    const control = await controlService.update(controlId, data, getActor(event));
    return success(control);
  } catch (err) {
    return errorResponse(err);
  }
}

export async function list(event: APIGatewayProxyEvent) {
  try {
    const filters = event.queryStringParameters || {};
    const controls = await controlService.list(filters);
    return success(controls);
  } catch (err) {
    return errorResponse(err);
  }
}
`);
console.log('Controls generated');
