import { APIGatewayProxyEvent } from 'aws-lambda';
import { success, errorResponse } from '../shared/response';
import { reviewControlService } from './service';

function getActor(event: APIGatewayProxyEvent) {
  return event.headers['x-actor-id'] || event.headers['X-Actor-Id'] || 'USER-LOD2-001';
}

export async function attachControl(event: APIGatewayProxyEvent) {
  try {
    const reviewId = event.pathParameters?.reviewId;
    if (!reviewId) throw new Error('reviewId required');
    const data = JSON.parse(event.body || '{}');
    const rc = await reviewControlService.attachControl(reviewId, data, getActor(event));
    return success(rc);
  } catch (err) {
    return errorResponse(err);
  }
}

export async function listControlsForReview(event: APIGatewayProxyEvent) {
  try {
    const reviewId = event.pathParameters?.reviewId;
    if (!reviewId) throw new Error('reviewId required');
    const rcs = await reviewControlService.listForReview(reviewId);
    return success(rcs);
  } catch (err) {
    return errorResponse(err);
  }
}

export async function getDetails(event: APIGatewayProxyEvent) {
  try {
    const rcId = event.pathParameters?.reviewControlId;
    if (!rcId) throw new Error('reviewControlId required');
    const details = await reviewControlService.getDetails(rcId);
    return success(details);
  } catch (err) {
    return errorResponse(err);
  }
}

export async function update(event: APIGatewayProxyEvent) {
  try {
    const rcId = event.pathParameters?.reviewControlId;
    if (!rcId) throw new Error('reviewControlId required');
    const data = JSON.parse(event.body || '{}');
    const rc = await reviewControlService.update(rcId, data, getActor(event));
    return success(rc);
  } catch (err) {
    return errorResponse(err);
  }
}
