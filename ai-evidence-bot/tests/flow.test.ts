import { reviewService } from '../src/reviews/service';
import { controlService } from '../src/controls/service';
import { reviewControlService } from '../src/review-controls/service';
import { auditService } from '../src/audit/service';
import { getUser } from '../src/users/repository';
import * as reviewRepo from '../src/reviews/repository';
import * as controlRepo from '../src/controls/repository';
import * as rcRepo from '../src/review-controls/repository';

jest.mock('../src/reviews/repository');
jest.mock('../src/controls/repository');
jest.mock('../src/review-controls/repository');
jest.mock('../src/users/repository');
jest.mock('../src/audit/service', () => ({
  auditService: { record: jest.fn(), getForEntity: jest.fn() }
}));
jest.mock('../src/shared/id', () => ({
  generateId: (prefix: string) => `${prefix}-123`
}));

describe('Integration Flow Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('Create review', async () => {
    (reviewRepo.saveReview as jest.Mock).mockResolvedValue(undefined);
    const review = await reviewService.create({ name: 'Test', type: 'AML_KYC', startDate: '2026-01-01', endDate: '2026-12-31' }, 'USER-1');
    expect(review.reviewId).toBe('REV-123');
    expect(auditService.record).toHaveBeenCalled();
  });

  it('Invalid review dates on activate', async () => {
    (reviewRepo.getReview as jest.Mock).mockResolvedValue({
      reviewId: 'REV-1', name: 'Test', startDate: '2026-12-31', endDate: '2026-01-01', status: 'DRAFT'
    });
    await expect(reviewService.activate('REV-1', 'USER-1')).rejects.toThrow('endDate must be greater than or equal to startDate');
  });

  it('Attach control', async () => {
    (reviewRepo.getReview as jest.Mock).mockResolvedValue({ reviewId: 'REV-1' });
    (controlRepo.getControl as jest.Mock).mockResolvedValue({ controlId: 'CTRL-1', status: 'ACTIVE' });
    (rcRepo.listReviewControls as jest.Mock).mockResolvedValue([]);
    (rcRepo.saveReviewControl as jest.Mock).mockResolvedValue(undefined);
    (getUser as jest.Mock).mockResolvedValue({ userId: 'USER-1' });

    const rc = await reviewControlService.attachControl('REV-1', { controlId: 'CTRL-1', ownerId: 'USER-1' }, 'USER-1');
    expect(rc.reviewControlId).toBe('RC-123');
    expect(auditService.record).toHaveBeenCalledTimes(2); // attach + owner assigned
  });

  it('Duplicate control attachment', async () => {
    (reviewRepo.getReview as jest.Mock).mockResolvedValue({ reviewId: 'REV-1' });
    (controlRepo.getControl as jest.Mock).mockResolvedValue({ controlId: 'CTRL-1', status: 'ACTIVE' });
    (rcRepo.listReviewControls as jest.Mock).mockResolvedValue([{ controlId: 'CTRL-1' }]);
    
    await expect(reviewControlService.attachControl('REV-1', { controlId: 'CTRL-1' }, 'USER-1')).rejects.toThrow('Control CTRL-1 is already attached to this review');
  });

  it('Invalid owner', async () => {
    (reviewRepo.getReview as jest.Mock).mockResolvedValue({ reviewId: 'REV-1' });
    (controlRepo.getControl as jest.Mock).mockResolvedValue({ controlId: 'CTRL-1', status: 'ACTIVE' });
    (getUser as jest.Mock).mockResolvedValue(null);
    await expect(reviewControlService.attachControl('REV-1', { controlId: 'CTRL-1', ownerId: 'USER-99' }, 'USER-1')).rejects.toThrow('Owner not found');
  });

  it('Activation without controls', async () => {
    (reviewRepo.getReview as jest.Mock).mockResolvedValue({
      reviewId: 'REV-1', name: 'Test', startDate: '2026-01-01', endDate: '2026-12-31', status: 'DRAFT'
    });
    (rcRepo.listReviewControls as jest.Mock).mockResolvedValue([]);
    await expect(reviewService.activate('REV-1', 'USER-1')).rejects.toThrow('at least one ReviewControl must exist to activate');
  });

  it('Activation with unassigned owner', async () => {
    (reviewRepo.getReview as jest.Mock).mockResolvedValue({
      reviewId: 'REV-1', name: 'Test', startDate: '2026-01-01', endDate: '2026-12-31', status: 'DRAFT'
    });
    (rcRepo.listReviewControls as jest.Mock).mockResolvedValue([{ reviewControlId: 'RC-1', controlId: 'CTRL-1', ownerId: null }]);
    await expect(reviewService.activate('REV-1', 'USER-1')).rejects.toThrow('ReviewControl RC-1 is missing an ownerId');
  });

  it('Valid status transition (update review)', async () => {
    (reviewRepo.getReview as jest.Mock).mockResolvedValue({ reviewId: 'REV-1', status: 'DRAFT' });
    (reviewRepo.saveReview as jest.Mock).mockResolvedValue(undefined);
    const rev = await reviewService.update('REV-1', { name: 'New Name' }, 'USER-1');
    expect(rev.name).toBe('New Name');
  });

  it('Invalid status transition (update COMPLETED review)', async () => {
    (reviewRepo.getReview as jest.Mock).mockResolvedValue({ reviewId: 'REV-1', status: 'COMPLETED' });
    await expect(reviewService.update('REV-1', { name: 'New' }, 'USER-1')).rejects.toThrow('Cannot update COMPLETED or ARCHIVED review');
  });
});
