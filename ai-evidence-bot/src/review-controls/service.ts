import { saveReviewControl, getReviewControl, listReviewControls } from './repository';
import { generateId } from '../shared/id';
import { ReviewControl, ReviewControlStatus, ControlStatus } from '../shared/types';
import { NotFoundError, ValidationError, ConflictError } from '../shared/errors';
import { auditService } from '../audit/service';
import { getReview } from '../reviews/repository';
import { getControl } from '../controls/repository';
import { getUser } from '../users/repository';

export const reviewControlService = {
  async attachControl(reviewId: string, data: any, actorId: string) {
    const { controlId, ownerId } = data;
    const review = await getReview(reviewId);
    if (!review) throw new NotFoundError('Review not found');

    const control = await getControl(controlId);
    if (!control) throw new NotFoundError('Control not found');
    if (control.status !== ControlStatus.ACTIVE) throw new ValidationError('Control is not ACTIVE');

    if (ownerId) {
      const owner = await getUser(ownerId);
      if (!owner) throw new ValidationError('Owner not found');
    }

    const existingRcs = await listReviewControls(reviewId);
    if (existingRcs.find(rc => rc.controlId === controlId)) {
      throw new ConflictError(`Control ${controlId} is already attached to this review`);
    }

    const reviewControlId = generateId('RC');
    const rc: ReviewControl = {
      reviewControlId,
      reviewId,
      controlId,
      ownerId,
      status: ReviewControlStatus.NOT_STARTED,
      riskLevel: control.riskLevel,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    await saveReviewControl(rc);
    
    await auditService.record({
      entityType: 'REVIEW_CONTROL',
      entityId: reviewControlId,
      action: 'CONTROL_ATTACHED',
      actorType: 'USER',
      actorId,
      metadata: { eventType: 'CONTROL_ATTACHED', reviewId, reviewControlId, controlId }
    });
    
    if (ownerId) {
      await auditService.record({
        entityType: 'REVIEW_CONTROL',
        entityId: reviewControlId,
        action: 'OWNER_ASSIGNED',
        actorType: 'USER',
        actorId,
        metadata: { eventType: 'OWNER_ASSIGNED', reviewControlId, ownerId }
      });
    }
    
    return rc;
  },

  async listForReview(reviewId: string) {
    const rcs = await listReviewControls(reviewId);
    const result = [];
    for (const rc of rcs) {
      const c = await getControl(rc.controlId);
      const o = rc.ownerId ? await getUser(rc.ownerId) : null;
      result.push({
        reviewControlId: rc.reviewControlId,
        reviewId: rc.reviewId,
        controlId: rc.controlId,
        controlName: c?.name,
        ownerId: rc.ownerId,
        ownerName: o?.name,
        riskLevel: rc.riskLevel,
        status: rc.status
      });
    }
    return result;
  },

  async getDetails(rcId: string) {
    const rc = await getReviewControl(rcId);
    if (!rc) throw new NotFoundError('ReviewControl not found');
    const r = await getReview(rc.reviewId);
    const c = await getControl(rc.controlId);
    const o = rc.ownerId ? await getUser(rc.ownerId) : null;
    return {
      reviewControlId: rc.reviewControlId,
      reviewId: rc.reviewId,
      controlId: rc.controlId,
      controlName: c?.name,
      controlDescription: c?.description,
      riskLevel: rc.riskLevel,
      ownerId: rc.ownerId,
      ownerName: o?.name,
      ownerEmail: o?.email,
      reviewStartDate: r?.startDate,
      reviewEndDate: r?.endDate,
      requiredEvidenceTypes: c?.requiredEvidenceTypes || [],
      status: rc.status
    };
  },

  async update(rcId: string, data: any, actorId: string) {
    const rc = await getReviewControl(rcId);
    if (!rc) throw new NotFoundError('ReviewControl not found');
    
    if (data.status) {
      const allowed = Object.values(ReviewControlStatus);
      if (!allowed.includes(data.status)) {
        throw new ValidationError(`Invalid status. Allowed: ${allowed.join(',')}`);
      }
      rc.status = data.status;
    }
    
    if (data.ownerId && data.ownerId !== rc.ownerId) {
      const owner = await getUser(data.ownerId);
      if (!owner) throw new ValidationError('Owner not found');
      rc.ownerId = data.ownerId;
      await auditService.record({
        entityType: 'REVIEW_CONTROL',
        entityId: rcId,
        action: 'CONTROL_OWNER_CHANGED',
        actorType: 'USER',
        actorId,
        metadata: { eventType: 'OWNER_ASSIGNED', reviewControlId: rcId, ownerId: rc.ownerId }
      });
    }
    
    rc.updatedAt = new Date().toISOString();
    await saveReviewControl(rc);
    return rc;
  }
};
