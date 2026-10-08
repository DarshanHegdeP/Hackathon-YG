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
