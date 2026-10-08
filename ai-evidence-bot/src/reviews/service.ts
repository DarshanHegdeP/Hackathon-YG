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
        throw new ValidationError(`ReviewControl ${rc.reviewControlId} is missing an ownerId`);
      }
      const c = await getControl(rc.controlId);
      if (!c || c.status !== 'ACTIVE') {
        throw new ValidationError(`Attached control ${rc.controlId} is invalid or inactive`);
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
