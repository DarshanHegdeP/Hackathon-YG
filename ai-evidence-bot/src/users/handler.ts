import { APIGatewayProxyEvent } from 'aws-lambda';
import { success, errorResponse } from '../shared/response';
import { NotFoundError } from '../shared/errors';
import { getUser, listUsers } from './repository';

export async function get(event: APIGatewayProxyEvent) {
  try {
    const userId = event.pathParameters?.userId;
    if (!userId) throw new Error('userId required');
    const user = await getUser(userId);
    if (!user) throw new NotFoundError('User not found');
    return success(user);
  } catch (err) {
    return errorResponse(err);
  }
}

export async function list(event: APIGatewayProxyEvent) {
  try {
    const filters = event.queryStringParameters || {};
    const users = await listUsers(filters);
    return success(users);
  } catch (err) {
    return errorResponse(err);
  }
}
