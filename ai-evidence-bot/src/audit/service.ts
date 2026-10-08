import { saveAuditEvent, getAuditEventsForEntity } from './repository';
import { generateId } from '../shared/id';
import { AuditEvent } from '../shared/types';

export const auditService = {
  async record(params: Omit<AuditEvent, 'auditId' | 'timestamp'>) {
    const event: AuditEvent = {
      ...params,
      auditId: generateId('AUDIT'),
      timestamp: new Date().toISOString()
    };
    await saveAuditEvent(event);
  },
  async getForEntity(entityId: string) {
    return await getAuditEventsForEntity(entityId);
  }
};
