import { PutCommand, GetCommand, ScanCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from "../shared/db";
import { Control } from "../shared/types";

const TABLE_NAME = process.env.CONTROLS_TABLE || '';

export async function saveControl(control: Control): Promise<void> {
  await docClient.send(new PutCommand({
    TableName: TABLE_NAME,
    Item: control
  }));
}

export async function getControl(controlId: string): Promise<Control | null> {
  const result = await docClient.send(new GetCommand({
    TableName: TABLE_NAME,
    Key: { controlId }
  }));
  return (result.Item as Control) || null;
}

export async function listControls(filters: any): Promise<Control[]> {
  const result = await docClient.send(new ScanCommand({
    TableName: TABLE_NAME
  }));
  let controls = (result.Items || []) as Control[];
  if (filters.domain) controls = controls.filter(c => c.domain === filters.domain);
  if (filters.riskLevel) controls = controls.filter(c => c.riskLevel === filters.riskLevel);
  if (filters.status) controls = controls.filter(c => c.status === filters.status);
  return controls;
}
