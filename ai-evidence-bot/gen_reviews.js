const fs = require('fs');
const path = require('path');

function write(file, content) {
  fs.writeFileSync(path.join(__dirname, file), content.trim() + '\n');
}

write('src/reviews/repository.ts', `
import { PutCommand, GetCommand, ScanCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from "../shared/db";
import { Review } from "../shared/types";

const TABLE_NAME = process.env.REVIEWS_TABLE || '';

export async function saveReview(review: Review): Promise<void> {
  await docClient.send(new PutCommand({
    TableName: TABLE_NAME,
    Item: review
  }));
}

export async function getReview(reviewId: string): Promise<Review | null> {
  const result = await docClient.send(new GetCommand({
    TableName: TABLE_NAME,
    Key: { reviewId }
  }));
  return (result.Item as Review) || null;
}

export async function listReviews(filters: any): Promise<Review[]> {
  const result = await docClient.send(new ScanCommand({
    TableName: TABLE_NAME
  }));
  let reviews = (result.Items || []) as Review[];
  if (filters.status) reviews = reviews.filter(r => r.status === filters.status);
  if (filters.type) reviews = reviews.filter(r => r.type === filters.type);
  return reviews;
}
`);

write('src/reviews/service.ts', `
import { saveReview, getReview, listReviews } from './repository';
import { generateId } from '../shared/id';
import { Review, ReviewStatus } from '../shared/types';
import { NotFoundError, ValidationError, ConflictError } from '../shared/errors';
import { auditService } from '../audit/service';
import { listReviewControls } from '../review-controls/repository';
import { getControl } from '../controls/repository';

export const reviewService = {
  async create(data: any, actorId: string) {
    const reviewId = generateId('REV');
    const review: Review = {
      reviewId,
      name: data.name,
      type: data.type,
      startDate: data.startDate,
      endDate: data.endDate,
      businessUnits: data.businessUnits || [],
      description: data.description || '',
      status: ReviewStatus.DRAFT,
      createdBy: actorId,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    await saveReview(review);
    await auditService.record({
      entityType: 'REVIEW',
      entityId: reviewId,
      action: 'REVIEW_CREATED',
      actorType: 'USER',
      actorId,
      metadata: { review }
    });
    return review;
  },
  async get(reviewId: string) {
    const review = await getReview(reviewId);
    if (!review) throw new NotFoundError('Review not found');
    return review;
  },
  async list(filters: any) {
    return await listReviews(filters);
  },
  async update(reviewId: string, data: any, actorId: string) {
    const review = await this.get(reviewId);
    if (review.status === ReviewStatus.COMPLETED || review.status === ReviewStatus.ARCHIVED) {
      throw new ValidationError('Cannot update COMPLETED or ARCHIVED review');
    }
    const updated = {
      ...review,
      ...data,
      reviewId,
      updatedAt: new Date().toISOString()
    };
    await saveReview(updated);
    await auditService.record({
      entityType: 'REVIEW',
      entityId: reviewId,
      action: 'REVIEW_UPDATED',
      actorType: 'USER',
      actorId,
      metadata: { changes: data }
    });
    return updated;
  },
  async activate(reviewId: string, actorId: string) {
    const review = await this.get(reviewId);
    if (!review.name || !review.startDate || !review.endDate) {
      throw new ValidationError('name, startDate, and endDate are required to activate');
    }
    if (new Date(review.endDate) < new Date(review.startDate)) {
      throw new ValidationError('endDate must be greater than or equal to startDate');
    }
    const rcs = await listReviewControls(reviewId);
    if (rcs.length === 0) {
      throw new ValidationError('at least one ReviewControl must exist to activate');
    }
    for (const rc of rcs) {
      if (!rc.ownerId) {
        throw new ValidationError(\`ReviewControl \${rc.reviewControlId} is missing an ownerId\`);
      }
      const c = await getControl(rc.controlId);
      if (!c || c.status !== 'ACTIVE') {
        throw new ValidationError(\`Attached control \${rc.controlId} is invalid or inactive\`);
      }
    }
    review.status = ReviewStatus.ACTIVE;
    review.updatedAt = new Date().toISOString();
    await saveReview(review);
    await auditService.record({
      entityType: 'REVIEW',
      entityId: reviewId,
      action: 'REVIEW_ACTIVATED',
      actorType: 'USER',
      actorId,
      metadata: { eventType: 'REVIEW_ACTIVATED', reviewId }
    });
    return review;
  },
  async complete(reviewId: string, actorId: string) {
    const review = await this.get(reviewId);
    if (review.status !== ReviewStatus.UNDER_REVIEW) {
      throw new ValidationError('Only UNDER_REVIEW reviews can be COMPLETED');
    }
    review.status = ReviewStatus.COMPLETED;
    review.updatedAt = new Date().toISOString();
    await saveReview(review);
    await auditService.record({
      entityType: 'REVIEW',
      entityId: reviewId,
      action: 'REVIEW_COMPLETED',
      actorType: 'USER',
      actorId,
      metadata: {}
    });
    return review;
  }
};
`);

write('src/reviews/handler.ts', `
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
`);
console.log('Reviews generated');
