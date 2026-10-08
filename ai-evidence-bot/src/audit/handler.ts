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
