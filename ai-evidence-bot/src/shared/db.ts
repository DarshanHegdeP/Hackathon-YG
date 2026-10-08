import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient } from "@aws-sdk/lib-dynamodb";

const client = new DynamoDBClient({
  endpoint: process.env.AWS_SAM_LOCAL ? "http://127.0.0.1:8000" : undefined,
});
export const docClient = DynamoDBDocumentClient.from(client);
