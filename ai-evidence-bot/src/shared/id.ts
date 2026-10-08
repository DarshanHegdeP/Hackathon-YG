import { v4 as uuidv4 } from 'uuid';
export function generateId(prefix: string): string {
  return `${prefix}-${uuidv4().substring(0, 8)}`;
}
