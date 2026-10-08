import { AppError } from './errors';

export function success(data: any) {
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data })
  };
}

export function errorResponse(err: any) {
  if (err instanceof AppError) {
    return {
      statusCode: err.statusCode,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: {
          code: err.code,
          message: err.message,
          details: err.details
        }
      })
    };
  }
  console.error(err);
  return {
    statusCode: 500,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      error: {
        code: 'INTERNAL_ERROR',
        message: 'An internal error occurred'
      }
    })
  };
}
