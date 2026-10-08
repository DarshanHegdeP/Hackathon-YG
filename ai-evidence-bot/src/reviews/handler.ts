import { APIGatewayProxyEvent } from 'aws-lambda';
import { success, errorResponse } from '../shared/response';
import { reviewService } from './service';

function getActor(event: APIGatewayProxyEvent) {
  return event.headers['x-actor-id'] || event.headers['X-Actor-Id'] || 'USER-LOD2-001';
}

export async function create(event: APIGatewayProxyEvent) {
  try {
    const data = JSON.parse(event.body || '{}');
    const review = await reviewService.create(data, getActor(event));
    return success(review);
  } catch (err) {
    return errorResponse(err);
  }
}

export async function get(event: APIGatewayProxyEvent) {
  try {
    const reviewId = event.pathParameters?.reviewId;
    if (!reviewId) throw new Error('reviewId required');
    const review = await reviewService.get(reviewId);
    return success(review);
  } catch (err) {
    return errorResponse(err);
  }
}

export async function list(event: APIGatewayProxyEvent) {
  try {
    const filters = event.queryStringParameters || {};
    const reviews = await reviewService.list(filters);
    return success(reviews);
  } catch (err) {
    return errorResponse(err);
  }
}

export async function update(event: APIGatewayProxyEvent) {
  try {
    const reviewId = event.pathParameters?.reviewId;
    if (!reviewId) throw new Error('reviewId required');
    const data = JSON.parse(event.body || '{}');
    const review = await reviewService.update(reviewId, data, getActor(event));
    return success(review);
  } catch (err) {
    return errorResponse(err);
  }
}

export async function activate(event: APIGatewayProxyEvent) {
  try {
    const reviewId = event.pathParameters?.reviewId;
    if (!reviewId) throw new Error('reviewId required');
    const review = await reviewService.activate(reviewId, getActor(event));
    return success(review);
  } catch (err) {
    return errorResponse(err);
  }
}

export async function complete(event: APIGatewayProxyEvent) {
  try {
    const reviewId = event.pathParameters?.reviewId;
    if (!reviewId) throw new Error('reviewId required');
    const review = await reviewService.complete(reviewId, getActor(event));
    return success(review);
  } catch (err) {
    return errorResponse(err);
  }
}
