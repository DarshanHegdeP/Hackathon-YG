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
