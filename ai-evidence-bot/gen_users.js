const fs = require('fs');
const path = require('path');

function write(file, content) {
  fs.writeFileSync(path.join(__dirname, file), content.trim() + '\n');
}

write('src/users/repository.ts', `
import { GetCommand, ScanCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from "../shared/db";
import { User } from "../shared/types";

const TABLE_NAME = process.env.USERS_TABLE || '';

export async function getUser(userId: string): Promise<User | null> {
  const result = await docClient.send(new GetCommand({
    TableName: TABLE_NAME,
    Key: { userId }
  }));
  return (result.Item as User) || null;
}

export async function listUsers(filters: any): Promise<User[]> {
  const result = await docClient.send(new ScanCommand({
    TableName: TABLE_NAME
  }));
  let users = (result.Items || []) as User[];
  if (filters.role) users = users.filter(u => u.role === filters.role);
  if (filters.businessUnit) users = users.filter(u => u.businessUnit === filters.businessUnit);
  if (filters.active !== undefined) {
    const active = filters.active === 'true';
    users = users.filter(u => u.active === active);
  }
  return users;
}
`);

write('src/users/handler.ts', `
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
`);
console.log('Users generated');
