export class AppError extends Error {
  constructor(public code: string, message: string, public statusCode: number = 400, public details: any = {}) {
    super(message);
    this.name = 'AppError';
  }
}
export class ValidationError extends AppError {
  constructor(message: string, details: any = {}) {
    super('VALIDATION_ERROR', message, 400, details);
  }
}
export class NotFoundError extends AppError {
  constructor(message: string) {
    super('NOT_FOUND', message, 404);
  }
}
export class ConflictError extends AppError {
  constructor(message: string) {
    super('CONFLICT', message, 409);
  }
}
