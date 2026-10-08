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
